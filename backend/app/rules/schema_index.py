import sqlglot.expressions as exp
from typing import Any, Dict, List, Optional
from app.rules.base import BaseRule, Finding, registry

class I01CoveringIndexOpportunity(BaseRule):
    rule_id = "I01"
    severity = 7
    category = "INDEX"
    title = "Covering index opportunity"
    description = "Query filters on column A and selects columns A, B, C from same table with no covering index."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        if not schema_context or "tables" not in schema_context:
            return None
            
        findings = []
        for select in ast.find_all(exp.Select):
            # Find tables in from/join
            for tbl in select.find_all(exp.Table):
                tbl_name = tbl.name
                if tbl_name not in schema_context["tables"]:
                    continue
                
                # Check columns selected from this table
                selected_cols = set()
                for expr in select.expressions:
                    for col in expr.find_all(exp.Column):
                        if not col.table or col.table.lower() == tbl_name.lower():
                            selected_cols.add(col.name.lower())
                            
                # Check columns filtered (WHERE)
                filter_cols = set()
                where = select.args.get("where")
                if where:
                    for col in where.find_all(exp.Column):
                        if not col.table or col.table.lower() == tbl_name.lower():
                            filter_cols.add(col.name.lower())
                
                if not filter_cols or not selected_cols:
                    continue
                
                # Check if there is an index covering filters + selected columns
                table_indexes = schema_context.get("indexes", {}).get(tbl_name, [])
                has_covering = False
                all_cols = filter_cols.union(selected_cols)
                
                for idx in table_indexes:
                    defn = idx.get("definition", "").lower()
                    # If all required columns are in index definition, it could be covering
                    if all(c in defn for c in all_cols):
                        has_covering = True
                        break
                        
                if not has_covering and len(all_cols) <= 4:
                    col_list = ", ".join(all_cols)
                    findings.append(self.create_finding(
                        f"Covering index opportunity on table '{tbl_name}' for columns: ({col_list}). This would allow an index-only scan."
                    ))
        return findings

class I02IndexPrefixMismatch(BaseRule):
    rule_id = "I02"
    severity = 8
    category = "INDEX"
    title = "Composite index prefix mismatch"
    description = "Composite index exists on (A, B, C) but WHERE filters only on B or C, omitting prefix column A."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        if not schema_context or "indexes" not in schema_context:
            return None
            
        findings = []
        for select in ast.find_all(exp.Select):
            where = select.args.get("where")
            if not where:
                continue
                
            filter_cols = {col.name.lower() for col in where.find_all(exp.Column)}
            
            for tbl in select.find_all(exp.Table):
                tbl_name = tbl.name
                table_idxs = schema_context.get("indexes", {}).get(tbl_name, [])
                
                for idx in table_idxs:
                    defn = idx.get("definition", "").lower()
                    # Parse index columns from definition, e.g. "create index idx on tbl (col_a, col_b)"
                    # Very simple regex-like extraction of parenthesis contents
                    if "(" in defn and ")" in defn:
                        cols_str = defn.split("(")[-1].split(")")[0]
                        idx_cols = [c.strip().replace("`", "").replace("\"", "") for c in cols_str.split(",")]
                        
                        if len(idx_cols) > 1:
                            prefix_col = idx_cols[0].lower()
                            other_cols = [c.lower() for c in idx_cols[1:]]
                            
                            # If we filter on B or C, but NOT on A
                            if any(c in filter_cols for c in other_cols) and prefix_col not in filter_cols:
                                findings.append(self.create_finding(
                                    f"Composite index '{idx.get('name')}' on table '{tbl_name}' ({cols_str}) prefix mismatch: predicate filters on columns {list(filter_cols)} but misses prefix column '{prefix_col}'."
                                ))
        return findings

class I03DuplicateOrRedundantIndex(BaseRule):
    rule_id = "I03"
    severity = 5
    category = "INDEX"
    title = "Duplicate or redundant index defined"
    description = "Redundant index defined (e.g. index on (A) exists when composite index on (A, B) already exists)."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        # This is a schema-level check. It does not inspect the SQL query AST itself,
        # but queries the schema context directly. We only run it once per context.
        if not schema_context or "indexes" not in schema_context:
            return None
            
        findings = []
        for tbl_name, idxs in schema_context.get("indexes", {}).items():
            parsed_idxs = []
            for idx in idxs:
                defn = idx.get("definition", "").lower()
                if "(" in defn and ")" in defn:
                    cols_str = defn.split("(")[-1].split(")")[0]
                    cols = [c.strip().replace("`", "").replace("\"", "") for c in cols_str.split(",")]
                    parsed_idxs.append((idx.get("name"), cols))
            
            # Compare index column sequences
            for i, (name_a, cols_a) in enumerate(parsed_idxs):
                for j, (name_b, cols_b) in enumerate(parsed_idxs):
                    if i == j:
                        continue
                    # If index A is a prefix of index B: index A is redundant
                    if len(cols_a) < len(cols_b) and cols_b[:len(cols_a)] == cols_a:
                        findings.append(self.create_finding(
                            f"Redundant index: index '{name_a}' on table '{tbl_name}' ({cols_a}) is a prefix of index '{name_b}' ({cols_b}). index '{name_a}' can be safely dropped."
                        ))
        return findings

class I04TableWithoutPrimaryKey(BaseRule):
    rule_id = "I04"
    severity = 6
    category = "INDEX"
    title = "Table lacks primary key definition"
    description = "Table lacks a primary key. Can cause severe replication lag and slows down row lookups."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        if not schema_context or "tables" not in schema_context:
            return None
            
        findings = []
        for tbl in ast.find_all(exp.Table):
            tbl_name = tbl.name
            tables = schema_context.get("tables", {})
            if tbl_name in tables:
                pks = tables[tbl_name].get("primary_key", [])
                if not pks:
                    findings.append(self.create_finding(
                        f"Table '{tbl_name}' lacks a primary key definition."
                    ))
        return findings

class I05OverlyWideIndex(BaseRule):
    rule_id = "I05"
    severity = 4
    category = "INDEX"
    title = "Overly wide index definition"
    description = "Index spans more than 4 columns or exceeds 200 bytes. Slows down write operations."

    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        if not schema_context or "indexes" not in schema_context:
            return None
            
        findings = []
        for tbl_name, idxs in schema_context.get("indexes", {}).items():
            for idx in idxs:
                defn = idx.get("definition", "").lower()
                if "(" in defn and ")" in defn:
                    cols_str = defn.split("(")[-1].split(")")[0]
                    cols = [c.strip() for c in cols_str.split(",")]
                    if len(cols) > 4:
                        findings.append(self.create_finding(
                            f"Index '{idx.get('name')}' on table '{tbl_name}' is overly wide (spans {len(cols)} columns). Limit indexes to <= 4 columns."
                        ))
        return findings

# Register rules
registry.register(I01CoveringIndexOpportunity())
registry.register(I02IndexPrefixMismatch())
registry.register(I03DuplicateOrRedundantIndex())
registry.register(I04TableWithoutPrimaryKey())
registry.register(I05OverlyWideIndex())
