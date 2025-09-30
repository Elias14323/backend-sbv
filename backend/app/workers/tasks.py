"""Celery task definitions for the backend."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import timezone
from typing import Any

import feedparser
import httpx
import trafilatura
from dateutil import parser as date_parser
from simhash import Simhash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.models.article import Article, Source

from .celery_app import app

logger = logging.getLogger(__name__)


async def _fetch_source(session: AsyncSession, source_id: int) -> Source | None:
    """Return the Source entity for the given identifier."""

    result = await session.execute(select(Source).where(Source.id == source_id))
    return result.scalar_one_or_none()


def _hamming_distance(left: int, right: int) -> int:
    """Compute the Hamming distance between two 64-bit integers."""

    return (left ^ right).bit_count()


@app.task(name="tasks.process_article_url")
async def process_article_url(url: str, source_id: int) -> dict[str, Any]:
    """Fetch, normalize, dedupe, and persist an individual article."""

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            follow_redirects=True,
            headers={"User-Agent": "backend-ingestion-bot/0.1"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.error(
            "Timeout while fetching article",
            exc_info=exc,
            extra={"source_id": source_id, "url": url},
        )
        return {"status": "error", "reason": "timeout"}
    except httpx.HTTPError as exc:
        logger.error(
            "HTTP error while fetching article",
            exc_info=exc,
            extra={"source_id": source_id, "url": url},
        )
        return {"status": "error", "reason": "http"}

    html = response.text

    try:
        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            json_output=True,
        )
    except Exception as exc:  # pragma: no cover - extraction rarely raises
        logger.error(
            "Trafilatura extraction failure",
            exc_info=exc,
            extra={"source_id": source_id, "url": url},
        )
        return {"status": "error", "reason": "extract"}

    if not extracted:
        logger.info(
            "Extraction returned no content",
            extra={"source_id": source_id, "url": url},
        )
        return {"status": "skipped", "reason": "empty"}

    try:
        metadata = json.loads(extracted)
    except json.JSONDecodeError as exc:
        logger.error(
            "Failed to decode extraction payload",
            exc_info=exc,
            extra={"source_id": source_id, "url": url},
        )
        return {"status": "error", "reason": "extract-json"}

    text_content = (metadata.get("text") or "").strip()
    if not text_content:
        logger.info(
            "No usable text content extracted",
            extra={"source_id": source_id, "url": url},
        )
        return {"status": "skipped", "reason": "empty-text"}

    title = (metadata.get("title") or "").strip() or None
    authors_data = metadata.get("authors")
    if isinstance(authors_data, list):
        author = ", ".join(a for a in authors_data if a)
    else:
        author = authors_data
    author = author or None

    lang = metadata.get("language") or metadata.get("lang") or None

    published_at = None
    for candidate_key in ("date", "date_publish", "date_modify"):
        value = metadata.get(candidate_key)
        if not value:
            continue
        try:
            parsed = date_parser.parse(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if parsed is None:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        published_at = parsed
        break

    simhash_value = int(Simhash(text_content, f=64).value)
    content_hash = hashlib.blake2b(
        text_content.encode("utf-8"),
        digest_size=8,
    ).digest()

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Article).where(Article.url == url))
        if existing is not None:
            logger.info(
                "Article already ingested (same URL)",
                extra={"source_id": source_id, "url": url, "article_id": existing.id},
            )
            return {"status": "duplicate", "article_id": existing.id}

        duplicates_stmt = select(Article.id, Article.simhash_64).where(
            Article.source_id == source_id,
            Article.simhash_64.isnot(None),
        )
        duplicates_result = await session.execute(duplicates_stmt)
        for article_id, existing_hash in duplicates_result.all():
            if existing_hash is None:
                continue
            if _hamming_distance(existing_hash, simhash_value) <= 3:
                logger.info(
                    "Article considered duplicate via simhash",
                    extra={
                        "source_id": source_id,
                        "url": url,
                        "duplicate_of": article_id,
                    },
                )
                return {"status": "duplicate", "article_id": article_id}

        article = Article(
            source_id=source_id,
            url=url,
            url_canonical=metadata.get("canonical_url") or url,
            title=title,
            author=author,
            lang=lang,
            published_at=published_at,
            raw_html=html,
            text_content=text_content,
            hash_64=content_hash,
            simhash_64=simhash_value,
        )

        session.add(article)
        await session.flush()
        created_id = article.id
        await session.commit()

        logger.info(
            "Article stored",
            extra={"source_id": source_id, "url": url, "article_id": created_id},
        )

        return {"status": "stored", "article_id": created_id}


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

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(source.url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error(
                "Timeout while fetching source feed",
                exc_info=exc,
                extra={"source_id": source_id, "url": source.url},
            )
            return {"status": "error", "reason": "timeout"}
        except httpx.HTTPError as exc:
            logger.error(
                "HTTP error while fetching source feed",
                exc_info=exc,
                extra={"source_id": source_id, "url": source.url},
            )
            return {"status": "error", "reason": "http"}

        try:
            feed = feedparser.parse(response.content)
        except Exception as exc:  # pragma: no cover - feedparser rarely raises
            logger.error(
                "Failed to parse feed content",
                exc_info=exc,
                extra={"source_id": source_id, "url": source.url},
            )
            return {"status": "error", "reason": "parse"}

        if getattr(feed, "bozo", False):
            bozo_exc = getattr(feed, "bozo_exception", None)
            logger.warning(
                "Feed parsing reported anomalies",
                extra={
                    "source_id": source_id,
                    "url": source.url,
                    "bozo_exception": str(bozo_exc) if bozo_exc else None,
                },
            )
        entries = getattr(feed, "entries", []) or []

        for entry in entries:
            entry_url = getattr(entry, "link", None)
            if not entry_url:
                logger.debug(
                    "Skipping feed entry without link",
                    extra={"source_id": source_id},
                )
                continue
            process_article_url.delay(url=entry_url, source_id=source_id)

        logger.info(
            "Ingestion complete",
            extra={
                "source_id": source_id,
                "entries": len(entries),
            },
        )

        return {"status": "ok", "entries": len(entries)}
