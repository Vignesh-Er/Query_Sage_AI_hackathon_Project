import os
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

def parse_alter_statement(sql_line: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single ALTER TABLE SQL statement.
    Returns details on table, type of change (add/drop/rename), and column name.
    """
    cleaned = " ".join(sql_line.split())
    # Match ALTER TABLE table_name ...
    match_table = re.search(r"alter\s+table\s+([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE)
    if not match_table:
        return None
        
    table_name = match_table.group(1).replace("`", "").replace("\"", "")
    
    # 1. ADD COLUMN
    if re.search(r"add\s+(?:column\s+)?([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE):
        match_col = re.search(r"add\s+(?:column\s+)?([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE)
        col = match_col.group(1).replace("`", "").replace("\"", "")
        return {"table": table_name, "type": "ADD", "column": col}
        
    # 2. DROP COLUMN
    elif re.search(r"drop\s+(?:column\s+)?([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE):
        match_col = re.search(r"drop\s+(?:column\s+)?([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE)
        col = match_col.group(1).replace("`", "").replace("\"", "")
        return {"table": table_name, "type": "DROP", "column": col}
        
    # 3. RENAME COLUMN
    elif re.search(r"rename\s+column\s+([a-zA-Z0-9_`\"-]+)\s+to\s+([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE):
        match_cols = re.search(r"rename\s+column\s+([a-zA-Z0-9_`\"-]+)\s+to\s+([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE)
        col = match_cols.group(1).replace("`", "").replace("\"", "")
        new_col = match_cols.group(2).replace("`", "").replace("\"", "")
        return {"table": table_name, "type": "RENAME", "column": col, "new_name": new_col}
        
    # 4. RENAME TABLE
    elif re.search(r"rename\s+to\s+([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE):
        match_tbl = re.search(r"rename\s+to\s+([a-zA-Z0-9_`\"-]+)", cleaned, re.IGNORECASE)
        new_tbl = match_tbl.group(1).replace("`", "").replace("\"", "")
        return {"table": table_name, "type": "RENAME_TABLE", "new_name": new_tbl}

    return None

def parse_flyway_migrations(directory: str) -> List[Dict[str, Any]]:
    """Reads Flyway SQL files from a folder sorted by version."""
    changes = []
    if not os.path.exists(directory):
        return []
        
    # Sort files matching V<version>__<name>.sql
    files = [f for f in os.listdir(directory) if f.upper().startswith("V") and f.endswith(".sql")]
    
    def extract_version(filename: str) -> float:
        # Extract leading numeric version
        match = re.match(r"^V([0-9.]+)", filename, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(".", ""))
            except ValueError:
                pass
        return 0.0

    files.sort(key=extract_version)

    for filename in files:
        path = os.path.join(directory, filename)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "alter table" in line.lower():
                    parsed = parse_alter_statement(line)
                    if parsed:
                        changes.append(parsed)
    return changes

def parse_liquibase_changelogs(filepath: str) -> List[Dict[str, Any]]:
    """Parses Liquibase XML changelogs looking for column alterations."""
    changes = []
    if not os.path.exists(filepath):
        return []

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # NS mappings (Liquibase XML namespaces)
        ns = {"lb": "http://www.liquibase.org/xml/ns/dbchangelog"}
        
        # Support both namespaced and non-namespaced queries
        for changeSet in root.findall(".//changeSet") + root.findall(".//lb:changeSet", ns):
            # 1. addColumn
            for add_col in changeSet.findall(".//addColumn") + changeSet.findall(".//lb:addColumn", ns):
                tbl = add_col.attrib.get("tableName")
                for col in add_col.findall(".//column") + add_col.findall(".//lb:column", ns):
                    col_name = col.attrib.get("name")
                    if tbl and col_name:
                        changes.append({"table": tbl, "type": "ADD", "column": col_name})
                        
            # 2. dropColumn
            for drop_col in changeSet.findall(".//dropColumn") + changeSet.findall(".//lb:dropColumn", ns):
                tbl = drop_col.attrib.get("tableName")
                col_name = drop_col.attrib.get("columnName")
                if tbl and col_name:
                    changes.append({"table": tbl, "type": "DROP", "column": col_name})
                    
            # 3. renameColumn
            for rename_col in changeSet.findall(".//renameColumn") + changeSet.findall(".//lb:renameColumn", ns):
                tbl = rename_col.attrib.get("tableName")
                old_name = rename_col.attrib.get("oldColumnName")
                new_name = rename_col.attrib.get("newColumnName")
                if tbl and old_name and new_name:
                    changes.append({"table": tbl, "type": "RENAME", "column": old_name, "new_name": new_name})
    except Exception:
        pass
        
    return changes

def parse_prisma_migrations(directory: str) -> List[Dict[str, Any]]:
    """Parses Prisma migrate SQL files inside individual folder versions."""
    changes = []
    if not os.path.exists(directory):
        return []

    # Sort directories by creation time / name
    subdirs = []
    for d in os.listdir(directory):
        d_path = os.path.join(directory, d)
        if os.path.isdir(d_path) and os.path.exists(os.path.join(d_path, "migration.sql")):
            subdirs.append(d)
            
    subdirs.sort()  # typical naming includes timestamp prefix

    for subdir in subdirs:
        path = os.path.join(directory, subdir, "migration.sql")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "alter table" in line.lower():
                    parsed = parse_alter_statement(line)
                    if parsed:
                        changes.append(parsed)
    return changes

def parse_any_migrations(path: str) -> List[Dict[str, Any]]:
    """Autodetects migration type based on path structure and parses it."""
    if os.path.isdir(path):
        # Check if contains Prisma style migration.sql inside folders
        # or Flyway style SQLs
        is_prisma = any(os.path.isdir(os.path.join(path, d)) for d in os.listdir(path))
        if is_prisma:
            return parse_prisma_migrations(path)
        else:
            return parse_flyway_migrations(path)
    elif os.path.isfile(path) and path.endswith(".xml"):
        return parse_liquibase_changelogs(path)
    return []
