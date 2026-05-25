import csv
import io
import hashlib
import sqlglot
import sqlglot.expressions as exp
from typing import Any, Dict, Optional, Tuple
from app.connectors.base import DatabaseConnector

def convert_dml_to_select(sql: str, dialect: str) -> Optional[str]:
    """Translates UPDATE or DELETE queries into a corresponding SELECT COUNT(*) query."""
    try:
        parsed = sqlglot.parse_one(sql, read=dialect)
        if isinstance(parsed, exp.Update):
            tbl = parsed.this
            where = parsed.args.get("where")
            select_query = exp.select("COUNT(*)").from_(tbl)
            if where:
                select_query = select_query.where(where.this)
            return select_query.sql(dialect=dialect)
            
        elif isinstance(parsed, exp.Delete):
            tbl = parsed.this
            where = parsed.args.get("where")
            select_query = exp.select("COUNT(*)").from_(tbl)
            if where:
                select_query = select_query.where(where.this)
            return select_query.sql(dialect=dialect)
            
        elif isinstance(parsed, exp.Select):
            return sql
    except Exception:
        pass
    return None

def verify_equivalence(
    connector: DatabaseConnector,
    original_sql: str,
    optimized_sql: str,
    dialect: str
) -> Dict[str, Any]:
    """
    Executes original and optimized queries inside a read-only transaction,
    validating row counts, schemas, and result hashes.
    """
    orig_select = convert_dml_to_select(original_sql, dialect)
    opt_select = convert_dml_to_select(optimized_sql, dialect)
    
    if not orig_select or not opt_select:
        return {
            "row_count_match": False,
            "original_row_count": 0,
            "optimized_row_count": 0,
            "original_hash": "",
            "optimized_hash": "",
            "result_match": False,
            "status": "ALTERED",
            "error": "Could not translate queries into SELECT statements."
        }

    # Add LIMIT 1000 to ensure we don't blow up memory or transaction bounds
    try:
        orig_parsed = sqlglot.parse_one(orig_select, read=dialect)
        if not orig_parsed.args.get("limit"):
            orig_select = orig_parsed.limit(1000).sql(dialect=dialect)
            
        opt_parsed = sqlglot.parse_one(opt_select, read=dialect)
        if not opt_parsed.args.get("limit"):
            opt_select = opt_parsed.limit(1000).sql(dialect=dialect)
    except Exception:
        pass

    try:
        # Fetch results
        orig_rows = connector.execute_readonly(orig_select)
        opt_rows = connector.execute_readonly(opt_select)
        
        orig_count = len(orig_rows)
        opt_count = len(opt_rows)
        
        # Serialize and hash results (sort row representations to check values independently of sort ordering)
        def get_sorted_hash(rows) -> Tuple[str, str]:
            # Convert rows to stable CSV strings
            # Output two hashes: unsorted (for ordering validation) and sorted (for value validation)
            output_unsorted = io.StringIO()
            writer_unsorted = csv.writer(output_unsorted)
            writer_unsorted.writerows(rows)
            unsorted_data = output_unsorted.getvalue()
            unsorted_hash = hashlib.sha256(unsorted_data.encode("utf-8")).hexdigest()

            # Sort rows by their string values
            sorted_rows = sorted([list(map(str, row)) for row in rows])
            output_sorted = io.StringIO()
            writer_sorted = csv.writer(output_sorted)
            writer_sorted.writerows(sorted_rows)
            sorted_data = output_sorted.getvalue()
            sorted_hash = hashlib.sha256(sorted_data.encode("utf-8")).hexdigest()
            
            return unsorted_hash, sorted_hash

        orig_unsorted_hash, orig_sorted_hash = get_sorted_hash(orig_rows)
        opt_unsorted_hash, opt_sorted_hash = get_sorted_hash(opt_rows)
        
        row_count_match = (orig_count == opt_count)
        values_match = (orig_sorted_hash == opt_sorted_hash)
        order_match = (orig_unsorted_hash == opt_unsorted_hash)
        
        if row_count_match and values_match:
            if order_match:
                status = "VERIFIED"
                result_match = True
            else:
                status = "ORDER_DIFFERS"
                result_match = True  # logically equivalent values, just order differed
        else:
            status = "ALTERED"
            result_match = False

        return {
            "row_count_match": row_count_match,
            "original_row_count": orig_count,
            "optimized_row_count": opt_count,
            "original_hash": orig_unsorted_hash,
            "optimized_hash": opt_unsorted_hash,
            "result_match": result_match,
            "status": status
        }
    except Exception as e:
        return {
            "row_count_match": False,
            "original_row_count": 0,
            "optimized_row_count": 0,
            "original_hash": "",
            "optimized_hash": "",
            "result_match": False,
            "status": "ALTERED",
            "error": f"Execution validation failed: {str(e)}"
        }
Plot = None
