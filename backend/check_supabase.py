#!/usr/bin/env python3
"""Vérifie le contenu de la base Supabase"""
import asyncio
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import AsyncSessionLocal
from app.models import Article, Cluster

async def check_database():
    print("📊 Vérification de la base de données Supabase\n")
    
    async with AsyncSessionLocal() as session:
        # Compter les articles
        result = await session.execute(select(func.count(Article.id)))
        article_count = result.scalar()
        print(f"✅ Articles : {article_count}")
        
        # Compter les clusters
        result = await session.execute(select(func.count(Cluster.id)))
        cluster_count = result.scalar()
        print(f"✅ Clusters : {cluster_count}")
        
        # Montrer les derniers articles triés par date d'agrégation (created_at)
        result = await session.execute(
            select(Article.id, Article.title, Article.url, Article.published_at, Article.created_at)
            .order_by(Article.created_at.desc())
            .limit(10)
        )
        articles = result.all()

        print(f"\n📰 Derniers articles agrégés (par created_at, 10) :")
        for a in articles:
            aid, title, url, published_at, created_at = a
            t = (title[:80] if title else "Sans titre")
            u = (url[:60] if url else "")
            print(f"   - id={aid} | {t} | published_at={published_at} | aggregated_at={created_at} | {u}")

if __name__ == "__main__":
    asyncio.run(check_database())
