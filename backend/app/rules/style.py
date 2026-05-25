import re
import sqlglot.expressions as exp
from typing import Any, Dict, List, Optional
from app.rules.base import BaseRule, Finding, registry

class S01ImplicitInsertColumns(BaseRule):
    rule_id = "S01"
    severity = 7
    category = "STYLE"
    title = "Implicit INSERT column definition list"
    description = "INSERT INTO table VALUES (...) executes without defining column names. Breaks on database schema updates."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for insert in ast.find_all(exp.Insert):
            # In sqlglot, Insert args has 'this' which contains the Table, and the insert column list can be in 'this' or other keys
            # Let's check if columns are specified
            cols = insert.args.get("this")
            if isinstance(cols, exp.Schema):
                # if Schema has columns, it's defined
                if not cols.expressions:
                    findings.append(self.create_finding(self.description))
            elif isinstance(cols, exp.Table):
                # Table alone has no columns defined in schema
                # Check if it has a list of columns
                # Typically sqlglot structures INSERT as Insert(this=Schema(this=Table, expressions=[...])) or Insert(this=Table)
                if not insert.args.get("expression") or isinstance(insert.this, exp.Table):
                    # check if insert contains VALUES without column names
                    findings.append(self.create_finding(self.description))
        return findings

class S02HardcodedLiteralsInFilters(BaseRule):
    rule_id = "S02"
    severity = 3
    category = "STYLE"
    title = "Hardcoded values should be parameterized"
    description = "Query contains hardcoded literals in filters (emails, phones, dates, or IDs). Parameterize inputs to enable plan caching."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
        phone_regex = re.compile(r"^\+?[1-9]\d{1,14}$") # E.164
        
        predicates = list(ast.find_all(exp.Where)) + list(ast.find_all(exp.Having))
        for pred in predicates:
            for lit in pred.find_all(exp.Literal):
                val = str(lit.this)
                # Check for indicators: email, phone, date or long digits
                if lit.is_string:
                    if email_regex.match(val):
                        findings.append(self.create_finding("Hardcoded email literal found. Parameterize value."))
                    elif phone_regex.match(val):
                        findings.append(self.create_finding("Hardcoded phone number literal found. Parameterize value."))
                    elif len(val) == 10 and "-" in val: # date check yyyy-mm-dd
                        findings.append(self.create_finding("Hardcoded date string literal found. Parameterize value."))
                else:
                    # check numeric ID (high integers)
                    try:
                        num = int(val)
                        if num > 100000:
                            findings.append(self.create_finding(f"Hardcoded large numeric ID '{val}' found. Parameterize value."))
                    except ValueError:
                        pass
        return findings

class S03ExcessiveNesting(BaseRule):
    rule_id = "S03"
    severity = 5
    category = "STYLE"
    title = "Excessive query nesting levels"
    description = "Subqueries nested more than three levels deep. Decreases code readability and maintainability. Rewrite using CTEs."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        
        def check_depth(node, current_depth):
            if current_depth > 3:
                return True
            for child in node.walk(prune=lambda n: isinstance(n, (exp.Subquery, exp.Select)) and n != node):
                if child != node and isinstance(child, (exp.Subquery, exp.Select)):
                    if check_depth(child, current_depth + 1):
                        return True
            return False

        if check_depth(ast, 1):
            findings.append(self.create_finding(self.description))
        return findings

class S04UnreferencedCTE(BaseRule):
    rule_id = "S04"
    severity = 3
    category = "STYLE"
    title = "Unreferenced CTE declaration"
    description = "CTE defined but never referenced in query select statement. Adds dead code."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        # Check CTEs
        with_node = ast.find(exp.With)
        if with_node:
            ctes = with_node.expressions
            cte_names = {cte.alias_or_name.lower() for cte in ctes}
            
            # Find all references in the main body (excluding CTE declarations themselves)
            referenced = set()
            for table in ast.find_all(exp.Table):
                # Check if this table reference is inside a CTE's definition
                # If the table is inside a CTE, we only count it as a reference if it references another CTE
                parent = table.parent
                is_inside_cte_def = False
                while parent and parent != ast:
                    if isinstance(parent, exp.CTE):
                        is_inside_cte_def = True
                        break
                    parent = parent.parent
                
                tbl_name = table.name.lower()
                if tbl_name in cte_names:
                    referenced.add(tbl_name)
                    
            unreferenced = cte_names - referenced
            for cte_name in unreferenced:
                findings.append(self.create_finding(
                    f"CTE '{cte_name}' is declared but never referenced in query. Clean up dead code."
                ))
        return findings

class S05RedundantJoin(BaseRule):
    rule_id = "S05"
    severity = 5
    category = "STYLE"
    title = "Redundant JOIN with no columns selected"
    description = "Table included in JOIN but none of its columns appear in SELECT, WHERE, or HAVING. Unnecessary join overhead."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            joins = list(select.find_all(exp.Join))
            if not joins:
                continue
                
            # Collect all table aliases in JOIN
            join_aliases = {}
            for join in joins:
                tbl = join.this
                alias = tbl.alias_or_name
                if alias:
                    join_aliases[alias.lower()] = tbl.name
            
            if not join_aliases:
                continue

            # Check if columns from these aliases are referenced in SELECT, WHERE, HAVING
            referenced_aliases = set()
            
            # 1. Check select expressions
            for expr in select.expressions:
                for col in expr.find_all(exp.Column):
                    if col.table:
                        referenced_aliases.add(col.table.lower())
            
            # 2. Check WHERE
            where = select.args.get("where")
            if where:
                for col in where.find_all(exp.Column):
                    if col.table:
                        referenced_aliases.add(col.table.lower())
                        
            # 3. Check HAVING
            having = select.args.get("having")
            if having:
                for col in having.find_all(exp.Column):
                    if col.table:
                        referenced_aliases.add(col.table.lower())

            # Check if JOIN ON predicate uses columns from join table (which it should, but does that count as 'used'?)
            # If ONLY used in JOIN ON condition and nowhere else, it is redundant because it returns no data
            # and filters or duplicates rows, which should be done via EXISTS or rewrite.
            unreferenced = set(join_aliases.keys()) - referenced_aliases
            for alias in unreferenced:
                tbl_name = join_aliases[alias]
                findings.append(self.create_finding(
                    f"Redundant JOIN: Table '{tbl_name}' (alias '{alias}') is joined, but no columns from it are selected or filtered."
                ))
        return findings

class S06MixedJoinSyntax(BaseRule):
    rule_id = "S06"
    severity = 2
    category = "STYLE"
    title = "Mixed JOIN syntax patterns"
    description = "Mixed usage of old comma-separated join syntax and ANSI-SQL JOIN keyword in the same query."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        for select in ast.find_all(exp.Select):
            joins = list(select.find_all(exp.Join))
            if len(joins) < 2:
                continue
                
            has_comma_join = False
            has_ansi_join = False
            for join in joins:
                method = (join.args.get("method") or "").upper()
                if not join.args.get("on") and not join.args.get("using") and method != "CROSS":
                    has_comma_join = True
                else:
                    has_ansi_join = True
            
            if has_comma_join and has_ansi_join:
                findings.append(self.create_finding(self.description))
        return findings

class S07ComplexUncommentedQuery(BaseRule):
    rule_id = "S07"
    severity = 1
    category = "STYLE"
    title = "Complex query lacking comments"
    description = "Query length exceeds 50 AST nodes/tokens and contains no inline SQL comments. Inefficient for maintainability."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        findings = []
        # Count tokens/nodes in AST
        nodes_count = sum(1 for _ in ast.walk())
        if nodes_count > 50:
            # Check if comments are present in query
            # sqlglot attachments can have comments. Or check raw query if accessible.
            # We can check AST comments attribute
            has_comments = False
            for node in ast.walk():
                if node.comments:
                    has_comments = True
                    break
            if not has_comments:
                findings.append(self.create_finding(self.description))
        return findings

# Register rules
registry.register(S01ImplicitInsertColumns())
registry.register(S02HardcodedLiteralsInFilters())
registry.register(S03ExcessiveNesting())
registry.register(S04UnreferencedCTE())
registry.register(S05RedundantJoin())
registry.register(S06MixedJoinSyntax())
registry.register(S07ComplexUncommentedQuery())
