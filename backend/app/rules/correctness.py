import sqlglot.expressions as exp
from typing import Any, Dict, List, Optional
from app.rules.base import BaseRule, Finding, registry

class C01NullComparisonEquals(BaseRule):
    rule_id = "C01"
    severity = 8
    category = "CORRECTNESS"
    title = "NULL comparison using equality operator"
    description = "Detects comparison checks like column = NULL or column != NULL. Always evaluates to FALSE. Use IS NULL or IS NOT NULL instead."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for eq in ast.find_all((exp.EQ, exp.NEQ)):
            left = eq.left
            right = eq.right
            if isinstance(left, exp.Null) or isinstance(right, exp.Null):
                findings.append(self.create_finding(self.description))
        return findings

class C02OuterJoinNullabilityIgnored(BaseRule):
    rule_id = "C02"
    severity = 7
    category = "CORRECTNESS"
    title = "LEFT JOIN nullability filtered in WHERE"
    description = "LEFT JOIN column is filtered in WHERE without checking for NULL. Unintentionally converts LEFT JOIN to INNER JOIN."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            left_joined_tables = set()
            for join in select.find_all(exp.Join):
                if join.args.get("side") == "LEFT":
                    # extract table name/alias
                    tbl = join.this
                    alias = tbl.alias_or_name
                    if alias:
                        left_joined_tables.add(alias.lower())

            if not left_joined_tables:
                continue

            where = select.args.get("where")
            if where:
                for col in where.find_all(exp.Column):
                    if col.table and col.table.lower() in left_joined_tables:
                        # Check if column is wrapped in IS NULL or IS NOT NULL, which is fine.
                        # If it is in direct comparison (e.g. column = 5 or column != 10), it filters NULLs.
                        parent = col.parent
                        is_guarded = False
                        # Walk up to check if wrapped in Null checks or OR
                        while parent and parent != where:
                            if isinstance(parent, (exp.Null, exp.Is)):
                                is_guarded = True
                                break
                            parent = parent.parent
                        
                        if not is_guarded:
                            findings.append(self.create_finding(
                                f"LEFT JOIN table alias '{col.table}' column '{col.name}' is filtered in WHERE without NULL guards. This implicitly converts the LEFT JOIN to an INNER JOIN."
                            ))
                            break
        return findings

class C03NonDeterministicOrderBy(BaseRule):
    rule_id = "C03"
    severity = 4
    category = "CORRECTNESS"
    title = "Non-deterministic ORDER BY sort keys"
    description = "All ORDER BY sort keys can have duplicate values. Results in undefined ordering across query runs."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        # Checked primarily for paginated queries (with LIMIT or OFFSET)
        findings = []
        for select in ast.find_all(exp.Select):
            limit = select.args.get("limit")
            order = select.args.get("order")
            if limit and order:
                # If ordering columns is small (e.g., ordering by status, category, date), warn about uniqueness
                cols = [col.name.lower() for col in order.find_all(exp.Column)]
                non_deterministic_indicators = {"status", "category", "type", "created_date", "date"}
                
                # Check schema keys if available
                has_unique_key = False
                if schema_context and "tables" in schema_context:
                    # check referenced tables PKs
                    for tbl in select.find_all(exp.Table):
                        tbl_name = tbl.name
                        tables = schema_context.get("tables", {})
                        if tbl_name in tables:
                            pks = {pk.lower() for pk in tables[tbl_name].get("primary_key", [])}
                            # If primary key is in order columns, then it is deterministic
                            if pks and pks.intersection(cols):
                                has_unique_key = True
                                break
                
                if not has_unique_key and any(c in non_deterministic_indicators for c in cols):
                    # Flag if ordering does not appear to contain unique elements
                    findings.append(self.create_finding(
                        "Pagination query sorted on non-unique columns. Ordering is non-deterministic. Add a unique column (like primary key) to ORDER BY."
                    ))
        return findings

class C04UnionInsteadOfUnionAll(BaseRule):
    rule_id = "C04"
    severity = 4
    category = "CORRECTNESS"
    title = "UNION instead of UNION ALL"
    description = "UNION used instead of UNION ALL. UNION forces performance-costly deduplication checks. Use UNION ALL if duplicates are acceptable."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for union in ast.find_all(exp.Union):
            # sqlglot representation: Union distinct=True/False
            if not union.args.get("distinct") == False: # In sqlglot Distinct defaults to true if distinct=True or distinct is not set
                # UNION ALL is represented as Distinct = False
                findings.append(self.create_finding(self.description))
        return findings

class C05TimezoneUnawareDate(BaseRule):
    rule_id = "C05"
    severity = 6
    category = "CORRECTNESS"
    title = "Timezone-unaware date functions"
    description = "Detects usage of NOW() or GETDATE() without explicit timezone conversions. Can cause offset anomalies across regions."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        tz_unaware_funcs = {"now", "getdate", "current_timestamp"}
        for func in ast.find_all(exp.Func):
            if isinstance(func, exp.Anonymous):
                func_name = func.name.lower()
            else:
                func_name = func.sql_name().lower()
            if func_name in tz_unaware_funcs:
                # Check if wrapped in timezone conversions
                parent = func.parent
                has_tz = False
                while parent and parent != ast:
                    parent_name = ""
                    if isinstance(parent, exp.Anonymous):
                        parent_name = parent.name.lower()
                    elif isinstance(parent, exp.Func):
                        parent_name = parent.sql_name().lower()
                    
                    if any(x in parent_name for x in {"timezone", "convert_tz", "at_time_zone", "at time zone"}):
                        has_tz = True
                        break
                    parent = parent.parent
                if not has_tz:
                    findings.append(self.create_finding(
                        f"Timezone-unaware datetime function '{func_name.upper()}()' used. Cast to UTC explicitly to prevent server region offset anomalies."
                    ))
        return findings

class C06DivisionWithoutZeroGuard(BaseRule):
    rule_id = "C06"
    severity = 7
    category = "CORRECTNESS"
    title = "Division without zero check"
    description = "Division operator used without zero guard. Can crash query execution with 'division by zero' errors."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for div in ast.find_all((exp.Div, exp.DPipe)): # DPipe or Div
            right = div.right
            if not right:
                continue
            # Check if right side is guarded by NULLIF or CASE
            is_guarded = False
            for func in right.find_all(exp.Func):
                if func.sql_name().lower() == "nullif":
                    is_guarded = True
                    break
            if not is_guarded and not isinstance(right, exp.Literal):
                findings.append(self.create_finding(
                    "Division operator used without NULLIF() or zero guard. Wrap the divisor in NULLIF(divisor, 0) to avoid division-by-zero crashes."
                ))
        return findings

class C07MySQLPermissiveGroupBy(BaseRule):
    rule_id = "C07"
    severity = 9
    category = "CORRECTNESS"
    title = "MySQL non-deterministic GROUP BY projections"
    description = "SELECT projections contain columns not in GROUP BY and not wrapped in aggregate functions. Returns arbitrary row values."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            group = select.args.get("group")
            if not group:
                continue
            group_cols = {col.name.lower() for col in group.find_all(exp.Column)}
            
            for expr in select.expressions:
                # Get columns in this projection
                cols = list(expr.find_all(exp.Column))
                if not cols:
                    continue
                
                # Check if columns are grouped or inside aggregates
                for col in cols:
                    col_name = col.name.lower()
                    if col_name not in group_cols:
                        # Check if it is wrapped in an aggregate function
                        parent = col.parent
                        is_aggregated = False
                        while parent and parent != select:
                            # Aggregate function checks
                            if isinstance(parent, (exp.Count, exp.Sum, exp.Max, exp.Min, exp.Avg)):
                                is_aggregated = True
                                break
                            if isinstance(parent, exp.Anonymous) and parent.name.lower() in {"count", "sum", "max", "min", "avg", "group_concat"}:
                                is_aggregated = True
                                break
                            parent = parent.parent
                            
                        if not is_aggregated:
                            findings.append(self.create_finding(
                                f"Non-deterministic aggregation: SELECT column '{col.name}' is not in GROUP BY and is not wrapped in an aggregate function."
                            ))
                            break
        return findings

# Register rules
registry.register(C01NullComparisonEquals())
registry.register(C02OuterJoinNullabilityIgnored())
registry.register(C03NonDeterministicOrderBy())
registry.register(C04UnionInsteadOfUnionAll())
registry.register(C05TimezoneUnawareDate())
registry.register(C06DivisionWithoutZeroGuard())
registry.register(C07MySQLPermissiveGroupBy())
