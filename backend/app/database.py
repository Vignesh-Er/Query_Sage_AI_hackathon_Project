import os
from contextlib import asynccontextmanager
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.config import settings
from app.models import Base

# Construct database URI
db_path = os.path.abspath(os.path.expanduser(settings.QUERYSAGE_DB_PATH))
DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

# Enable foreign keys in SQLite
engine = create_async_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=NullPool
)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            pass

@asynccontextmanager
async def get_db_context():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS audit_log_prevent_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(FAIL, 'Updates are not allowed on audit_log');
            END;
            """)
        )
        await conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS audit_log_prevent_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(FAIL, 'Deletions are not allowed on audit_log');
            END;
            """)
        )
    
    # Load settings from SQLite settings table and override Pydantic settings instance
    from app.models import Settings
    from sqlalchemy import select
    async with SessionLocal() as db:
        try:
            result = await db.execute(select(Settings))
            db_settings = result.scalars().all()
            for s in db_settings:
                key_upper = s.key.upper()
                if hasattr(settings, key_upper):
                    orig_val = getattr(settings, key_upper)
                    try:
                        if isinstance(orig_val, bool):
                            casted = s.value.lower() in ("true", "1", "yes")
                        elif isinstance(orig_val, int):
                            casted = int(s.value)
                        elif isinstance(orig_val, float):
                            casted = float(s.value)
                        else:
                            casted = s.value
                        setattr(settings, key_upper, casted)
                    except Exception:
                        setattr(settings, key_upper, s.value)
        except Exception:
            pass
