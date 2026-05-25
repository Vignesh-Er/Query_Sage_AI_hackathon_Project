from fastapi import APIRouter, Depends, HTTPException, Query as FastAPIQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogResponse

router = APIRouter(prefix="/api/audit-log", tags=["Auditing"])

@router.get("", response_model=List[AuditLogResponse])
async def get_audit_logs(
    page: int = 1,
    page_size: int = 20,
    event_type: Optional[str] = None,
    start_date: Optional[str] = None, # ISO-8601 string
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * page_size
    stmt = select(AuditLog)
    
    if event_type:
        stmt = stmt.filter(AuditLog.event_type == event_type)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            stmt = stmt.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            stmt = stmt.filter(AuditLog.created_at <= end_dt)
        except ValueError:
            pass
            
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all()
