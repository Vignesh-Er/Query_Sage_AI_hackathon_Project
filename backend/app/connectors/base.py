from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

class DatabaseConnector(ABC):
    def __init__(self, connection_id: int, config: Dict[str, Any]):
        self.connection_id = connection_id
        self.config = config

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def execute_explain(self, sql: str, use_analyze: bool) -> Any:
        """Run EXPLAIN query wrapped in a BEGIN/ROLLBACK block."""
        pass

    @abstractmethod
    def execute_readonly(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Tuple]:
        """Execute a read-only query and return results."""
        pass

    @abstractmethod
    def fetch_schema(self) -> Dict[str, Any]:
        """Fetch all tables, columns, types, indexes, and primary keys."""
        pass

    @abstractmethod
    def fetch_pg_stats(self, table: str, column: str) -> Optional[Dict[str, Any]]:
        """Fetch pg_stats details for the given table and column."""
        pass

    @abstractmethod
    def fetch_pg_stat_statements(self) -> List[Dict[str, Any]]:
        """Fetch query executions from pg_stat_statements."""
        pass

    @abstractmethod
    def fetch_table_row_counts(self) -> Dict[str, int]:
        """Fetch table row counts."""
        pass
