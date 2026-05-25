import re
import sqlglot
from typing import Any, Dict, Optional, Tuple
from app.connectors.base import DatabaseConnector

def parse_create_index_statement(statement: str) -> Optional[Tuple[str, str, str]]:
    """
    Parses index creation statements to extract:
    index name, table name, and target columns.
    E.g. CREATE INDEX idx_rental_customer ON rental (customer_id)
    Returns: (index_name, table_name, columns_str)
    """
    cleaned = " ".join(statement.split())
    # Regex matching CREATE [UNIQUE] INDEX index_name ON table_name (columns)
    match = re.search(
        r"create\s+(?:unique\s+)?index\s+([a-zA-Z0-9_]+)\s+on\s+([a-zA-Z0-9_]+)\s*\((.*?)\)",
        cleaned,
        re.IGNORECASE
    )
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None

def simulate_hypothetical_index(
    connector: DatabaseConnector,
    query: str,
    index_statement: str,
    dialect: str = "postgres"
) -> Optional[Dict[str, Any]]:
    """
    Appends pg_hint_plan hints to the query representing the proposed index,
    runs EXPLAIN on original and hinted queries, and returns before/after comparisons.
    """
    index_details = parse_create_index_statement(index_statement)
    if not index_details:
        return None

    idx_name, tbl_name, cols_str = index_details
    
    # Generate pg_hint_plan hint syntax:
    # /*+ IndexScan(table index_name) */
    hint = f"/*+ IndexScan({tbl_name} {idx_name}) */ "
    hinted_query = hint + query
    
    try:
        from app.parser import parse_postgresql_plan
        
        # Run EXPLAIN for original query
        original_plan_json = connector.execute_explain(query, use_analyze=False)
        # Run EXPLAIN for hinted query
        hinted_plan_json = connector.execute_explain(hinted_query, use_analyze=False)
        
        orig_node = parse_postgresql_plan(original_plan_json)
        hint_node = parse_postgresql_plan(hinted_plan_json)
        
        original_cost = orig_node.cost_total
        original_rows = orig_node.rows_estimated
        hinted_cost = hint_node.cost_total
        hinted_rows = hint_node.rows_estimated
        
        cost_reduction_percent = 0.0
        if original_cost > 0:
            cost_reduction_percent = round(((original_cost - hinted_cost) / original_cost) * 100, 2)
            
        return {
            "index_name": idx_name,
            "table_name": tbl_name,
            "columns": cols_str,
            "hinted_query": hinted_query,
            "original_cost": original_cost,
            "original_rows": original_rows,
            "hinted_cost": hinted_cost,
            "hinted_rows": hinted_rows,
            "cost_reduction_percent": cost_reduction_percent,
            "original_plan_json": original_plan_json,
            "hinted_plan_json": hinted_plan_json
        }
    except Exception:
        # If pg_hint_plan is missing or throws error, return gracefully
        return None
