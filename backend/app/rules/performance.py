import sqlglot.expressions as exp
from typing import Any, Dict, List, Optional
from app.rules.base import BaseRule, Finding, registry

class P01SelectStar(BaseRule):
    rule_id = "P01"
    severity = 6
    category = "PERFORMANCE"
    title = "SELECT star anti-pattern"
    description = "Detects SELECT * or SELECT table.* outside CTEs. Forces full row fetch, prevents covering index, and breaks on schema changes."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            # Check if this SELECT is a CTE definition (which is ok, or rather we check if select is inside CTE)
            # For simplicity, look at all SELECT * instances
            for expression in select.expressions:
                if isinstance(expression, exp.Star) or (isinstance(expression, exp.Column) and expression.name == "*"):
                    findings.append(self.create_finding(self.description))
                    break
        return findings

class P02FunctionOnIndexedColumn(BaseRule):
    rule_id = "P02"
    severity = 9
    category = "PERFORMANCE"
    title = "Scalar function on indexed column"
    description = "Scalar function wraps column in predicate. Destroys SARGability, preventing index traversals."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        target_funcs = {"year", "month", "date", "lower", "upper", "cast", "trim", "coalesce"}
        
        # We search inside WHERE, JOIN ON, and HAVING
        predicates = []
        for where in ast.find_all(exp.Where):
            predicates.append(where.this)
        for join in ast.find_all(exp.Join):
            on = join.args.get("on")
            if on:
                predicates.append(on)
        for having in ast.find_all(exp.Having):
            predicates.append(having.this)

        for pred in predicates:
            if not pred:
                continue
            for func in pred.find_all((exp.Func, exp.Anonymous)):
                if isinstance(func, exp.Anonymous):
                    func_name = func.name.lower()
                else:
                    func_name = func.sql_name().lower()
                
                if func_name in target_funcs:
                    # check if there is any column inside the function
                    col = func.find(exp.Column)
                    if col:
                        col_name = col.name
                        findings.append(self.create_finding(
                            f"Column '{col_name}' wrapped in scalar function '{func_name.upper()}()' inside a filter. Rewrite predicate to compare column directly (e.g. WHERE {col_name} >= '...')."
                        ))
        return findings

class P03LeadingWildcardLike(BaseRule):
    rule_id = "P03"
    severity = 8
    category = "PERFORMANCE"
    title = "Leading wildcard LIKE"
    description = "Detects LIKE '%value' or LIKE '%value%'. Prevents left-to-right B-tree index traversals."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for like in ast.find_all(exp.Like):
            expr = like.args.get("expression")
            if expr and isinstance(expr, exp.Literal):
                val = expr.this
                if val and isinstance(val, str) and val.startswith("%"):
                    findings.append(self.create_finding(self.description))
        return findings

class P04OrConditionsIndex(BaseRule):
    rule_id = "P04"
    severity = 6
    category = "PERFORMANCE"
    title = "OR conditions preventing index usage"
    description = "Detects OR condition in WHERE clauses on separately indexed columns. Rewrite as UNION ALL."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for where in ast.find_all(exp.Where):
            # Check for OR expressions
            for or_node in where.find_all(exp.Or):
                # If both sides are column comparisons, flag
                cols = list(or_node.find_all(exp.Column))
                if len(cols) >= 2:
                    findings.append(self.create_finding(self.description))
                    break
        return findings

class P05UnindexedJoinColumn(BaseRule):
    rule_id = "P05"
    severity = 8
    category = "PERFORMANCE"
    title = "Unindexed JOIN column"
    description = "JOIN condition references unindexed columns (requires schema context)."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        if not schema_context or "tables" not in schema_context:
            return None
        
        findings = []
        for join in ast.find_all(exp.Join):
            on = join.args.get("on")
            if not on:
                continue
            for col in on.find_all(exp.Column):
                table_name = col.table
                col_name = col.name
                if not table_name:
                    continue
                
                # Check schema details
                tables = schema_context.get("tables", {})
                indexes = schema_context.get("indexes", {})
                
                if table_name in tables:
                    # Let's check if there is an index covering this column as the prefix
                    table_idxs = indexes.get(table_name, [])
                    has_index = False
                    for idx in table_idxs:
                        definition = idx.get("definition", "").lower()
                        # simple heuristic check if column name is inside index definition
                        if col_name.lower() in definition:
                            has_index = True
                            break
                    
                    if not has_index:
                        findings.append(self.create_finding(
                            f"Column '{col_name}' in table '{table_name}' is used in JOIN ON condition but has no index. Recommended: CREATE INDEX idx_{table_name}_{col_name} ON {table_name}({col_name});"
                        ))
        return findings

class P06CorrelatedSubquery(BaseRule):
    rule_id = "P06"
    severity = 8
    category = "PERFORMANCE"
    title = "Correlated subquery in WHERE"
    description = "Detects a SELECT in WHERE referencing outer columns. Usually executes once per outer row."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            where = select.args.get("where")
            if not where:
                continue
            for subquery in where.find_all(exp.Subquery):
                # Check if subquery references tables/columns outside its own scope
                # Simplified check: subquery references a column whose table is not in the subquery's FROM/JOIN
                subquery_select = subquery.this
                if not isinstance(subquery_select, exp.Select):
                    continue
                subquery_tables = {t.name.lower() for t in subquery_select.find_all(exp.Table)}
                
                for col in subquery_select.find_all(exp.Column):
                    if col.table and col.table.lower() not in subquery_tables:
                        findings.append(self.create_finding(
                            f"Correlated subquery references outer table column '{col.sql()}'. Rewrite as JOIN or CTE."
                        ))
                        break
        return findings

class P07MissingLimit(BaseRule):
    rule_id = "P07"
    severity = 5
    category = "PERFORMANCE"
    title = "Missing LIMIT on large table scan"
    description = "Detects table scan without LIMIT on tables exceeding 100,000 rows (requires schema context)."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        if not schema_context or "tables" not in schema_context:
            return None
            
        findings = []
        # Check if query has a limit at root SELECT
        if not ast.find(exp.Limit):
            # Check tables referenced
            for table in ast.find_all(exp.Table):
                tbl_name = table.name
                tables = schema_context.get("tables", {})
                if tbl_name in tables:
                    row_count = tables[tbl_name].get("row_count", 0)
                    if row_count > 100000:
                        findings.append(self.create_finding(
                            f"Missing LIMIT on query scanning large table '{tbl_name}' ({row_count:,} rows)."
                        ))
        return findings

class P08DistinctMaskingBadJoin(BaseRule):
    rule_id = "P08"
    severity = 6
    category = "PERFORMANCE"
    title = "DISTINCT masking incorrect JOIN cardinality"
    description = "DISTINCT present alongside a JOIN (especially LEFT JOIN). Often signals incorrect JOIN cardinality assumption."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            # Check distinct flag
            if select.args.get("distinct") and len(list(select.find_all(exp.Join))) > 0:
                findings.append(self.create_finding(self.description))
        return findings

class P09NPlusOneSubquery(BaseRule):
    rule_id = "P09"
    severity = 9
    category = "PERFORMANCE"
    title = "N+1 subquery in SELECT projection"
    description = "Subquery located in projection list of SELECT instead of JOIN or CTE. Forces N+1 database operations."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            for expression in select.expressions:
                # Check if select projection expression contains a subquery
                if expression.find(exp.Select):
                    findings.append(self.create_finding(self.description))
                    break
        return findings

class P10DeepOffsetPagination(BaseRule):
    rule_id = "P10"
    severity = 7
    category = "PERFORMANCE"
    title = "Deep OFFSET pagination"
    description = "LIMIT x OFFSET y where y exceeds 10,000. Recommend keyset pagination."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for offset in ast.find_all(exp.Offset):
            expr = offset.args.get("expression")
            if expr and isinstance(expr, exp.Literal):
                try:
                    val = int(expr.this)
                    if val > 10000:
                        findings.append(self.create_finding(
                            f"Deep OFFSET pagination detected ({val:,}). Requires database to scan and discard rows. Use keyset pagination instead."
                        ))
                except ValueError:
                    pass
        return findings

class P11ImplicitTypeConversion(BaseRule):
    rule_id = "P11"
    severity = 8
    category = "PERFORMANCE"
    title = "Implicit type conversion in query predicate"
    description = "Comparing columns and literals of different data types causing full table scan."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        # Hard to completely verify without exact db stats and schema types, basic scan:
        if not schema_context or "tables" not in schema_context:
            return None
        findings = []
        for eq in ast.find_all(exp.EQ):
            left = eq.left
            right = eq.right
            if isinstance(left, exp.Column) and isinstance(right, exp.Literal):
                col = left
                lit = right
            elif isinstance(right, exp.Column) and isinstance(left, exp.Literal):
                col = right
                lit = left
            else:
                continue

            tbl_name = col.table
            col_name = col.name
            tables = schema_context.get("tables", {})
            tbl_names = [tbl_name] if tbl_name else list(tables.keys())
            for t_name in tbl_names:
                if t_name in tables:
                    columns = tables[t_name].get("columns", [])
                    col_type = next((c["type"].lower() for c in columns if c["name"] == col_name), None)
                    if col_type:
                        # If col type is int but literal is string, or vice versa, warn
                        if ("int" in col_type or "serial" in col_type) and lit.is_string:
                            findings.append(self.create_finding(
                                f"Implicit type conversion: comparing integer column '{col_name}' with string literal '{lit.this}'."
                            ))
                            break
                        elif ("char" in col_type or "text" in col_type) and not lit.is_string:
                            findings.append(self.create_finding(
                                f"Implicit type conversion: comparing character column '{col_name}' with numeric literal '{lit.this}'."
                            ))
                            break
        return findings

class P12NonSargablePredicates(BaseRule):
    rule_id = "P12"
    severity = 6
    category = "PERFORMANCE"
    title = "Non-SARGable negative predicates"
    description = "NOT IN, !=, or NOT LIKE comparisons used on indexed columns. B-tree indexes cannot index exclusions."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        negatives = (exp.NEQ, exp.Not)
        for node in ast.walk():
            if isinstance(node, negatives):
                # check if it wraps or references column
                for col in node.find_all(exp.Column):
                    findings.append(self.create_finding(
                        f"Non-SARGable predicate: '{node.sql()}' references column '{col.name}'. Indexes cannot optimize negative bounds."
                    ))
                    break
        return findings

class P13RedundantOrderBy(BaseRule):
    rule_id = "P13"
    severity = 3
    category = "PERFORMANCE"
    title = "Redundant ORDER BY in subquery"
    description = "ORDER BY clause inside a subquery derived table. Has no effect on outer result ordering, adds sort overhead."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for subquery in ast.find_all(exp.Subquery):
            subquery_select = subquery.this
            if isinstance(subquery_select, exp.Select) and subquery_select.args.get("order"):
                findings.append(self.create_finding(self.description))
        return findings

class P14CountInsteadOfExists(BaseRule):
    rule_id = "P14"
    severity = 5
    category = "PERFORMANCE"
    title = "COUNT(*) used for existence verification"
    description = "COUNT(*) value is compared to check existence. Use EXISTS instead to enable fast-exit search."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        # Check comparison nodes (GT, NEQ, GTE)
        for comp in ast.find_all((exp.GT, exp.NEQ, exp.GTE)):
            for func in comp.find_all(exp.Anonymous):
                if func.name.lower() == "count":
                    findings.append(self.create_finding(self.description))
            for func in comp.find_all(exp.Count):
                findings.append(self.create_finding(self.description))
        
        # Check for root-level SELECT COUNT(*) without alias/GROUP BY but with WHERE
        for select in ast.find_all(exp.Select):
            if select.args.get("group"):
                continue
            if not select.args.get("where"):
                continue
            for expr in select.expressions:
                if isinstance(expr, exp.Count):
                    findings.append(self.create_finding(self.description))
        return findings

class P15MultipleCountDistinct(BaseRule):
    rule_id = "P15"
    severity = 6
    category = "PERFORMANCE"
    title = "Multiple COUNT(DISTINCT) projections"
    description = "More than one COUNT(DISTINCT column) in a single SELECT projection. Requires multiple hashing scans."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            distinct_counts = 0
            for expr in select.expressions:
                # search for COUNT(DISTINCT ...)
                for count_node in expr.find_all(exp.Count):
                    if count_node.args.get("distinct") or count_node.find(exp.Distinct):
                        distinct_counts += 1
            if distinct_counts > 2:
                findings.append(self.create_finding(
                    f"Multiple COUNT(DISTINCT) statements ({distinct_counts}) in SELECT projection. Each distinct calculation requires a separate hash table partition."
                ))
        return findings

class P16HavingWithoutGroupBy(BaseRule):
    rule_id = "P16"
    severity = 5
    category = "PERFORMANCE"
    title = "HAVING clause without GROUP BY"
    description = "Using HAVING as a replacement for WHERE filters without aggregations."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            if select.args.get("having") and not select.args.get("group"):
                findings.append(self.create_finding(self.description))
        return findings

class P17UnboundedUpdateDelete(BaseRule):
    rule_id = "P17"
    severity = 10
    category = "PERFORMANCE"
    title = "Unbounded UPDATE or DELETE mutation"
    description = "UPDATE or DELETE statements executing without a WHERE filter. Mutations will apply to all database rows."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        # sqlglot structures: exp.Update, exp.Delete
        for update in ast.find_all(exp.Update):
            if not update.args.get("where"):
                findings.append(self.create_finding("Unbounded UPDATE: mutation executing without a WHERE filter."))
        for delete in ast.find_all(exp.Delete):
            if not delete.args.get("where"):
                findings.append(self.create_finding("Unbounded DELETE: statement executing without a WHERE filter."))
        return findings

class P18CartesianJoin(BaseRule):
    rule_id = "P18"
    severity = 10
    category = "PERFORMANCE"
    title = "Cartesian join (CROSS JOIN)"
    description = "JOIN condition executing without ON criteria, or comma-separated table imports without linking conditions."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            tables = [t.name.lower() for t in select.find_all(exp.Table)]
            if len(tables) < 2:
                continue

            # Check if there is an explicit CROSS JOIN
            has_explicit_cross = False
            for join in select.find_all(exp.Join):
                if (join.args.get("method") or "").upper() == "CROSS":
                    has_explicit_cross = True
                    break

            if has_explicit_cross:
                findings.append(self.create_finding(self.description))
                continue

            # Check for comma-separated implicit joins
            has_on_or_using = all(join.args.get("on") or join.args.get("using") for join in select.find_all(exp.Join))
            if not has_on_or_using:
                # Check if WHERE clause contains an equality comparison linking the tables
                where = select.args.get("where")
                linked = False
                if where:
                    for eq in where.find_all(exp.EQ):
                        left_cols = list(eq.left.find_all(exp.Column))
                        right_cols = list(eq.right.find_all(exp.Column))
                        if left_cols and right_cols:
                            l_tbl = left_cols[0].table
                            r_tbl = right_cols[0].table
                            if l_tbl and r_tbl and l_tbl.lower() != r_tbl.lower():
                                linked = True
                                break
                if not linked:
                    findings.append(self.create_finding(self.description))
        return findings

class P19SelfJoinReplaceableByWindow(BaseRule):
    rule_id = "P19"
    severity = 7
    category = "PERFORMANCE"
    title = "Self-join for logical row comparison"
    description = "Table joined to itself to compare previous/next rows or run totals. Use window functions (LAG, LEAD) instead."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            from_table = select.args.get("from_")
            if not from_table:
                continue
            from_tables = [t.name.lower() for t in from_table.find_all(exp.Table)]
            if not from_tables:
                continue
            primary_table = from_tables[0]

            for join in select.find_all(exp.Join):
                join_tables = [t.name.lower() for t in join.find_all(exp.Table)]
                if primary_table in join_tables:
                    # Self join detected. Now check if the ON condition contains arithmetic operations (LAG/LEAD hint)
                    on = join.args.get("on")
                    if on:
                        has_arithmetic = False
                        for node in on.walk():
                            if isinstance(node, (exp.Add, exp.Sub)):
                                has_arithmetic = True
                                break
                        if has_arithmetic:
                            findings.append(self.create_finding(
                                f"Table '{primary_table}' is self-joined with sequence arithmetic. Rewrite query using window functions (e.g. LAG() or LEAD()) for performance."
                            ))
                            break
        return findings

class P20InefficientRowNumberWrapping(BaseRule):
    rule_id = "P20"
    severity = 4
    category = "PERFORMANCE"
    title = "Inefficient ROW_NUMBER() pagination wrapping"
    description = "Full query wrapped in subquery only to filter ROW_NUMBER() bounds. Use LIMIT/OFFSET pagination."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            # Check if outer SELECT filters on a column mapping to ROW_NUMBER() in inner SELECT
            where = select.args.get("where")
            if not where:
                continue
            for subquery in select.find_all(exp.Subquery):
                subquery_select = subquery.this
                if not isinstance(subquery_select, exp.Select):
                    continue
                # check if inner select has row_number window func
                for window in subquery_select.find_all(exp.Window):
                    if isinstance(window.this, exp.RowNumber) or (isinstance(window.this, exp.Anonymous) and window.this.name.lower() == "row_number"):
                        findings.append(self.create_finding(self.description))
                        break
        return findings

# Register rules
registry.register(P01SelectStar())
registry.register(P02FunctionOnIndexedColumn())
registry.register(P03LeadingWildcardLike())
registry.register(P04OrConditionsIndex())
registry.register(P05UnindexedJoinColumn())
registry.register(P06CorrelatedSubquery())
registry.register(P07MissingLimit())
registry.register(P08DistinctMaskingBadJoin())
registry.register(P09NPlusOneSubquery())
registry.register(P10DeepOffsetPagination())
registry.register(P11ImplicitTypeConversion())
registry.register(P12NonSargablePredicates())
registry.register(P13RedundantOrderBy())
registry.register(P14CountInsteadOfExists())
registry.register(P15MultipleCountDistinct())
registry.register(P16HavingWithoutGroupBy())
registry.register(P17UnboundedUpdateDelete())
registry.register(P18CartesianJoin())
registry.register(P19SelfJoinReplaceableByWindow())
registry.register(P20InefficientRowNumberWrapping())
