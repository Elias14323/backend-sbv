import asyncio

async def test_no_ssl():
    """Test connexion sans SSL"""
    import asyncpg
    
    try:
        conn = await asyncpg.connect(
            host="yvjubeiwbnuttbuysvto.supabase.co",
            port=5432,
            user="postgres",
            password="RkoWNQbm5Wp6VY",
            database="postgres",
            ssl=False,  # Désactiver SSL
            timeout=30,
        )
        print("✅ Connexion sans SSL réussie!")
        await conn.close()
    except Exception as e:
        print(f"❌ Erreur sans SSL: {e}")
        print(f"Type: {type(e)}")

asyncio.run(test_no_ssl())
