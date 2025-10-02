#!/usr/bin/env python3
"""Test direct de connexion à Supabase"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    db_url = os.getenv("DATABASE_URL")
    print(f"🔍 Testing connection to Supabase...")
    print(f"   URL pattern: {db_url.split('@')[1] if '@' in db_url else 'hidden'}")
    
    # Extraire les paramètres de connexion
    # Format: postgresql+asyncpg://user:pass@host:port/db
    url_parts = db_url.replace("postgresql+asyncpg://", "").split("@")
    user_pass = url_parts[0].split(":")
    host_port_db = url_parts[1].split("/")
    host_port = host_port_db[0].split(":")
    
    user = user_pass[0]
    password = user_pass[1]
    host = host_port[0]
    port = int(host_port[1])
    database = host_port_db[1]
    
    print(f"\n📋 Connection details:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Database: {database}")
    print(f"   User: {user}")
    print(f"   Password: {'*' * len(password)}")
    
    try:
        print(f"\n⏳ Attempting connection...")
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            timeout=10.0,
            ssl='require',
            statement_cache_size=0
        )
        
        print(f"✅ Connection successful!")
        
        # Test simple query
        version = await conn.fetchval('SELECT version()')
        print(f"\n🗄️  PostgreSQL version:")
        print(f"   {version}")
        
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        
        print(f"\n📊 Existing tables: {len(tables)}")
        for table in tables:
            print(f"   - {table['tablename']}")
        
        await conn.close()
        print(f"\n✅ Test completed successfully!")
        
    except asyncio.TimeoutError:
        print(f"❌ Connection timeout - peut-être un problème de firewall ou de réseau")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
