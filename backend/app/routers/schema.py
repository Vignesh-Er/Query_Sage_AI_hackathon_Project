import os
import sqlglot
import sqlglot.expressions as exp
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from app.database import get_db
from app.models import Connection, Query
from app.connectors import get_connector
from app.schemas import SchemaImpactRequest, SchemaImpactResponse, SchemaImpactRow
from app.migration_parser import parse_any_migrations, parse_alter_statement

router = APIRouter(prefix="/api/schema", tags=["Schema"])

@router.get("/{connection_id}")
async def get_connection_schema(connection_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Connection).filter(Connection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    try:
        db_config = {
            "host": conn.host,
            "port": conn.port,
            "database": conn.database,
            "username": conn.username
        }
        connector = get_connector(conn.id, conn.engine, db_config)
        connector.connect()
        schema = connector.fetch_schema()
        connector.disconnect()
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema: {str(e)}")

def assess_migration_impact(
    queries: List[Query], 
    alter_operations: List[Dict[str, Any]], 
    dialect: str
) -> Dict[str, List[SchemaImpactRow]]:
    """
    Scans query ASTs against DDL alterations and groups queries into:
    broken, potentially affected, or unaffected.
    """
    broken = []
    potentially_affected = []
    unaffected = []
    
    # Track operations per table for quick lookup
    # table -> list of operations: {type: 'DROP'/'RENAME'/'ADD', column: str, new_name: str}
    table_ops = {}
    for op in alter_operations:
        tbl = op["table"].lower()
        if tbl not in table_ops:
            table_ops[tbl] = []
        table_ops[tbl].append(op)

    for q in queries:
        try:
            parsed = sqlglot.parse_one(q.normalized_sql, read=dialect)
        except Exception:
            # Fallback simple string check
            has_impact = False
            for tbl, ops in table_ops.items():
                if tbl in q.raw_sql.lower():
                    has_impact = True
                    break
            if has_impact:
                potentially_affected.append(SchemaImpactRow(
                    query_id=q.id,
                    fingerprint=q.fingerprint,
                    raw_sql=q.raw_sql,
                    impact_reason="Could not parse AST. Table is referenced in raw SQL."
                ))
            else:
                unaffected.append(SchemaImpactRow(
                    query_id=q.id,
                    fingerprint=q.fingerprint,
                    raw_sql=q.raw_sql,
                    impact_reason=""
                ))
            continue

        # Extract tables and columns referenced in query
        query_tables = {t.name.lower() for t in parsed.find_all(exp.Table)}
        query_cols = {} # table_alias or name -> list of cols
        for col in parsed.find_all(exp.Column):
            tbl_alias = col.table.lower() if col.table else "unspecified"
            if tbl_alias not in query_cols:
                query_cols[tbl_alias] = []
            query_cols[tbl_alias].append(col.name.lower())

        is_broken = False
        is_affected = False
        broken_reasons = []
        affected_reasons = []

        # Check operations against query elements
        for tbl_name in query_tables:
            ops = table_ops.get(tbl_name)
            if not ops:
                continue

            for op in ops:
                op_type = op["type"]
                col_name = op.get("column", "").lower()
                new_name = op.get("new_name", "").lower()

                # 1. Check if query references the altered column (explicitly or via unspecified table)
                # If table matches or unspecified, check columns
                referenced_cols = []
                if tbl_name in query_cols:
                    referenced_cols.extend(query_cols[tbl_name])
                if "unspecified" in query_cols:
                    referenced_cols.extend(query_cols["unspecified"])

                col_is_referenced = col_name in referenced_cols if col_name else False

                if op_type == "DROP" and col_is_referenced:
                    is_broken = True
                    broken_reasons.append(f"Dropped column '{col_name}' in table '{tbl_name}' is referenced.")
                elif op_type == "RENAME" and col_is_referenced:
                    is_broken = True
                    broken_reasons.append(f"Column '{col_name}' in table '{tbl_name}' was renamed to '{new_name}'.")
                elif op_type == "RENAME_TABLE":
                    is_broken = True
                    broken_reasons.append(f"Table '{tbl_name}' was renamed to '{new_name}'.")
                elif op_type == "ADD" and tbl_name in query_tables:
                    # Adding a column is generally non-breaking, unless SELECT * is used (causes mismatch)
                    # We classify SELECT * as potentially affected
                    if "*" in referenced_cols or "star" in str(parsed).lower():
                        is_affected = True
                        affected_reasons.append(f"New column '{col_name}' added to table '{tbl_name}' will be fetched by SELECT *.")
                    else:
                        is_affected = True
                        affected_reasons.append(f"Added column '{col_name}' in table '{tbl_name}' is now available.")

        # Group queries
        if is_broken:
            broken.append(SchemaImpactRow(
                query_id=q.id,
                fingerprint=q.fingerprint,
                raw_sql=q.raw_sql,
                impact_reason="; ".join(broken_reasons)
            ))
        elif is_affected:
            potentially_affected.append(SchemaImpactRow(
                query_id=q.id,
                fingerprint=q.fingerprint,
                raw_sql=q.raw_sql,
                impact_reason="; ".join(affected_reasons)
            ))
        else:
            unaffected.append(SchemaImpactRow(
                query_id=q.id,
                fingerprint=q.fingerprint,
                raw_sql=q.raw_sql,
                impact_reason=""
            ))

    return {
        "broken": broken,
        "potentially_affected": potentially_affected,
        "unaffected": unaffected
    }

@router.post("/impact", response_model=SchemaImpactResponse)
async def get_schema_evolution_impact(
    data: SchemaImpactRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Connection).filter(Connection.id == data.connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Step 1: Extract operations from DDL string or directory migrations
    alter_operations = []
    
    if data.alter_statement:
        parsed_op = parse_alter_statement(data.alter_statement)
        if parsed_op:
            alter_operations.append(parsed_op)
        else:
            raise HTTPException(status_code=400, detail="Invalid DDL statement format. Must be an ALTER TABLE statement.")
            
    elif data.migrations_dir:
        try:
            alter_operations = parse_any_migrations(data.migrations_dir)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse migration files: {str(e)}")
            
    else:
        raise HTTPException(status_code=400, detail="Must provide either alter_statement or migrations_dir parameter.")

    if not alter_operations:
        return SchemaImpactResponse(broken=[], potentially_affected=[], unaffected=[])

    # Step 2: Fetch history queries for this connection
    queries_result = await db.execute(select(Query).filter(Query.connection_id == data.connection_id))
    queries = queries_result.scalars().all()
    
    # Step 3: Run impact evaluation
    results = assess_migration_impact(queries, alter_operations, conn.engine)
    
    return SchemaImpactResponse(
        broken=results["broken"],
        potentially_affected=results["potentially_affected"],
        unaffected=results["unaffected"]
    )

@router.post("/impact/directory", response_model=SchemaImpactResponse)
async def get_schema_evolution_impact_directory(
    data: SchemaImpactRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluates schema impact of all migration files in a directory.
    """
    if not data.migrations_dir:
        raise HTTPException(status_code=400, detail="migrations_dir parameter is required.")
    return await get_schema_evolution_impact(data, db)

@router.post("/impact/file", response_model=SchemaImpactResponse)
async def get_schema_evolution_impact_file(
    connection_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluates schema impact of a single uploaded ALTER TABLE statement file.
    """
    result = await db.execute(select(Connection).filter(Connection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        content_bytes = file.file.read()
        content = content_bytes.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload file: {str(e)}")

    # Parse alter statement(s)
    alter_operations = []
    # Support multiple statements split by semicolon
    statements = [stmt.strip() for stmt in content.split(";") if stmt.strip()]
    for stmt in statements:
        if stmt.lower().startswith("alter table"):
            parsed_op = parse_alter_statement(stmt)
            if parsed_op:
                alter_operations.append(parsed_op)

    if not alter_operations:
        raise HTTPException(status_code=400, detail="No valid ALTER TABLE statement found in the uploaded file.")

    queries_result = await db.execute(select(Query).filter(Query.connection_id == connection_id))
    queries = queries_result.scalars().all()
    results = assess_migration_impact(queries, alter_operations, conn.engine)
    
    return SchemaImpactResponse(
        broken=results["broken"],
        potentially_affected=results["potentially_affected"],
        unaffected=results["unaffected"]
    )
