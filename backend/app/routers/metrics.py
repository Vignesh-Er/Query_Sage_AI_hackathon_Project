import math
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Connection
from app.connectors import get_connector
from app.fingerprint import fingerprint

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])

@router.get("/workload")
async def get_workload_metrics(connection_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetches the top 20 slow queries from pg_stat_statements sorted by total_exec_time.
    Gracefully degrades if the pg_stat_statements extension is missing.
    """
    result = await db.execute(select(Connection).filter(Connection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    if conn.engine != "postgresql":
        return {
            "data": [],
            "metadata": {
                "message": "pg_stat_statements extension not installed on this database. Enable it with CREATE EXTENSION pg_stat_statements and restart the database."
            }
        }

    db_config = {
        "host": conn.host,
        "port": conn.port,
        "database": conn.database,
        "username": conn.username
    }
    connector = get_connector(conn.id, conn.engine, db_config)
    await asyncio.to_thread(connector.connect)

    try:
        stats_list = await asyncio.to_thread(connector.fetch_pg_stat_statements)
        if not stats_list:
            return {
                "data": [],
                "metadata": {
                    "message": "pg_stat_statements extension not installed on this database. Enable it with CREATE EXTENSION pg_stat_statements and restart the database."
                }
            }
    except Exception:
        return {
            "data": [],
            "metadata": {
                "message": "pg_stat_statements extension not installed on this database. Enable it with CREATE EXTENSION pg_stat_statements and restart the database."
            }
        }
    finally:
        await asyncio.to_thread(connector.disconnect)

    formatted_stats = []
    for stat in stats_list:
        stat_query = stat.get("query", "")
        stat_fp = fingerprint(stat_query, "postgres")
        calls = int(stat.get("calls", 0))
        total_exec_time = float(stat.get("total_exec_time", 0.0))
        mean_exec_time = float(stat.get("mean_exec_time", 0.0))
        rows = int(stat.get("rows", 0))

        fp_truncated = stat_fp[:60]
        impact_score = 1.0 * math.log10(calls + 1)

        formatted_stats.append({
            "query_fingerprint": fp_truncated,
            "calls": calls,
            "mean_exec_time_ms": round(mean_exec_time, 2),
            "total_exec_time_ms": round(total_exec_time, 2),
            "rows": rows,
            "infrastructure_impact_score": round(impact_score, 2),
            "total_exec_time": total_exec_time
        })

    # Sort by total_exec_time descending and take top 20
    formatted_stats.sort(key=lambda x: x["total_exec_time"], reverse=True)
    top_20 = formatted_stats[:20]

    for item in top_20:
        item.pop("total_exec_time", None)

    return {
        "data": top_20,
        "metadata": {
            "count": len(top_20)
        }
    }
