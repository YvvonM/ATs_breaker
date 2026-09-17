import os 
from contextlib import contextmanager
from typing import Iterator
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

def _build_sync_url()-> str:
    url = os.getenv('DATABASE_URL').strip("'").strip('"')
    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)

    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values= True)
    for bad in(
        "channel_binding",
        "prepared_statement_cache_size",
        "sslmode",
    ):
        query.pop(bad, None)

    query['sslmode'] = ['require']
    new_query = urlencode(query, doseq=True)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )

SYNC_DATABASE_URL = _build_sync_url()

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=3600,
    pool_recycle=500,   
    connect_args={
        "application_name": "ats_breaker_pipeline",
        
    },
)

_SyncSessionLocal = sessionmaker(
    bind= sync_engine,
    class_=Session,
    expire_on_commit=False,   
    autoflush=False,
)

@contextmanager
def sync_session() -> Iterator[Session]:
    session = _SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
