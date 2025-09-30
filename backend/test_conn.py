import asyncio
from app.core.db import async_engine

async def test():
    async with async_engine.connect() as conn:
        print('✅ Connected successfully!')
        
asyncio.run(test())
