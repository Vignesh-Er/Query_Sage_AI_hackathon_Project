import json
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Query
from app.report import generate_pdf_report, generate_markdown_report

router = APIRouter(prefix="/api/report", tags=["Reporting"])

@router.get("/{query_id}/pdf")
async def export_pdf_report(
    query_id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Query).filter(Query.id == query_id))
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query record not found")
        
    try:
        # Determine host (for local vs docker context)
        host = request.url.hostname or "localhost"
        pdf_bytes = await generate_pdf_report(query_id, host=host)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=querysage_report_{query_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

@router.get("/{query_id}/markdown")
async def export_markdown_report(query_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Query).options(
        selectinload(Query.findings),
        selectinload(Query.plans),
        selectinload(Query.rewrites)
    ).filter(Query.id == query_id)
    result = await db.execute(stmt)
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query record not found")
        
    findings = [
        {
            "rule_id": f.rule_id,
            "severity": f.severity,
            "category": f.category,
            "title": f.title,
            "description": f.description
        }
        for f in query.findings
    ]
    
    plan_info = None
    if query.plans:
        p = query.plans[0]
        plan_info = {
            "total_cost": p.total_cost,
            "rows_estimated": p.rows_estimated,
            "rows_actual": p.rows_actual,
            "execution_time_ms": p.execution_time_ms,
            "cache_hit_ratio": p.cache_hit_ratio,
            "has_seq_scan": p.has_seq_scan,
            "has_sort_spill": p.has_sort_spill
        }
        
    rewrite_info = None
    if query.rewrites:
        r = query.rewrites[0]
        try:
            changes = json.loads(r.changes_json)
            recs = json.loads(r.index_recommendations_json)
        except Exception:
            changes = r.changes_json
            recs = r.index_recommendations_json
            
        rewrite_info = {
            "rewritten_query": r.rewritten_sql,
            "changes": changes,
            "index_recommendations": recs,
            "estimated_row_reduction_percent": r.estimated_row_reduction_percent,
            "confidence": r.confidence
        }
        
    md_content = generate_markdown_report(
        raw_sql=query.raw_sql,
        findings=findings,
        plan_summary=plan_info,
        rewrite_proposal=rewrite_info
    )
    
    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=querysage_report_{query_id}.md"
        }
    )
