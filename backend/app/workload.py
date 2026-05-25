import math
from typing import Any, Dict, List, Optional
from app.connectors.base import DatabaseConnector
from app.fingerprint import fingerprint

def get_workload_context(
    connector: DatabaseConnector,
    query_sql: str,
    dialect: str,
    base_severity_sum: float
) -> Optional[Dict[str, Any]]:
    """
    Queries pg_stat_statements, normalizes digests, maps the query to workload context,
    and returns execution statistics and the Infrastructure Impact Score.
    """
    stats_list = connector.fetch_pg_stat_statements()
    if not stats_list:
        return None

    # Calculate fingerprint of the input query
    query_fp = fingerprint(query_sql, dialect)

    for stat in stats_list:
        stat_query = stat.get("query", "")
        # Get fingerprint of pg_stat_statements item
        stat_fp = fingerprint(stat_query, dialect)
        
        if query_fp == stat_fp:
            calls = stat.get("calls", 0)
            total_exec_time = stat.get("total_exec_time", 0.0)
            mean_exec_time = stat.get("mean_exec_time", 0.0)
            rows = stat.get("rows", 0)
            
            # Estimate daily calls (assume stat window is average daily, or raw value)
            # We treat calls as raw calls for the scoring calculation
            severity_coeff = max(base_severity_sum, 1.0)
            impact_score = severity_coeff * math.log10(calls + 1)
            
            return {
                "query": stat_query,
                "calls": calls,
                "total_exec_time": total_exec_time,
                "mean_exec_time": mean_exec_time,
                "rows": rows,
                "calls_per_day": float(calls),
                "infrastructure_impact_score": round(impact_score, 2)
            }
            
    return None
