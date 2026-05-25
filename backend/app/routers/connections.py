from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import Connection
from app.schemas import ConnectionCreate, ConnectionResponse, ConnectionTestResponse
from app.keyring_store import save_password, delete_password, get_password
from app.connectors import get_connector

router = APIRouter(prefix="/api/connections", tags=["Connections"])

@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(data: ConnectionCreate, db: AsyncSession = Depends(get_db)):
    # Save connection configuration to SQLite
    conn = Connection(
        name=data.name,
        engine=data.engine.lower(),
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    
    # Save password to Keyring
    if data.password is not None:
        save_password(conn.id, data.password)
        
    return conn

@router.get("", response_model=List[ConnectionResponse])
async def get_connections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Connection))
    return result.scalars().all()

@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Connection).filter(Connection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    # Delete from DB and Keyring
    delete_password(connection_id)
    await db.delete(conn)
    await db.commit()
    return None

@router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
async def test_saved_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
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
        connector.disconnect()
        return ConnectionTestResponse(connected=True)
    except Exception as e:
        return ConnectionTestResponse(connected=False, error=str(e))

@router.post("/test", response_model=ConnectionTestResponse)
def test_transient_connection(data: ConnectionCreate):
    try:
        # We can temporarily mock an ID of 99999 to test
        # We save password briefly or construct transient config
        db_config = {
            "host": data.host,
            "port": data.port,
            "database": data.database,
            "username": data.username
        }
        
        # Temp save password to keyring for transient check, then delete it
        save_password(99999, data.password or "")
        connector = get_connector(99999, data.engine, db_config)
        connector.connect()
        connector.disconnect()
        delete_password(99999)
        return ConnectionTestResponse(connected=True)
    except Exception as e:
        delete_password(99999)
        return ConnectionTestResponse(connected=False, error=str(e))
