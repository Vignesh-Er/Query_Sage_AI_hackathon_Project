import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Dict, List, Optional, Tuple
from app.connectors.base import DatabaseConnector
from app.keyring_store import get_password

class PostgresConnector(DatabaseConnector):
    def __init__(self, connection_id: int, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.conn = None

    def connect(self) -> None:
        password = get_password(self.connection_id) or ""
        self.conn = psycopg2.connect(
            host=self.config.get("host", "localhost"),
            port=self.config.get("port", 5432),
            database=self.config.get("database"),
            user=self.config.get("username"),
            password=password,
            connect_timeout=5
        )
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT current_setting('server_version_num')::int;")
                self.server_version = cur.fetchone()[0]
        except Exception:
            self.server_version = 150000

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_explain(self, sql: str, use_analyze: bool) -> Any:
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        try:
            # Wrap execution inside transaction block that is rolled back
            self.conn.autocommit = False
            cursor.execute("BEGIN ISOLATION LEVEL SERIALIZABLE READ ONLY;")
            
            # Format explain command
            if use_analyze:
                version = getattr(self, "server_version", 150000)
                if version >= 160000:
                    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, MEMORY, SERIALIZE, FORMAT JSON) {sql}"
                else:
                    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
            else:
                explain_query = f"EXPLAIN (FORMAT JSON) {sql}"
                
            cursor.execute(explain_query)
            plan = cursor.fetchone()
            
            # Rollback transaction immediately
            cursor.execute("ROLLBACK;")
            self.conn.commit()
            
            if plan and len(plan) > 0:
                return plan[0]
            return None
        except Exception as e:
            try:
                cursor.execute("ROLLBACK;")
                self.conn.commit()
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
            self.conn.autocommit = False
            cursor.execute("BEGIN ISOLATION LEVEL SERIALIZABLE READ ONLY;")
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            cursor.execute("ROLLBACK;")
            self.conn.commit()
            return results
        except Exception as e:
            try:
                cursor.execute("ROLLBACK;")
                self.conn.commit()
            except Exception:
                pass
            raise e
        finally:
            cursor.close()

    def fetch_schema(self) -> Dict[str, Any]:
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        schema = {"tables": {}, "indexes": {}}
        try:
            # Query tables and columns
            cursor.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
                """
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

            # Fetch Row Counts from pg_stat_user_tables
            cursor.execute(
                """
                SELECT relname as table_name, n_live_tup as row_count
                FROM pg_stat_user_tables;
                """
            )
            for row in cursor.fetchall():
                tbl = row["table_name"]
                if tbl in schema["tables"]:
                    schema["tables"][tbl]["row_count"] = row["row_count"]

            # Query primary keys
            cursor.execute(
                """
                SELECT kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public';
                """
            )
            for pk in cursor.fetchall():
                tbl = pk["table_name"]
                if tbl in schema["tables"]:
                    schema["tables"][tbl]["primary_key"].append(pk["column_name"])

            # Query foreign keys
            cursor.execute(
                """
                SELECT
                    tc.table_name as table_name,
                    kcu.column_name as column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public';
                """
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
                SELECT
                    tablename as table_name,
                    indexname as index_name,
                    indexdef as definition
                FROM pg_indexes
                WHERE schemaname = 'public';
                """
            )
            for idx in cursor.fetchall():
                tbl = idx["table_name"]
                if tbl not in schema["indexes"]:
                    schema["indexes"][tbl] = []
                schema["indexes"][tbl].append({
                    "name": idx["index_name"],
                    "definition": idx["definition"]
                })

            return schema
        finally:
            cursor.close()

    def fetch_pg_stats(self, table: str, column: str) -> Optional[Dict[str, Any]]:
        try:
            results = self.execute_readonly(
                """
                SELECT most_common_vals, most_common_freqs, histogram_bounds
                FROM pg_stats
                WHERE schemaname = 'public' AND tablename = %s AND attname = %s;
                """,
                (table, column)
            )
            if results:
                row = results[0]
                return {
                    "most_common_vals": row[0],
                    "most_common_freqs": row[1],
                    "histogram_bounds": row[2]
                }
        except Exception:
            pass
        return None

    def fetch_pg_stat_statements(self) -> List[Dict[str, Any]]:
        try:
            # We fetch statements using execute_readonly to avoid manual cursor creation
            if not self.conn:
                self.connect()
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            try:
                cursor.execute(
                    """
                    SELECT query, calls, total_exec_time, mean_exec_time, rows
                    FROM pg_stat_statements
                    ORDER BY total_exec_time DESC
                    LIMIT 500;
                    """
                )
                return list(cursor.fetchall())
            finally:
                cursor.close()
        except Exception:
            return []

    def fetch_table_row_counts(self) -> Dict[str, int]:
        counts = {}
        try:
            res = self.execute_readonly(
                "SELECT relname, n_live_tup FROM pg_stat_user_tables;"
            )
            for name, count in res:
                counts[name] = int(count)
        except Exception:
            pass
        return counts
