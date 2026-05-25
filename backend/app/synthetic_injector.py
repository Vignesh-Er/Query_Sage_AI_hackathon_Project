import sqlglot
import sqlglot.expressions as exp
from typing import Any, Dict, Tuple, Optional, List
from app.connectors.base import DatabaseConnector

def inject_synthetic_parameters(
    sql: str, 
    dialect: str, 
    connector: DatabaseConnector
) -> Tuple[str, List[str]]:
    """
    Analyzes parameter placeholders in the query, queries stats for the referenced columns,
    substitutes most common values (MCVs), and returns the rewritten SQL and injection logs.
    """
    logs = []
    try:
        parsed = sqlglot.parse_one(sql, read=dialect)
    except Exception:
        return sql, ["Failed to parse query for parameter injection."]

    # Step 1: Find comparisons of Column and Parameter/Placeholder
    # Map placeholder names/positions to table/column names
    param_mappings = {}  # index or name -> (table, column)
    placeholder_nodes = []
    
    # We walk the tree and look for placeholder nodes
    for node in parsed.walk():
        # Placeholders in sqlglot: exp.Parameter (like :name), exp.Placeholder (like ?)
        if isinstance(node, (exp.Parameter, exp.Placeholder)):
            placeholder_nodes.append(node)
            parent = node.parent
            if isinstance(parent, (exp.EQ, exp.NE, exp.LT, exp.GT, exp.LTE, exp.GTE, exp.Like, exp.ILike)):
                # Left or right should be a Column
                col = parent.left if parent.right == node else parent.right
                if isinstance(col, exp.Column):
                    # Find table name
                    tbl_name = col.table
                    if not tbl_name:
                        # Find table from query tables if only one table is referenced
                        tables = list(parsed.find_all(exp.Table))
                        if len(tables) == 1:
                            tbl_name = tables[0].name
                    
                    if tbl_name:
                        # Map node identifier
                        param_mappings[node] = (tbl_name, col.name)

    if not param_mappings:
        return sql, []

    # Step 2: Query database catalog pg_stats for each mapped placeholder
    substitutions = {}
    for node, (tbl_name, col_name) in param_mappings.items():
        stats = connector.fetch_pg_stats(tbl_name, col_name)
        if stats and stats.get("most_common_vals"):
            mcvs = stats["most_common_vals"]
            freqs = stats.get("most_common_freqs", [0.0])
            
            # Extract first MCV
            # MCVs is usually a string representation of an array, e.g. "{4821, 5100}"
            # Let's clean it up
            val_str = str(mcvs)
            if val_str.startswith("{") and val_str.endswith("}"):
                vals = val_str[1:-1].split(",")
                val = vals[0].strip()
            else:
                val = val_str
                
            freq = freqs[0] if freqs else 0.0
            
            # Store replacement
            substitutions[node] = val
            logs.append(
                f"EXPLAIN was run with {col_name} = {val} (most common value, {freq:.1%} frequency) injected for parameter."
            )

    if not substitutions:
        return sql, []

    # Step 3: Mutate AST to replace nodes with literal values
    def mutate_nodes(node):
        if node in substitutions:
            val = substitutions[node]
            # Try to format as numeric or string literal
            try:
                # If numeric
                if val.isdigit():
                    return exp.Literal.number(val)
                float(val)
                return exp.Literal.number(val)
            except ValueError:
                # String literal
                return exp.Literal.string(val)
        return node

    rewritten_ast = parsed.transform(mutate_nodes)
    return rewritten_ast.sql(dialect=dialect), logs
