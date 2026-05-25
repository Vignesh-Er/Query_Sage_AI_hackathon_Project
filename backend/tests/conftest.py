import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.config import settings

# Test SQLite in-memory database
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

@pytest.fixture(name="db_session")
async def fixture_db_session():
    engine = create_async_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Enable SQLite foreign keys and create schema
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
        
    TestingSessionLocal = async_sessionmaker(
        autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(name="client")
def fixture_client(db_session):
    async def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(name="sample_bad_queries")
def fixture_sample_bad_queries():
    return {
        "P01": "SELECT * FROM rental;",
        "P02": "SELECT rental_id FROM rental WHERE YEAR(rental_date) = 2005;",
        "P03": "SELECT customer_id FROM customer WHERE email LIKE '%@gmail.com';",
        "P17": "DELETE FROM rental;",
        "P18": "SELECT * FROM rental, customer;",
        "C01": "SELECT * FROM customer WHERE email = NULL;",
        "C06": "SELECT rental_id / staff_id FROM rental;",
        "S01": "INSERT INTO rental VALUES (1, '2005-05-24', 1, 1);",
        "S02": "SELECT * FROM customer WHERE email = 'johndoe@gmail.com';"
    }
