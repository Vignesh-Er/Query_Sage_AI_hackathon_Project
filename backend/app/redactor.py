import copy
from typing import Any, Dict, List, Tuple

class DataClassifier:
    SENSITIVE_COLUMNS = [
        "ssn", "social_security", "sin", "passport", "credit_card", "card_number", 
        "cvv", "patient_id", "medical_record", "health_plan", "diagnosis", 
        "salary", "compensation", "payroll", "bank_account", "routing_number", 
        "dob", "date_of_birth", "biometric", "email", "phone", "password"
    ]
    SENSITIVE_TABLES = [
        "patients", "employees_sensitive", "payroll", "medical_records", 
        "financial_records", "pii", "gdpr_data", "users", "customers", "patient"
    ]

    @classmethod
    def is_sensitive_column(cls, name: str) -> bool:
        name_lower = name.lower()
        return any(indicator in name_lower for indicator in cls.SENSITIVE_COLUMNS)

    @classmethod
    def is_sensitive_table(cls, name: str) -> bool:
        name_lower = name.lower()
        return any(indicator in name_lower for indicator in cls.SENSITIVE_TABLES)

def redact_schema_excerpt(
    schema_excerpt: Dict[str, Any]
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Scans table and column names in the schema excerpt, and replaces sensitive indicators
    with consistent anonymous placeholders. Returns the sanitized schema and logs.
    """
    redacted = copy.deepcopy(schema_excerpt)
    logs = []
    
    # Track mappings to apply consistency across tables, columns, indexes, keys
    table_mappings = {}
    column_mappings = {}  # (table_name, col_name) -> alias

    tables = redacted.get("tables", {})
    indexes = redacted.get("indexes", {})

    # Step 1: Detect and build mappings for tables
    table_counter = 1
    for tbl_name in list(tables.keys()):
        if DataClassifier.is_sensitive_table(tbl_name):
            alias = f"pii_table_{table_counter}"
            table_mappings[tbl_name] = alias
            table_counter += 1
            logs.append(f"Table '{tbl_name}' was anonymized as '{alias}'.")

    # Step 2: Detect and build mappings for columns
    for tbl_name, tbl_info in tables.items():
        col_counter = 1
        cols_list = tbl_info.get("columns", [])
        for col in cols_list:
            col_name = col["name"]
            if DataClassifier.is_sensitive_column(col_name):
                # Use current table name (mapped or original) to track uniqueness
                mapped_tbl = table_mappings.get(tbl_name, tbl_name)
                alias = f"pii_column_{col_counter}"
                column_mappings[(tbl_name, col_name)] = alias
                col_counter += 1
                logs.append(f"Column '{tbl_name}.{col_name}' was anonymized as '{alias}'.")

    # Step 3: Apply the mappings recursively
    # 3.1: Re-structure tables mapping
    new_tables = {}
    for tbl_name, tbl_info in tables.items():
        mapped_tbl = table_mappings.get(tbl_name, tbl_name)
        
        # Anonymize column definitions inside table
        new_cols = []
        for col in tbl_info.get("columns", []):
            col_name = col["name"]
            mapped_col = column_mappings.get((tbl_name, col_name), col_name)
            new_col = copy.deepcopy(col)
            new_col["name"] = mapped_col
            new_cols.append(new_col)
            
        # Anonymize PK list
        new_pks = [column_mappings.get((tbl_name, pk), pk) for pk in tbl_info.get("primary_key", [])]
        
        # Anonymize FK list
        new_fks = []
        for fk in tbl_info.get("foreign_keys", []):
            col_name = fk["column"]
            ref_tbl = fk["referenced_table"]
            ref_col = fk["referenced_column"]
            
            mapped_col = column_mappings.get((tbl_name, col_name), col_name)
            mapped_ref_tbl = table_mappings.get(ref_tbl, ref_tbl)
            mapped_ref_col = column_mappings.get((ref_tbl, ref_col), ref_col)
            
            new_fks.append({
                "column": mapped_col,
                "referenced_table": mapped_ref_tbl,
                "referenced_column": mapped_ref_col
            })
            
        # Store updated table definition
        new_tables[mapped_tbl] = {
            "name": mapped_tbl,
            "columns": new_cols,
            "primary_key": new_pks,
            "foreign_keys": new_fks,
            "row_count": tbl_info.get("row_count", 0)
        }
        
    redacted["tables"] = new_tables

    # 3.2: Re-structure indexes mapping
    new_indexes = {}
    for tbl_name, idx_list in indexes.items():
        mapped_tbl = table_mappings.get(tbl_name, tbl_name)
        new_idx_list = []
        
        for idx in idx_list:
            idx_name = idx["name"]
            defn = idx["definition"]
            
            # Replace table name in index definition
            defn = defn.replace(tbl_name, mapped_tbl)
            
            # Replace columns in index definition
            for (t_name, c_name), c_alias in column_mappings.items():
                if t_name == tbl_name:
                    defn = defn.replace(c_name, c_alias)
                    
            new_idx_list.append({
                "name": idx_name,
                "definition": defn
            })
            
        new_indexes[mapped_tbl] = new_idx_list
        
    redacted["indexes"] = new_indexes

    return redacted, logs
