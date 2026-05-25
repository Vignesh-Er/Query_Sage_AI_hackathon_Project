import json
import mysql.connector
from typing import Any, Dict, List, Optional, Tuple
from app.connectors.base import DatabaseConnector
from app.keyring_store import get_password

class MySQLConnector(DatabaseConnector):
    def __init__(self, connection_id: int, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.conn = None

    def connect(self) -> None:
        password = get_password(self.connection_id) or ""
        self.conn = mysql.connector.connect(
            host=self.config.get("host", "localhost"),
            port=self.config.get("port", 3306),
            database=self.config.get("database"),
            user=self.config.get("username"),
            password=password,
            connection_timeout=5
        )

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_explain(self, sql: str, use_analyze: bool) -> Any:
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        try:
            self.conn.start_transaction(readonly=True)
            # MySQL supports EXPLAIN FORMAT=JSON
            explain_query = f"EXPLAIN FORMAT=JSON {sql}"
            cursor.execute(explain_query)
            res = cursor.fetchone()
            
            self.conn.rollback()
            
            if res and len(res) > 0:
                # In MySQL, the result is returned as a JSON string in the first column
                try:
                    return json.loads(res[0])
                except Exception:
                    return res[0]
            return None
        except Exception as e:
            try:
                self.conn.rollback()
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
            self.conn.start_transaction(readonly=True)
            # MySQL doesn't use placeholders like postgres %s by default unless using prepared statements.
            # mysql-connector accepts %s or %(key)s or ?
            cursor.execute(sql, params)
            results = cursor.fetchall()
            self.conn.rollback()
            return results
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise e
        finally:
            cursor.close()

    def fetch_schema(self) -> Dict[str, Any]:
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor(dictionary=True)
        schema = {"tables": {}, "indexes": {}}
        db_name = self.config.get("database")
        try:
            # Query tables and columns
            cursor.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s
                ORDER BY table_name, ordinal_position;
                """,
                (db_name,)
            )
            columns = cursor.fetchall()
            for col in columns:
                tbl = col["table_name"]
                if tbl not in schema["tables"]:
                    schema["tables"][tbl] = {
                        "name": tbl,
                        "columns": [],
                        "primary_key": [],
                        "foreign_keys": [],
                        "row_count": 0
                    }
                schema["tables"][tbl]["columns"].append({
                    "name": col["column_name"],
                    "type": col["data_type"],
                    "nullable": col["is_nullable"] == "YES"
                })

            # Fetch row count estimations
            cursor.execute(
                """
                SELECT table_name, table_rows
                FROM information_schema.tables
                WHERE table_schema = %s;
                """,
                (db_name,)
            )
            for row in cursor.fetchall():
                tbl = row["table_name"]
                if tbl in schema["tables"]:
                    schema["tables"][tbl]["row_count"] = row["table_rows"] or 0

            # Query primary keys
            cursor.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.key_column_usage
                WHERE constraint_name = 'PRIMARY' AND table_schema = %s;
                """,
                (db_name,)
            )
            for pk in cursor.fetchall():
                tbl = pk["table_name"]
                if tbl in schema["tables"]:
                    schema["tables"][tbl]["primary_key"].append(pk["column_name"])

            # Query foreign keys
            cursor.execute(
                """
                SELECT 
                    table_name,
                    column_name,
                    referenced_table_name as foreign_table_name,
                    referenced_column_name as foreign_column_name
                FROM information_schema.key_column_usage
                WHERE referenced_table_name IS NOT NULL AND table_schema = %s;
                """,
                (db_name,)
            )
            for fk in cursor.fetchall():
                tbl = fk["table_name"]
                if tbl in schema["tables"]:
                    schema["tables"][tbl]["foreign_keys"].append({
                        "column": fk["column_name"],
                        "referenced_table": fk["foreign_table_name"],
                        "referenced_column": fk["foreign_column_name"]
                    })

            # Query indexes
            cursor.execute(
                """
                SELECT DISTINCT table_name, index_name
                FROM information_schema.statistics
                WHERE table_schema = %s;
                """,
                (db_name,)
            )
            for idx in cursor.fetchall():
                tbl = idx["table_name"]
                if tbl not in schema["indexes"]:
                    schema["indexes"][tbl] = []
                schema["indexes"][tbl].append({
                    "name": idx["index_name"],
                    "definition": f"INDEX {idx['index_name']} ON {tbl}"
                })

            return schema
        finally:
            cursor.close()

    def fetch_pg_stats(self, table: str, column: str) -> Optional[Dict[str, Any]]:
        # MySQL statistics are not exposed via pg_stats (only in information_schema or HISTOGRAMS in 8.0+)
        # We can implement a basic card/frequency estimator using query if necessary
        try:
            # Basic frequency check of top value
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
        # MySQL uses performance_schema.events_statements_summary_by_digest
        try:
            res = self.execute_readonly(
                """
                SELECT digest_text as query, count_star as calls, sum_timer_wait/1000000000 as total_exec_time,
                       avg_timer_wait/1000000000 as mean_exec_time, sum_rows_sent as rows
                FROM performance_schema.events_statements_summary_by_digest
                ORDER BY sum_timer_wait DESC
                LIMIT 500;
                """
            )
            return [
                {
                    "query": r[0],
                    "calls": r[1],
                    "total_exec_time": r[2],
                    "mean_exec_time": r[3],
                    "rows": r[4]
                }
                for r in res
            ]
        except Exception:
            return []

    def fetch_table_row_counts(self) -> Dict[str, int]:
        counts = {}
        try:
            db_name = self.config.get("database")
            res = self.execute_readonly(
                "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema = %s;",
                (db_name,)
            )
            for name, count in res:
                counts[name] = int(count or 0)
        except Exception:
            pass
        return counts
