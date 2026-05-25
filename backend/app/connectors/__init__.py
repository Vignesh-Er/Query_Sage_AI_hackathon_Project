from app.connectors.base import DatabaseConnector
from app.connectors.postgresql import PostgresConnector
from app.connectors.mysql import MySQLConnector
from app.connectors.sqlite import SQLiteConnector

def get_connector(connection_id: int, engine: str, config: dict) -> DatabaseConnector:
    engine_lower = engine.lower()
    if engine_lower == "postgresql":
        return PostgresConnector(connection_id, config)
    elif engine_lower == "mysql":
        return MySQLConnector(connection_id, config)
    elif engine_lower == "sqlite":
        return SQLiteConnector(connection_id, config)
    else:
        raise ValueError(f"Unsupported database engine: {engine}")
