"""Celery task definitions for the backend."""

from __future__ import annotations

import logging
from typing import Any

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.models.article import Source

from .celery_app import app

logger = logging.getLogger(__name__)


async def _fetch_source(session: AsyncSession, source_id: int) -> Source | None:
    """Return the Source entity for the given identifier."""

    result = await session.execute(select(Source).where(Source.id == source_id))
    return result.scalar_one_or_none()


@app.task(name="tasks.process_article_url")
def process_article_url(url: str, source_id: int) -> None:
    """Placeholder task for article processing downstream."""

    logger.info("Received article URL", extra={"url": url, "source_id": source_id})


@app.task(name="tasks.ingest_source")
async def ingest_source(source_id: int) -> dict[str, Any]:
    """Fetch a source feed, parse entries, and enqueue article processing tasks."""

    async with AsyncSessionLocal() as session:
        source = await _fetch_source(session, source_id)
        if source is None:
            logger.warning("Source not found", extra={"source_id": source_id})
            return {"status": "missing"}

        if not source.url:
            logger.warning("Source has no URL declared", extra={"source_id": source_id})
            return {"status": "invalid"}

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.get(source.url)
            response.raise_for_status()

        feed = feedparser.parse(response.content)
        entries = getattr(feed, "entries", []) or []

        for entry in entries:
            url = getattr(entry, "link", None)
            if not url:
                logger.debug(
                    "Skipping feed entry without link",
                    extra={"source_id": source_id},
                )
                continue
            process_article_url.delay(url=url, source_id=source_id)

        logger.info(
            "Ingestion complete",
            extra={
                "source_id": source_id,
                "entries": len(entries),
            },
        )

        return {"status": "ok", "entries": len(entries)}
