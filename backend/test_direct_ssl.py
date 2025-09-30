import asyncio
import ssl
from pathlib import Path

async def test_ssl():
    """Test direct de connexion SSL avec asyncpg"""
    import asyncpg
    
    backend_root = Path(__file__).resolve().parent
    cert_path = backend_root / "prod-ca-2021.crt"
    
    ssl_context = ssl.create_default_context(cafile=str(cert_path))
    
    try:
        conn = await asyncpg.connect(
            host="yvjubeiwbnuttbuysvto.supabase.co",
            port=5432,
            user="postgres",
            password="RkoWNQbm5Wp6VY",
            database="postgres",
            ssl=ssl_context,
            timeout=30,
        )
        print("✅ Connexion directe asyncpg réussie!")
        await conn.close()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print(f"Type: {type(e)}")
        import traceback
        traceback.print_exc()

asyncio.run(test_ssl())
