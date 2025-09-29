# backend/test_db_connection.py
import asyncio
from urllib.parse import urlparse, urlunparse

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


def _normalize_async_url(url: str) -> str:
    """Ensure the URL uses the asyncpg driver for SQLAlchemy async engines.

    Converts schemes like 'postgresql://...' or 'postgresql+psycopg2://' to
    'postgresql+asyncpg://...'. Leaves other schemes untouched.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme

    # If the URL already uses asyncpg, return unchanged
    if scheme.startswith("postgresql+asyncpg"):
        return url

    # Map common postgres schemes to asyncpg
    if scheme.startswith("postgresql") or scheme.startswith("postgres"):
        new_scheme = "postgresql+asyncpg"
        parsed = parsed._replace(scheme=new_scheme)
        return urlunparse(parsed)

    return url


def _mask_password_in_url(url: str) -> str:
    """Return the URL with the password portion replaced by '***' for safe printing."""
    parsed = urlparse(url)
    if parsed.password:
        # Reconstruct netloc with masked password
        user = parsed.username or ""
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        netloc = f"{user}:***@{host}{port}"
        parsed = parsed._replace(netloc=netloc)
    return urlunparse(parsed)


async def check_connection():
    """Tente de se connecter à la base de données et affiche le résultat."""
    print("Tentative de connexion à la base de données...")

    raw_db_url = getattr(settings, "DATABASE_URL", getattr(settings, "database_url", None))
    if raw_db_url is None:
        print("\n❌ Aucune URL de base de données trouvée dans les settings.")
        return

    safe_printable = _mask_password_in_url(raw_db_url)
    print(f"URL: {safe_printable}")

    try:
        # Normalize to asyncpg driver for SQLAlchemy async engines
        db_url = _normalize_async_url(raw_db_url)
        engine = create_async_engine(db_url)

        # Tente d'établir une connexion
        async with engine.connect() as connection:
            # Si cette ligne est atteinte, la connexion est réussie
            print("\n✅ Connexion à la base de données réussie !")

        # Ferme le moteur
        await engine.dispose()

    except Exception as e:
        print("\n❌ Échec de la connexion à la base de données.")
        print(f"Erreur : {e}")


if __name__ == "__main__":
    asyncio.run(check_connection())