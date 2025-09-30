"""Database engine and session management for the application."""

from __future__ import annotations

import os
import ssl
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _build_connect_args(db_url: str | None = None) -> dict[str, Any]:
    """Build connection arguments with a custom SSL context that trusts
    the Supabase CA certificate.
    
    Args:
        db_url: Database connection URL (optional, for compatibility)
        
    Returns:
        Dictionary of connection arguments with SSL configuration
    """
    # Check if we're using a local database (localhost)
    url_to_check = db_url or settings.database_url
    if "localhost" in url_to_check or "127.0.0.1" in url_to_check:
        # Local database - no SSL
        return {
            "ssl": False,
            "statement_cache_size": 0,
            "timeout": 10,
            "command_timeout": 30,
        }
    
    # Build the path to the certificate (at backend root) for remote DB
    backend_root = Path(__file__).resolve().parents[2]
    cert_path = backend_root / "prod-ca-2021.crt"

    if not cert_path.exists():
        raise FileNotFoundError(
            f"Le certificat SSL de Supabase 'prod-ca-2021.crt' est manquant. "
            f"Attendu à: {cert_path}"
        )

    ssl_context = ssl.create_default_context(cafile=str(cert_path))
    
    # Disable prepared statement cache for Supabase Transaction Pooler compatibility
    # (pgbouncer in transaction mode doesn't support prepared statements)
    return {
        "ssl": ssl_context,
        "statement_cache_size": 0,
        "timeout": 10,  # Connection timeout in seconds
        "command_timeout": 30,  # Query timeout in seconds
    }


async_engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=5,  # Limit concurrent connections
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
