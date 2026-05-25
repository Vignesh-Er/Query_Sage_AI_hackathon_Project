from fastapi import APIRouter, Depends, HTTPException, Query as FastAPIQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
import json
from app.database import get_db
from app.models import Query, Finding, Plan, Rewrite, EquivalenceCheck

router = APIRouter(prefix="/api/history", tags=["History"])

@router.get("")
async def get_query_history(
    page: int = 1,
    page_size: int = 10,
    fingerprint: Optional[str] = None,
    connection_id: Optional[int] = None,
    tags: Optional[str] = None, # comma-separated list
    days_ago: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * page_size
    stmt = select(Query)
    
    if fingerprint:
        stmt = stmt.filter(Query.fingerprint == fingerprint)
    if connection_id:
        stmt = stmt.filter(Query.connection_id == connection_id)
    if days_ago:
        cutoff = datetime.utcnow() - timedelta(days=days_ago)
        stmt = stmt.filter(Query.submitted_at >= cutoff)
        
    stmt = stmt.order_by(Query.submitted_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    results = result.scalars().all()
    
    # Optional tags filtering post-fetch for sqlite
    if tags:
        filter_tags = [t.strip().lower() for t in tags.split(",")]
        filtered_results = []
        for r in results:
            try:
                r_tags = [t.lower() for t in json.loads(r.tags or "[]")]
                if any(t in r_tags for t in filter_tags):
                    filtered_results.append(r)
            except Exception:
                pass
        return filtered_results
        
    return results

@router.get("/{query_id}")
async def get_query_detail(query_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Query).options(
        selectinload(Query.findings),
        selectinload(Query.plans),
        selectinload(Query.rewrites),
        selectinload(Query.equivalence_checks)
    ).filter(Query.id == query_id)
    result = await db.execute(stmt)
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query record not found")
        
    # Serialize relationships manually to ensure clean Pydantic conversions
    findings = [
        {
            "rule_id": f.rule_id,
            "severity": f.severity,
            "category": f.category,
            "title": f.title,
            "description": f.description,
            "location_start": f.location_start,
            "location_end": f.location_end,
            "auto_fixable": f.auto_fixable
        }
        for f in query.findings
    ]
    
    plan_info = None
    if query.plans:
        p = query.plans[0] # most recent plan
        try:
            plan_json = json.loads(p.plan_json)
        except Exception:
            plan_json = p.plan_json
        plan_info = {
            "total_cost": p.total_cost,
            "rows_estimated": p.rows_estimated,
            "rows_actual": p.rows_actual,
            "execution_time_ms": p.execution_time_ms,
            "cache_hit_ratio": p.cache_hit_ratio,
            "has_seq_scan": p.has_seq_scan,
            "has_sort_spill": p.has_sort_spill,
            "plan_json": plan_json
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
            "confidence": r.confidence,
            "plain_summary": r.plain_summary if hasattr(r, "plain_summary") else "Optimized rewrite",
            "follow_up_questions": json.loads(r.follow_up_questions) if hasattr(r, "follow_up_questions") and r.follow_up_questions else []
        }
        
    equivalence_info = None
    if query.equivalence_checks:
        eq = query.equivalence_checks[0]
        equivalence_info = {
            "row_count_match": eq.row_count_match if hasattr(eq, "row_count_match") else (eq.original_row_count == eq.optimized_row_count),
            "original_row_count": eq.original_row_count,
            "optimized_row_count": eq.optimized_row_count,
            "original_hash": eq.original_hash,
            "optimized_hash": eq.optimized_hash,
            "result_match": eq.result_match,
            "status": "VERIFIED" if eq.result_match else "ALTERED"
        }

    return {
        "id": query.id,
        "fingerprint": query.fingerprint,
        "raw_sql": query.raw_sql,
        "normalized_sql": query.normalized_sql,
        "submitted_at": query.submitted_at,
        "tags": json.loads(query.tags or "[]"),
        "source": query.source,
        "findings": findings,
        "plan": plan_info,
        "rewrite": rewrite_info,
        "equivalence": equivalence_info
    }

@router.post("/{query_id}/tags")
async def update_query_tags(query_id: int, tags: List[str], db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Query).filter(Query.id == query_id))
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query record not found")
        
    query.tags = json.dumps(tags)
    await db.commit()
    return {"id": query.id, "tags": tags}
