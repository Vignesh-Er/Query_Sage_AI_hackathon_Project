import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from app.connectors.base import DatabaseConnector

class SQLiteConnector(DatabaseConnector):
    def __init__(self, connection_id: int, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.conn = None

    def connect(self) -> None:
        # SQLite db path is host or database config
        db_path = self.config.get("database") or self.config.get("host") or ":memory:"
        self.conn = sqlite3.connect(db_path, timeout=5)

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_explain(self, sql: str, use_analyze: bool) -> Any:
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        try:
            # SQLite transaction rollback
            cursor.execute("BEGIN TRANSACTION;")
            explain_query = f"EXPLAIN QUERY PLAN {sql}"
            cursor.execute(explain_query)
            res = cursor.fetchall()
            cursor.execute("ROLLBACK;")
            
            # Convert SQLite plan rows to a list of dicts
            # SQLite columns: selectid, order, from, detail OR id, parent, notused, detail
            plan_rows = []
            for row in res:
                if len(row) == 4:
                    plan_rows.append({
                        "id": row[0],
                        "parent": row[1],
                        "notused": row[2],
                        "detail": row[3]
                    })
                elif len(row) == 3:
                    plan_rows.append({
                        "selectid": row[0],
                        "order": row[1],
                        "from": row[2],
                        "detail": row[3] if len(row) > 3 else ""
                    })
                else:
                    plan_rows.append({"detail": str(row)})
            return plan_rows
        except Exception as e:
            try:
                cursor.execute("ROLLBACK;")
            except Exception:
                pass
            raise e
        finally:
            cursor.close()

    def execute_readonly(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Tuple]:
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        try:
            cursor.execute("BEGIN TRANSACTION;")
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            results = cursor.fetchall()
            cursor.execute("ROLLBACK;")
            return results
        except Exception as e:
            try:
                cursor.execute("ROLLBACK;")
            except Exception:
                pass
            raise e
        finally:
            cursor.close()

    def fetch_schema(self) -> Dict[str, Any]:
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        schema = {"tables": {}, "indexes": {}}
        try:
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for (tbl_name,) in tables:
                if tbl_name.startswith("sqlite_"):
                    continue
                    
                schema["tables"][tbl_name] = {
                    "name": tbl_name,
                    "columns": [],
                    "primary_key": [],
                    "foreign_keys": [],
                    "row_count": 0
                }
                
                # Fetch row counts
                cursor.execute(f"SELECT COUNT(*) FROM `{tbl_name}`")
                schema["tables"][tbl_name]["row_count"] = cursor.fetchone()[0]

                # Fetch column info
                cursor.execute(f"PRAGMA table_info(`{tbl_name}`);")
                # cid, name, type, notnull, dflt_value, pk
                for col in cursor.fetchall():
                    schema["tables"][tbl_name]["columns"].append({
                        "name": col[1],
                        "type": col[2],
                        "nullable": col[3] == 0
                    })
                    if col[5] > 0:
                        schema["tables"][tbl_name]["primary_key"].append(col[1])

                # Fetch foreign keys
                cursor.execute(f"PRAGMA foreign_key_list(`{tbl_name}`);")
                # id, seq, table, from, to, on_update, on_delete, match
                for fk in cursor.fetchall():
                    schema["tables"][tbl_name]["foreign_keys"].append({
                        "column": fk[3],
                        "referenced_table": fk[2],
                        "referenced_column": fk[4]
                    })

                # Fetch indexes
                cursor.execute(f"PRAGMA index_list(`{tbl_name}`);")
                # seq, name, unique, origin, partial
                for idx in cursor.fetchall():
                    idx_name = idx[1]
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='index' AND name='{idx_name}';")
                    idx_sql = cursor.fetchone()
                    idx_definition = idx_sql[0] if idx_sql and idx_sql[0] else f"INDEX {idx_name} ON {tbl_name}"
                    
                    if tbl_name not in schema["indexes"]:
                        schema["indexes"][tbl_name] = []
                    schema["indexes"][tbl_name].append({
                        "name": idx_name,
                        "definition": idx_definition
                    })

            return schema
        finally:
            cursor.close()

    def fetch_pg_stats(self, table: str, column: str) -> Optional[Dict[str, Any]]:
        # SQLite basic statistics emulation
        try:
            res = self.execute_readonly(
                f"SELECT `{column}`, COUNT(*) as cnt FROM `{table}` GROUP BY 1 ORDER BY cnt DESC LIMIT 1;"
            )
            if res:
                val, count = res[0]
                total = self.execute_readonly(f"SELECT COUNT(*) FROM `{table}`;")[0][0]
                freq = count / total if total > 0 else 0
                return {
                    "most_common_vals": [str(val)],
                    "most_common_freqs": [freq],
                    "histogram_bounds": []
                }
        except Exception:
            pass
        return None

    def fetch_pg_stat_statements(self) -> List[Dict[str, Any]]:
        # SQLite doesn't track runtime stats
        return []

    def fetch_table_row_counts(self) -> Dict[str, int]:
        counts = {}
        try:
            if not self.conn:
                self.connect()
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for (tbl,) in tables:
                if tbl.startswith("sqlite_"):
                    continue
                cursor.execute(f"SELECT COUNT(*) FROM `{tbl}`;")
                counts[tbl] = cursor.fetchone()[0]
        except Exception:
            pass
        return counts
