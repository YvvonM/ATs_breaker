import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from models import job, company, application, job_url
from sqlalchemy import text  

load_dotenv()

def get_database_url() -> str:
    DATABASE_URL = os.getenv("DATABASE_URL")
    DATABASE_URL = DATABASE_URL.strip('"').strip("'")
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


    if "sslmode" in DATABASE_URL:
        # Parse the URL
        parsed = urlparse(DATABASE_URL)
        # Parse query parameters
        query_params = parse_qs(parsed.query)
        # Remove sslmode
        query_params.pop('sslmode', None)
        query_params.pop('channel_binding', None)
        # Rebuild query string
        new_query = urlencode(query_params, doseq=True)
        # Rebuild URL without sslmode
        DATABASE_URL = urlunparse((parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
    return DATABASE_URL
        
DATABASE_URL = get_database_url()
print(f"Connecting to database: {DATABASE_URL[:60]}...")

#engine = create_async_engine(DATABASE_URL, echo = False)
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  
    pool_pre_ping=True,  
    pool_size=5,  
    max_overflow=10,
    pool_timeout=30,
    connect_args={"server_settings": {
            "application_name": "ats_breaker_app",
        },
        "ssl": True, 
        "prepared_statement_cache_size": 0,  
    }
)

# async def create_db_and_tables() -> None:
#     async with engine.begin() as conn:
#         await conn.run_sync(SQLModel.metadata.create_all)

async def create_db_and_tables() -> None:
    """Create database tables"""
    try:
        print("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Failed to create tables: {e}")
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSession(engine) as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            print(f"Session error: {e}")
            raise
        finally:
            await session.close()

async def test_connection() -> bool:
    """Test database connection"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"Database connection successful!")
            print(f"PostgreSQL version: {version}")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    
async def drop_all_tables() -> None:
    """Drop all tables (use with caution)"""
    try:
        print("Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        print("All tables dropped successfully!")
    except Exception as e:
        print(f"Failed to drop tables: {e}")
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
