#!/usr/bin/env python3
"""Add a batch of sources into the database safely.

This script embeds the provided sources list and upserts them into the
`sources` table using the app's Source model and AsyncSessionLocal.

It checks for existing sources by URL, inserts missing ones, and can
optionally trigger the ingestion task for newly added sources (disabled
by default).
"""
import asyncio
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.db import AsyncSessionLocal
from app.models import Source, SourceKind, TrustTier

# Embedded sources payload (trimmed for readability in code; use the full list)
SOURCES = [
  {
    "id": 38,
    "url": "https://www.euronews.com/rss?level=theme&name=news",
    "title": "Euronews – All News",
    "language": "en",
    "bias_side": "c",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=euronews.com&sz=32"
  },
  {
    "id": 42,
    "url": "https://www.theguardian.com/world/rss",
    "title": "The Guardian – World",
    "language": "en",
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=theguardian.com&sz=32"
  },
  {
    "id": 7,
    "url": "https://feeds.theguardian.com/theguardian/world/rss",
    "title": "The Guardian",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 15:33:16.447873+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=theguardian.com&sz=32"
  },
  {
    "id": 33,
    "url": "https://services.lesechos.fr/rss/les-echos-start-up.xml",
    "title": "Les Échos – Start-up",
    "language": None,
    "bias_side": "na",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lesechos.fr&sz=32"
  },
  {
    "id": 29,
    "url": "https://www.rfi.fr/fr/rss",
    "title": "RFI – Monde",
    "language": None,
    "bias_side": "c",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=rfi.fr&sz=32"
  },
  {
    "id": 28,
    "url": "https://www.lemonde.fr/sport/rss_full.xml",
    "title": "Le Monde – Sport",
    "language": None,
    "bias_side": "na",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=32"
  },
  {
    "id": 25,
    "url": "https://www.lemonde.fr/pixels/rss_full.xml",
    "title": "Le Monde – Pixels (Tech)",
    "language": None,
    "bias_side": "na",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=32"
  },
  {
    "id": 24,
    "url": "https://www.lemonde.fr/international/rss_full.xml",
    "title": "Le Monde – International",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=32"
  },
  {
    "id": 21,
    "url": "http://www.lemonde.fr/rss/une.xml",
    "title": "Le Monde – A la Une",
    "language": "fr",
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=32"
  },
  {
    "id": 27,
    "url": "https://www.lemonde.fr/politique/rss_full.xml",
    "title": "Le Monde – Politique",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=32"
  },
  {
    "id": 23,
    "url": "https://www.lemonde.fr/economie/rss_full.xml",
    "title": "Le Monde – Économie",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=32"
  },
  {
    "id": 26,
    "url": "https://www.lemonde.fr/planete/rss_full.xml",
    "title": "Le Monde – Planète",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=32"
  },
  {
    "id": 20,
    "url": "http://www.lefigaro.fr/rss/figaro_actualites.xml",
    "title": "Le Figaro – Actualités",
    "language": None,
    "bias_side": "rc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lefigaro.fr&sz=32"
  },
  {
    "id": 19,
    "url": "https://www.france24.com/fr/rss",
    "title": "France 24 (FR)",
    "language": "fr",
    "bias_side": "c",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=france24.com&sz=32"
  },
  {
    "id": 34,
    "url": "https://services.lesechos.fr/rss/les-echos-tech-medias.xml",
    "title": "Les Échos – Tech et Médias",
    "language": None,
    "bias_side": "na",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lesechos.fr&sz=32"
  },
  {
    "id": 8,
    "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "title": "NY Times – World",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 15:33:18.667716+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=rss.nytimes.com&sz=32"
  },
  {
    "id": 22,
    "url": "https://www.lemonde.fr/culture/rss_full.xml",
    "title": "Le Monde – Culture",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lemonde.fr&sz=32"
  },
  {
    "id": 5,
    "url": "https://feeds.washingtonpost.com/rss/world",
    "title": "Washington Post - World",
    "language": None,
    "bias_side": "l",
    "status": "active",
    "created_at": "2025-07-07 15:33:05.798308+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=washingtonpost.com&sz=32"
  },
  {
    "id": 2,
    "url": "https://feeds.skynews.com/feeds/rss/world.xml",
    "title": "Sky News",
    "language": None,
    "bias_side": "c",
    "status": "active",
    "created_at": "2025-07-07 15:33:00.726256+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=skynews.com&sz=32"
  },
  {
    "id": 4,
    "url": "https://feeds.npr.org/1001/rss.xml",
    "title": "NPR News",
    "language": None,
    "bias_side": "l",
    "status": "active",
    "created_at": "2025-07-07 15:33:04.571492+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=npr.org&sz=32"
  },
  {
    "id": 6,
    "url": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
    "title": "Wall Street Journal",
    "language": None,
    "bias_side": "r",
    "status": "active",
    "created_at": "2025-07-07 15:33:14.286993+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=wsj.com&sz=32"
  },
  {
    "id": 9,
    "url": "https://rss.politico.com/politics-news.xml",
    "title": "Politico",
    "language": None,
    "bias_side": "c",
    "status": "active",
    "created_at": "2025-07-07 15:33:20.818749+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=politico.com&sz=32"
  },
  {
    "id": 39,
    "url": "https://feeds.npr.org/1004/rss.xml",
    "title": "NPR – World",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=npr.org&sz=32"
  },
  {
    "id": 37,
    "url": "https://rss.dw.com/rdf/rss-en-top",
    "title": "DW – Top Stories",
    "language": None,
    "bias_side": "c",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=dw.com&sz=32"
  },
  {
    "id": 41,
    "url": "https://www.politico.eu/feed/",
    "title": "Politico Europe",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=politico.eu&sz=32"
  },
  {
    "id": 43,
    "url": "https://www.spiegel.de/international/index.rss",
    "title": "Der Spiegel International",
    "language": "en",
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "DE",
    "logo_url": "https://www.google.com/s2/favicons?domain=spiegel.de&sz=32"
  },
  {
    "id": 1,
    "url": "https://feeds.bbci.co.uk/news/rss.xml",
    "title": "BBC News",
    "language": None,
    "bias_side": "c",
    "status": "active",
    "created_at": "2025-07-07 15:32:57.933006+00",
    "source_country": "GB",
    "logo_url": "https://static.files.bbci.co.uk/orbit/img/apple-touch/apple-touch-180.png"
  },
  {
    "id": 3,
    "url": "https://feeds.foxnews.com/foxnews/latest",
    "title": "Fox News",
    "language": None,
    "bias_side": "r",
    "status": "active",
    "created_at": "2025-07-07 15:33:02.122878+00",
    "source_country": "FR",
    "logo_url": "https://static.foxnews.com/static/orion/styles/img/fox-news/fox_news_apple_touch_icon.png"
  },
  {
    "id": 35,
    "url": "https://www.aljazeera.com/xml/rss/all.xml",
    "title": "Al Jazeera English – All",
    "language": None,
    "bias_side": "lc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.aljazeera.com/assets/build/img/favicon-32x32-b79e70f6d4.png"
  },
  {
    "id": 36,
    "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "title": "BBC World",
    "language": "en",
    "bias_side": "c",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "GB",
    "logo_url": "https://static.files.bbci.co.uk/orbit/img/apple-touch/apple-touch-180.png"
  },
  {
    "id": 31,
    "url": "https://services.lesechos.fr/rss/les-echos-monde.xml",
    "title": "Les Échos – Monde",
    "language": None,
    "bias_side": "rc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lesechos.fr&sz=32"
  },
  {
    "id": 32,
    "url": "https://services.lesechos.fr/rss/les-echos-politique.xml",
    "title": "Les Échos – Politique",
    "language": None,
    "bias_side": "rc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lesechos.fr&sz=32"
  },
  {
    "id": 30,
    "url": "https://services.lesechos.fr/rss/les-echos-finance-marches.xml",
    "title": "Les Échos – Finances et Marchés",
    "language": None,
    "bias_side": "rc",
    "status": "active",
    "created_at": "2025-07-07 17:50:50.616917+00",
    "source_country": "FR",
    "logo_url": "https://www.google.com/s2/favicons?domain=lesechos.fr&sz=32"
  }
]


async def add_sources(dry_run: bool = False):
    added = []
    updated = []
    async with AsyncSessionLocal() as session:
        for s in SOURCES:
            url = s.get("url")
            if not url:
                print("Skipping source with no URL:", s)
                continue

            # check existing by url
            stmt = select(Source).where(Source.url == url)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            if existing:
                # Optionally update fields if different
                changed = False
                if existing.name != (s.get("title") or existing.name):
                    existing.name = s.get("title") or existing.name
                    changed = True
                if existing.country_code != (s.get("source_country") or existing.country_code):
                    existing.country_code = s.get("source_country") or existing.country_code
                    changed = True
                if changed:
                    updated.append(url)
                    if not dry_run:
                        session.add(existing)
                else:
                    print(f"Already present, skipping: {url}")
                continue

            # Create new Source
            name = s.get("title") or s.get("url")
            # Postgres uses ENUM types for 'kind' and 'trust_tier'; pass plain strings
            kind = "rss"
            country = s.get("source_country")
            lang = s.get("language")
            trust = "B"
            scope = "national"
            created_at = None
            if s.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(s.get("created_at"))
                except Exception:
                    created_at = None

            new_src = Source(
                id=s.get("id"),
                name=name,
                url=url,
                kind=kind,
                country_code=country,
                lang_default=lang,
                trust_tier=trust,
                scope=scope,
                created_at=created_at,
            )

            if not dry_run:
                # Use raw INSERT with explicit casts for enum columns to avoid
                # datatype mismatch (DB uses PostgreSQL ENUM types)
                from sqlalchemy import text

                insert_sql = text(
                    """
                    INSERT INTO sources
                      (name, url, kind, country_code, lang_default, trust_tier, scope, home_area_id, last_fetch_at, created_at)
                    VALUES
                      (:name, :url, CAST(:kind AS source_kind), :country_code, :lang_default, CAST(:trust_tier AS source_trust_tier), CAST(:scope AS source_scope), :home_area_id, :last_fetch_at, :created_at)
                    ON CONFLICT (url) DO NOTHING
                    """
                )

                params = {
                    "name": name,
                    "url": url,
                    "kind": kind,
                    "country_code": country,
                    "lang_default": lang,
                    "trust_tier": trust,
                    "scope": scope,
                    "home_area_id": None,
                    "last_fetch_at": None,
                    "created_at": created_at,
                }

                await session.execute(insert_sql, params)
            added.append(url)

        if not dry_run:
            try:
                await session.commit()
            except IntegrityError as e:
                print("IntegrityError during commit:", e)
                await session.rollback()

    print("\nSummary:")
    print(f"Added: {len(added)}")
    print(f"Updated: {len(updated)}")
    return added, updated


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    added, updated = asyncio.run(add_sources(dry_run=args.dry_run))
    print("Done.")
