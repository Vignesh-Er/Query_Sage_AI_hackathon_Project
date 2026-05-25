from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse
from typing import List
from app.database import get_db
from app.schemas import AnalyzeRequest, WhatIfRequest, WhatIfResponse, LintRequest, FindingResponse
from app.pipeline import analyze_query_pipeline
from app.models import Connection
from app.connectors import get_connector
from app.what_if import simulate_hypothetical_index
from app.rules import registry
import sqlglot

router = APIRouter(prefix="/api/analyze", tags=["Analysis"])

@router.post("/stream")
async def analyze_query_stream(
    data: AnalyzeRequest
):
    """
    Accepts a SQL query and connection options, running Layer 1, 2, and 3
    in sequence and streaming events via SSE.
    """
    from app.database import SessionLocal
    
    async def stream_wrapper():
        async with SessionLocal() as db:
            generator = analyze_query_pipeline(
                db=db,
                query_sql=data.query,
                connection_id=data.connection_id,
                include_execution_plan=data.include_execution_plan,
                verify_equivalence_check=data.verify_equivalence,
                orm_framework=data.orm_framework
            )
            async for event in generator:
                yield event

    return EventSourceResponse(stream_wrapper())

@router.post("/what-if", response_model=WhatIfResponse)
async def analyze_what_if(
    data: WhatIfRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Simulates index creation using pg_hint_plan index scans and compares plan costs.
    """
    result = await db.execute(select(Connection).filter(Connection.id == data.connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        db_config = {
            "host": conn.host,
            "port": conn.port,
            "database": conn.database,
            "username": conn.username
        }
        connector = get_connector(conn.id, conn.engine, db_config)
        connector.connect()
        
        sim_res = simulate_hypothetical_index(
            connector=connector,
            query=data.query,
            index_statement=data.index_statement,
            dialect=conn.engine
        )
        connector.disconnect()
        
        if not sim_res:
            return WhatIfResponse(
                success=False,
                error="Hypothetical index simulation failed. Ensure pg_hint_plan is installed and loaded in PostgreSQL."
            )
            
        return WhatIfResponse(
            success=True,
            index_name=sim_res["index_name"],
            table_name=sim_res["table_name"],
            columns=sim_res["columns"],
            hinted_query=sim_res["hinted_query"],
            original_cost=sim_res["original_cost"],
            original_rows=sim_res["original_rows"],
            hinted_cost=sim_res["hinted_cost"],
            hinted_rows=sim_res["hinted_rows"],
            cost_reduction_percent=sim_res["cost_reduction_percent"],
            original_plan_json=sim_res["original_plan_json"],
            hinted_plan_json=sim_res["hinted_plan_json"]
        )
    except Exception as e:
        return WhatIfResponse(
            success=False,
            error=f"Simulation failed with error: {str(e)}"
        )

@router.post("/lint", response_model=List[FindingResponse])
async def analyze_lint(
    data: LintRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Fast AST-based SQL linter running Layer 1 only.
    No database execution, no AI integration, responds in < 150ms.
    """
    dialect = "postgres"
    if data.connection_id:
        result = await db.execute(select(Connection).filter(Connection.id == data.connection_id))
        conn = result.scalar_one_or_none()
        if conn:
            dialect = "postgres" if conn.engine == "postgresql" else conn.engine

    try:
        # Step 1: parse query with dialect
        parsed_ast = sqlglot.parse_one(data.query, read=dialect)
        # Step 2: run static rules engine
        findings = registry.run_all(parsed_ast)
        # Step 3: convert to response format
        return [FindingResponse.model_validate(f) for f in findings]
    except Exception as e:
        # Return fallback parse warning finding
        return [
            FindingResponse(
                rule_id="G01",
                severity=8,
                category="CORRECTNESS",
                title="SQL Syntax parsing error",
                description=f"Query structure could not be parsed: {str(e)}"
            )
        ]

