#!/usr/bin/env python3
"""Backfill existing articles into Meilisearch."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.core.meili import index_article, setup_articles_index
from app.models.article import Article


async def backfill_articles():
    """Index all existing articles in Meilisearch."""
    
    print("🔧 Setting up Meilisearch index...")
    await setup_articles_index()
    print("✅ Index configured\n")
    
    async with AsyncSessionLocal() as session:
        # Fetch all articles
        result = await session.execute(select(Article))
        articles = result.scalars().all()
        
        print(f"📊 Found {len(articles)} articles to index\n")
        
        indexed = 0
        failed = 0
        
        for article in articles:
            try:
                article_data = {
                    "id": article.id,
                    "title": article.title,
                    "text_content": article.text_content,
                    "lang": article.lang,
                    "source_id": article.source_id,
                    "published_at": article.published_at,
                }
                
                await index_article(article_data)
                indexed += 1
                print(f"✅ Indexed article {article.id}: {article.title[:60]}...")
                
            except Exception as e:
                failed += 1
                print(f"❌ Failed to index article {article.id}: {e}")
        
        print(f"\n📊 Backfill complete:")
        print(f"   ✅ Indexed: {indexed}")
        print(f"   ❌ Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(backfill_articles())
