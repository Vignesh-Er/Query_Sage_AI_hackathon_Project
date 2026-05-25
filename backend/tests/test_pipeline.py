import json
import pytest
from unittest.mock import AsyncMock, patch
from app.models import Query, Finding, Plan, Rewrite, Score
from app.pipeline import analyze_query_pipeline

@pytest.mark.anyio
@patch("app.pipeline.call_ai_provider")
async def test_analyze_query_stream_pipeline(mock_ai, db_session):
    # Mock AI response
    mock_ai.return_value = {
        "rewritten_query": "SELECT rental_id FROM rental WHERE rental_date >= '2005-01-01' AND rental_date < '2006-01-01';",
        "changes": [
            {
                "type": "predicate_rewrite",
                "original_fragment": "YEAR(rental_date) = 2005",
                "replacement_fragment": "rental_date >= '2005-01-01' AND rental_date < '2006-01-01'",
                "reason": "Optimize index usage by removing scalar function"
            }
        ],
        "index_recommendations": [],
        "estimated_row_reduction_percent": 15.0,
        "confidence": "high",
        "plain_summary": "Removed scalar function wrapping from column to enable index scans.",
        "follow_up_questions": []
    }

    # Execute the pipeline generator directly
    generator = analyze_query_pipeline(
        db=db_session,
        query_sql="SELECT * FROM rental WHERE YEAR(rental_date) = 2005;",
        connection_id=None,
        include_execution_plan=False,  # skip DB connection
        verify_equivalence_check=False,
        orm_framework=None
    )

    # Process SSE chunks
    events = []
    async for chunk in generator:
        # chunk is a string like "event: event_type\ndata: json_str\n\n"
        for line in chunk.split("\n"):
            if line.startswith("event:"):
                event_type = line.split("event: ")[1].strip()
                events.append(event_type)

    # Assert expected SSE stages
    assert "status" in events  # parsing status
    assert "finding" in events  # Rule findings (P01, P02, etc. should trigger on this query)
    assert "rewrite" in events  # AI proposal rewrite
    assert "complete" in events # completion event

    # Verify query and findings were written to in-memory SQLite DB
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    result = await db_session.execute(select(Query))
    saved_query = result.scalars().first()
    assert saved_query is not None
    assert "SELECT * FROM rental" in saved_query.raw_sql

    result = await db_session.execute(select(Finding).filter(Finding.query_id == saved_query.id))
    findings = result.scalars().all()
    assert len(findings) > 0
    # Rule P02 (YEAR function) and P01 (SELECT star) should have triggered
    rule_ids = [f.rule_id for f in findings]
    assert "P01" in rule_ids
    assert "P02" in rule_ids

    # Check score saved
    result = await db_session.execute(select(Score))
    score_entry = result.scalars().first()
    assert score_entry is not None
    assert score_entry.query_score < 100.0  # penalties applied

@pytest.mark.anyio
@patch("app.pipeline.call_ai_provider")
async def test_patient_records_anonymization(mock_ai, db_session):
    # Mock AI response to capture the prompt content passed to call_ai_provider
    mock_ai.return_value = {
        "rewritten_query": "SELECT * FROM pii_table_1;",
        "changes": [],
        "index_recommendations": [],
        "estimated_row_reduction_percent": 0.0,
        "confidence": "high",
        "plain_summary": "Query anonymized.",
        "follow_up_questions": []
    }

    # Execute the pipeline with a sensitive table query and custom schema metadata
    from unittest.mock import MagicMock
    with patch("app.pipeline.get_connector") as mock_conn_init:
        # Mock connector instance
        mock_connector_inst = MagicMock()
        mock_connector_inst.engine = "postgresql"
        mock_connector_inst.fetch_schema.return_value = {
            "tables": {
                "patient_records": {
                    "name": "patient_records",
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "patient_id", "type": "varchar"},
                        {"name": "diagnosis", "type": "varchar"}
                    ],
                    "primary_key": ["id"],
                    "foreign_keys": []
                }
            },
            "indexes": {}
        }
        mock_connector_inst.execute_explain.return_value = [{"Plan": {"Node Type": "Seq Scan", "Relation Name": "patient_records", "Startup Cost": 0.0, "Total Cost": 10.0, "Plan Rows": 100}}]
        mock_conn_init.return_value = mock_connector_inst
        
        # Create a connection model inside the db session
        from app.models import Connection
        conn_model = Connection(name="test_pg", engine="postgresql", host="127.0.0.1", port=5432, database="test")
        db_session.add(conn_model)
        await db_session.commit()
        
        generator = analyze_query_pipeline(
            db=db_session,
            query_sql="SELECT * FROM patient_records WHERE patient_id = '123';",
            connection_id=conn_model.id,
            include_execution_plan=True,
            verify_equivalence_check=False,
            orm_framework=None
        )
        
        # Consume generator to trigger build_analysis_context and call_ai_provider
        events = []
        async for chunk in generator:
            events.append(chunk)
            
        # Assert call_ai_provider was called with context containing redacted table name
        mock_ai.assert_called_once()
        called_context = mock_ai.call_args[0][0]
        
        # Redacted schema context check
        schema_context = called_context.get("schema_context")
        assert schema_context is not None
        assert "patient_records" not in schema_context["tables"]
        # It must be mapped to pii_table_1 or similar
        assert any(t.startswith("pii_table_") for t in schema_context["tables"])
