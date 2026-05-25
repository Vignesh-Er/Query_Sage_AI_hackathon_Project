import sqlglot.expressions as exp
from typing import Any, Dict, List, Optional
from app.rules.base import BaseRule, Finding, registry

class A01RecursiveCteLimit(BaseRule):
    rule_id = "A01"
    severity = 8
    category = "PERFORMANCE"
    title = "Recursive CTE without recursion limit guard"
    description = "Recursive CTE is missing a MAXRECURSION statement or depth control limit. Can cause infinite loops."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        with_node = ast.args.get("with_")
        if with_node and with_node.args.get("recursive"):
            for cte in with_node.expressions:
                cte_query = cte.this
                if not cte_query:
                    continue
                # Check for AST nodes indicating a guard
                has_guard = False
                if cte_query.find(exp.Where) or cte_query.find(exp.Limit):
                    has_guard = True
                else:
                    cte_sql = cte_query.sql().lower()
                    if any(x in cte_sql for x in ["maxrecursion", "depth", "level", "limit", "<", ">", "<=", ">="]):
                        has_guard = True
                
                if not has_guard:
                    findings.append(self.create_finding(self.description))
        return findings

class A02JsonWithoutExpressionIndex(BaseRule):
    rule_id = "A02"
    severity = 7
    category = "INDEX"
    title = "JSON query path without expression index"
    description = "Query filters on JSON paths in WHERE but has no expression index. Forces slow JSON parsing scans on every row."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        # JSON extraction operators in sqlglot: exp.JSONExtract, exp.JSONExtractScalar, etc.
        # Or look for operators like ->, ->>, #>
        for node in ast.find_all(exp.Where):
            for json_node in node.find_all((exp.JSONExtract, exp.JSONExtractScalar)):
                findings.append(self.create_finding(self.description))
                break
        return findings

class A03IlikeLargeText(BaseRule):
    rule_id = "A03"
    severity = 6
    category = "PERFORMANCE"
    title = "Case-insensitive ILIKE pattern match"
    description = "ILIKE comparison used on columns. Forces full table scans. Use expression functional indexes (LOWER) or Full-Text search instead."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        # In sqlglot, ILIKE is represented as ILike or a custom operator
        for ilike in ast.find_all(exp.ILike):
            findings.append(self.create_finding(self.description))
        return findings

class A04InsertWithoutReturning(BaseRule):
    rule_id = "A04"
    severity = 3
    category = "STYLE"
    title = "INSERT executed without RETURNING clause"
    description = "INSERT statement does not use RETURNING to retrieve auto-generated IDs. Avoids executing secondary SELECTs."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for insert in ast.find_all(exp.Insert):
            # Check if insert query contains RETURNING expression (Postgres style)
            if not insert.args.get("returning"):
                findings.append(self.create_finding(self.description))
        return findings

class A05LockEscalationRisk(BaseRule):
    rule_id = "A05"
    severity = 7
    category = "LOCKING"
    title = "Lock escalation risk on UPDATE"
    description = "UPDATE command with non-indexed filter columns. Can lock the entire table and block concurrent transactions."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        if not schema_context or "tables" not in schema_context:
            return None
            
        findings = []
        for update in ast.find_all(exp.Update):
            where = update.args.get("where")
            if not where:
                continue
                
            tbl_name = ""
            # Extract target table name from update expression
            tbl = update.this
            if isinstance(tbl, exp.Table):
                tbl_name = tbl.name
            
            if not tbl_name:
                continue
                
            filter_cols = [col.name.lower() for col in where.find_all(exp.Column)]
            if not filter_cols:
                continue
                
            # Check if any filter column is indexed
            table_indexes = schema_context.get("indexes", {}).get(tbl_name, [])
            has_indexed_filter = False
            for idx in table_indexes:
                defn = idx.get("definition", "").lower()
                if any(c in defn for c in filter_cols):
                    has_indexed_filter = True
                    break
                    
            if not has_indexed_filter:
                findings.append(self.create_finding(
                    f"UPDATE statement on table '{tbl_name}' filters on unindexed columns ({filter_cols}). High risk of lock escalation."
                ))
        return findings

# Register rules
registry.register(A01RecursiveCteLimit())
registry.register(A02JsonWithoutExpressionIndex())
registry.register(A03IlikeLargeText())
registry.register(A04InsertWithoutReturning())
registry.register(A05LockEscalationRisk())
