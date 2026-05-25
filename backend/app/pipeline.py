import json
import logging
import hashlib
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.config import settings
from app.connectors import get_connector
from app.connectors.base import DatabaseConnector
from app.rules import registry, Finding as RuleFinding
from app.parser import (
    PlanNode, 
    parse_postgresql_plan, 
    parse_mysql_plan, 
    parse_sqlite_plan, 
    derive_postgres_metrics
)
from app.synthetic_injector import inject_synthetic_parameters
from app.workload import get_workload_context
from app.validator import verify_equivalence as run_equivalence_test
from app.redactor import redact_schema_excerpt
from app.prompt import clean_sql_comments_injection, build_analysis_context, call_ai_provider
from app.scoring import get_or_create_next_score
from app.models import Connection, Query, Finding, Plan, Rewrite, RegressionEvent, AuditLog
from app.orm_detector import detect_orm
from app.observability import (
    setup_telemetry,
    instrument_pipeline_stage,
    record_finding_event,
    record_regression_event
)
import sqlglot

logger = logging.getLogger(__name__)

# Initialize the module-level tracer
tracer = setup_telemetry("querysage")

async def analyze_query_pipeline(
    db: AsyncSession,
    query_sql: str,
    connection_id: Optional[int],
    include_execution_plan: bool,
    verify_equivalence_check: bool,
    orm_framework: Optional[str]
) -> AsyncGenerator[str, None]:
    """
    Coordinates Layers 1, 2, and 3 of the QuerySage database analysis pipeline
    and yields SSE formatted messages as events arrive.
    """
    def sse_event(event_type: str, data: Any) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    # Step 1: Parsing
    yield sse_event("status", {"stage": "parsing", "message": "Parsing query AST..."})
    
    cleaned_sql, comment_logs = clean_sql_comments_injection(query_sql)
    for log in comment_logs:
        logger.warning(log)

    dialect = "postgres"  # default fallback
    connector: Optional[DatabaseConnector] = None
    db_conn_model: Optional[Connection] = None
    
    if connection_id:
        result = await db.execute(select(Connection).filter(Connection.id == connection_id))
        db_conn_model = result.scalar_one_or_none()
        if db_conn_model:
            dialect = "postgres" if db_conn_model.engine == "postgresql" else db_conn_model.engine
            # Initialize Connector
            try:
                db_config = {
                    "host": db_conn_model.host,
                    "port": db_conn_model.port,
                    "database": db_conn_model.database,
                    "username": db_conn_model.username
                }
                connector = get_connector(connection_id, db_conn_model.engine, db_config)
                await asyncio.to_thread(connector.connect)
            except Exception as e:
                logger.error(f"Failed to connect to database ID {connection_id}: {str(e)}")
                connector = None

    db_system = db_conn_model.engine if db_conn_model else "sqlite"
    from app.fingerprint import fingerprint
    query_fp = fingerprint(cleaned_sql, dialect)

    # Step 2: Layer 1 — Detective (Static AST analysis)
    static_findings: List[RuleFinding] = []
    schema_excerpt: Optional[Dict[str, Any]] = None
    
    with instrument_pipeline_stage(tracer, "parsing", query_fp, db_system) as span:
        try:
            parsed_ast = sqlglot.parse_one(cleaned_sql, read=dialect)
            
            # If we have an active connector, load schema metadata to assist rules engine (like I01-I05, P05)
            if connector:
                try:
                    schema_excerpt = await asyncio.to_thread(connector.fetch_schema)
                except Exception:
                    pass
                    
            static_findings = registry.run_all(parsed_ast, schema_excerpt)
        except Exception as e:
            logger.error(f"Static AST analysis error: {str(e)}")
            # Emplace default parsing error finding if sqlglot crashes
            static_findings = [
                RuleFinding(
                    rule_id="G01",
                    severity=8,
                    category="CORRECTNESS",
                    title="SQL Syntax parsing error",
                    description=f"Query structure could not be parsed: {str(e)}"
                )
            ]

        severity_sum = 0
        findings_list_dict = []
        for f in static_findings:
            severity_sum += f.severity
            f_dict = f.to_dict()
            findings_list_dict.append(f_dict)
            try:
                record_finding_event(span, f_dict)
            except Exception as te:
                logger.warning(f"Telemetry error in finding event: {str(te)}")
            yield sse_event("finding", f_dict)

    # Step 3: Layer 2 — Prosecutor (Execution Plan analysis)
    plan_summary: Optional[Dict[str, Any]] = None
    plan_node_tree: Optional[PlanNode] = None
    raw_explain_output = None
    
    if connector and include_execution_plan:
        yield sse_event("status", {"stage": "executing", "message": "Fetching execution plan..."})
        
        with instrument_pipeline_stage(tracer, "executing", query_fp, db_system) as exec_span:
            # Inject most common values from stats to avoid generic planner bias
            injected_sql, injection_logs = inject_synthetic_parameters(cleaned_sql, dialect, connector)
            
            try:
                # We run explain (only SELECT is analyzed, DML is only explained without execution)
                # Checked in connector base
                is_dml = any(keyword in cleaned_sql.lower() for keyword in ["update ", "delete ", "insert "])
                raw_explain_output = await asyncio.to_thread(connector.execute_explain, injected_sql, use_analyze=not is_dml)
                
                # Parse plan
                if db_conn_model.engine == "postgresql":
                    plan_node_tree = parse_postgresql_plan(raw_explain_output)
                    metrics = derive_postgres_metrics(plan_node_tree)
                    
                    plan_summary = {
                        "total_cost": plan_node_tree.cost_total,
                        "rows_estimated": plan_node_tree.rows_estimated,
                        "rows_actual": plan_node_tree.rows_actual,
                        "execution_time_ms": getattr(plan_node_tree, "execution_time_ms", None) or plan_node_tree.cost_total,
                        "cache_hit_ratio": metrics["cache_hit_ratio"],
                        "has_seq_scan": len(metrics["seq_scans"]) > 0,
                        "has_sort_spill": metrics["has_sort_spill"],
                        "plan_json": plan_node_tree.to_dict(),
                        "warnings": metrics.get("findings", [])
                    }
                elif db_conn_model.engine == "mysql":
                    plan_node_tree = parse_mysql_plan(raw_explain_output)
                    plan_summary = {
                        "total_cost": plan_node_tree.cost_total,
                        "rows_estimated": plan_node_tree.rows_estimated,
                        "rows_actual": 0.0,
                        "execution_time_ms": 0.0,
                        "cache_hit_ratio": 1.0,
                        "has_seq_scan": plan_node_tree.node_type == "ALL",
                        "has_sort_spill": False,
                        "plan_json": plan_node_tree.to_dict()
                    }
                else: # SQLite
                    plan_node_tree = parse_sqlite_plan(raw_explain_output)
                    plan_summary = {
                        "total_cost": 0.0,
                        "rows_estimated": 0.0,
                        "rows_actual": 0.0,
                        "execution_time_ms": 0.0,
                        "cache_hit_ratio": 1.0,
                        "has_seq_scan": False,
                        "has_sort_spill": False,
                        "plan_json": plan_node_tree.to_dict()
                    }
                    
                    plan_summary["injection_logs"] = injection_logs
                yield sse_event("plan", plan_summary)
                
                # Step 4: Regression Detection
                # Compare cost to historical queries with same fingerprint
                from app.fingerprint import fingerprint
                fp = fingerprint(cleaned_sql, dialect)
                result = await db.execute(
                    select(Query).options(selectinload(Query.plans)).filter(Query.fingerprint == fp, Query.connection_id == connection_id).order_by(Query.submitted_at.desc()).limit(1)
                )
                last_query_entry = result.scalar_one_or_none()
                if last_query_entry and last_query_entry.plans:
                    last_plan = last_query_entry.plans[0] # most recent plan
                    cost_ratio = plan_summary["total_cost"] / last_plan.total_cost if last_plan.total_cost > 0 else 1.0
                    
                    if cost_ratio > 1.20:
                        regression_type = "cost_increase"
                        # Log event
                        reg_event = RegressionEvent(
                            query_id=last_query_entry.id,
                            previous_plan_id=last_plan.id,
                            current_plan_id=0, # set after creating plan row
                            cost_delta_percent=(cost_ratio - 1) * 100,
                            regression_type=regression_type,
                            detected_at=datetime.utcnow()
                        )
                        # We will append to database inside cleanup, for now yield regression event
                        regression_data = {
                            "previous_cost": last_plan.total_cost,
                            "current_cost": plan_summary["total_cost"],
                            "delta_percent": (cost_ratio - 1) * 100,
                            "regression_type": regression_type
                        }
                        try:
                            record_regression_event(exec_span, regression_data)
                        except Exception as te:
                            logger.warning(f"Telemetry error in regression event: {str(te)}")
                        yield sse_event("regression", regression_data)
            except Exception as e:
                logger.error(f"Plan profiling execution error: {str(e)}")

    # Step 5: Workload Context
    workload_summary: Optional[Dict[str, Any]] = None
    if connector:
        yield sse_event("status", {"stage": "workload", "message": "Loading workload context..."})
        try:
            raw_summary = get_workload_context(connector, cleaned_sql, dialect, severity_sum)
            if raw_summary:
                from app.schemas import WorkloadContextResponse
                # Validate using Pydantic model
                validated_model = WorkloadContextResponse(**raw_summary)
                workload_summary = validated_model.model_dump()
                yield sse_event("workload", workload_summary)
        except Exception as e:
            logger.error(f"Workload context execution error: {str(e)}")

    # Step 6: Layer 3 — Counsel (AI optimizations & rewrites)
    yield sse_event("status", {"stage": "ai", "message": "Generating optimization..."})
    
    # Redact sensitive tables/columns in schema subset before prompt injection
    redacted_schema = None
    redaction_logs = []
    if schema_excerpt:
        redacted_schema, redaction_logs = redact_schema_excerpt(schema_excerpt)
        logger.info(f"PII redaction complete: {len(redaction_logs)} items masked.")
        
    ai_proposal: Optional[Dict[str, Any]] = None
    prompt_hash = ""
    schema_hash = ""
    output_hash = ""
    
    # Run ORM signature detection if not explicitly set
    detected_orm_val = detect_orm(query_sql)
    if detected_orm_val is not None and not orm_framework:
        orm_framework = detected_orm_val
    
    with instrument_pipeline_stage(tracer, "ai", query_fp, db_system) as ai_span:
        try:
            # Build query context prompt payload
            prompt_payload = build_analysis_context(
                query=cleaned_sql,
                findings=findings_list_dict,
                plan_summary=plan_summary,
                workload_context=workload_summary,
                schema_excerpt=redacted_schema,
                orm_framework=orm_framework
            )
            
            # Calculate context verification hashes
            prompt_hash = hashlib.sha256(json.dumps(prompt_payload.get("input_query")).encode("utf-8")).hexdigest()
            schema_hash = hashlib.sha256(json.dumps(prompt_payload.get("schema_context")).encode("utf-8")).hexdigest()
            
            ai_proposal = await call_ai_provider(prompt_payload)
            
            output_hash = hashlib.sha256(json.dumps(ai_proposal.get("rewritten_query")).encode("utf-8")).hexdigest()
            yield sse_event("rewrite", ai_proposal)
        except Exception as e:
            logger.error(f"AI Advisor processing error: {str(e)}")
            # Fallback rewrite
            ai_proposal = {
                "rewritten_query": cleaned_sql,
                "changes": [],
                "index_recommendations": [],
                "estimated_row_reduction_percent": 0.0,
                "confidence": "low",
                "plain_summary": f"Advisor failed to respond: {str(e)}",
                "follow_up_questions": []
            }
            yield sse_event("rewrite", ai_proposal)

    # Step 7: Semantic Equivalence Check
    equivalence_result = None
    if connector and verify_equivalence_check and ai_proposal and ai_proposal.get("rewritten_query"):
        yield sse_event("status", {"stage": "equivalence", "message": "Verifying semantic equivalence..."})
        try:
            equivalence_result = await asyncio.to_thread(
                run_equivalence_test,
                connector, 
                cleaned_sql, 
                ai_proposal["rewritten_query"], 
                dialect
            )
            yield sse_event("equivalence", equivalence_result)
        except Exception:
            pass

    # Close Connector Session
    if connector:
        await asyncio.to_thread(connector.disconnect)

    # Step 8: Database Logging, scoring and audit hooks
    try:
        from app.fingerprint import fingerprint
        query_fp = fingerprint(cleaned_sql, dialect)
        
        # Create Query Log
        query_row = Query(
            fingerprint=query_fp,
            raw_sql=query_sql,
            normalized_sql=cleaned_sql,
            connection_id=connection_id,
            submitted_at=datetime.utcnow(),
            tags=json.dumps([]),
            source="manual"
        )
        db.add(query_row)
        await db.commit()
        await db.refresh(query_row)
        
        # Add Static findings rows
        for f in static_findings:
            finding_row = Finding(
                query_id=query_row.id,
                rule_id=f.rule_id,
                severity=f.severity,
                category=f.category,
                title=f.title,
                description=f.description,
                location_start=f.location_start,
                location_end=f.location_end,
                auto_fixable=f.auto_fixable
            )
            db.add(finding_row)
            
        # Save Execution plan row
        plan_row = None
        if plan_summary:
            plan_row = Plan(
                query_id=query_row.id,
                plan_json=json.dumps(plan_summary["plan_json"]),
                total_cost=plan_summary["total_cost"],
                rows_estimated=plan_summary["rows_estimated"],
                rows_actual=plan_summary["rows_actual"],
                execution_time_ms=plan_summary["execution_time_ms"],
                cache_hit_ratio=plan_summary["cache_hit_ratio"],
                has_seq_scan=plan_summary["has_seq_scan"],
                has_sort_spill=plan_summary["has_sort_spill"]
            )
            db.add(plan_row)
            
        await db.commit()
        if plan_row:
            await db.refresh(plan_row)
            
        # Save Rewrite row
        rewrite_row = Rewrite(
            query_id=query_row.id,
            rewritten_sql=ai_proposal["rewritten_query"],
            changes_json=json.dumps(ai_proposal["changes"]),
            index_recommendations_json=json.dumps(ai_proposal["index_recommendations"]),
            estimated_row_reduction_percent=ai_proposal["estimated_row_reduction_percent"],
            confidence=ai_proposal["confidence"],
            semantic_equivalence_verified=equivalence_result.get("result_match", False) if equivalence_result else False,
            ai_model=settings.QUERYSAGE_ANTHROPIC_MODEL if settings.QUERYSAGE_AI_PROVIDER == "anthropic" else settings.QUERYSAGE_OLLAMA_MODEL
        )
        db.add(rewrite_row)
        await db.commit()
        await db.refresh(rewrite_row)

        # Save Scorecard rolling score
        score_row = await get_or_create_next_score(db, query_row.id, findings_list_dict)
        
        # Save AuditLog entry
        audit_row = AuditLog(
            event_type="query_optimize",
            query_id=query_row.id,
            ai_model=rewrite_row.ai_model,
            prompt_hash=prompt_hash,
            schema_subset_hash=schema_hash,
            output_hash=output_hash,
            confidence=rewrite_row.confidence,
            created_at=datetime.utcnow()
        )
        db.add(audit_row)
        await db.commit()
        
        # Yield final completion summary
        from app.scoring import calculate_cognitive_complexity
        try:
            cog_complexity = calculate_cognitive_complexity(query_sql)
        except Exception as ce:
            logger.warning(f"Failed to calculate cognitive complexity: {str(ce)}")
            cog_complexity = {
                "join_count": 0,
                "subquery_depth": 0,
                "case_count": 0,
                "window_function_count": 0,
                "cognitive_complexity_score": 0
            }

        yield sse_event("complete", {
            "query_id": query_row.id, 
            "score_delta": score_row.query_score - score_row.rolling_average,
            "cognitive_complexity": cog_complexity
        })
    except Exception as e:
        logger.error(f"Pipeline database logs commit crash: {str(e)}")
        yield sse_event("complete", {"query_id": 0, "score_delta": 0.0})
