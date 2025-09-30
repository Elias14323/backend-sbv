import asyncio
import ssl
from pathlib import Path

async def test_pooler():
    """Test avec le connection pooler port 6543"""
    import asyncpg
    
    backend_root = Path(__file__).resolve().parent
    cert_path = backend_root / "prod-ca-2021.crt"
    
    ssl_context = ssl.create_default_context(cafile=str(cert_path))
    
    try:
        conn = await asyncpg.connect(
            host="yvjubeiwbnuttbuysvto.supabase.co",
            port=6543,  # Connection pooler port
            user="postgres.yvjubeiwbnuttbuysvto",  # Format pour le pooler
            password="RkoWNQbm5Wp6VY",
            database="postgres",
            ssl=ssl_context,
            timeout=30,
        )
        print("✅ Connexion via pooler (port 6543) réussie!")
        await conn.close()
    except Exception as e:
        print(f"❌ Erreur pooler: {e}")

asyncio.run(test_pooler())
