"""Database engine and session management for the application."""

from __future__ import annotations

import os
import ssl
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _build_connect_args(db_url: str | None = None) -> dict[str, Any]:
    """Build connection arguments with SSL for psycopg driver.
    
    Args:
        db_url: Database connection URL (optional, for compatibility)
        
    Returns:
        Dictionary of connection arguments with SSL configuration
    """
    # Check if we're using a local database (localhost)
    url_to_check = db_url or settings.database_url
    if "localhost" in url_to_check or "127.0.0.1" in url_to_check:
        # Local database - no SSL
        return {}
    
    # Build the path to the certificate (at backend root) for remote DB
    backend_root = Path(__file__).resolve().parents[2]
    cert_path = backend_root / "prod-ca-2021.crt"

    if not cert_path.exists():
        raise FileNotFoundError(
            f"Le certificat SSL de Supabase 'prod-ca-2021.crt' est manquant. "
            f"Attendu à: {cert_path}"
        )

    ssl_context = ssl.create_default_context(cafile=str(cert_path))
    
    # psycopg3 uses conninfo string for SSL parameters
    # Return an empty dict and rely on URL parameters instead
    return {}


async_engine = create_async_engine(
    settings.database_url,
    # Use standard connection pooling (psycopg handles pgbouncer well)
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=5,
    max_overflow=10,
    connect_args=_build_connect_args(),
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""

    async with AsyncSessionLocal() as session:
        yield session


__all__ = ["async_engine", "AsyncSessionLocal", "get_db_session", "_build_connect_args"]
