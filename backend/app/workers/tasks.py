"""Celery task definitions for the backend."""

from __future__ import annotations

import asyncio
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
from app.core.mistral import get_mistral_client
from app.models.article import Article, Source
from app.models.cluster import ArticleEmbedding, EmbeddingSpace

from .celery_app import app

logger = logging.getLogger(__name__)


async def _fetch_source(session: AsyncSession, source_id: int) -> Source | None:
    """Return the Source entity for the given identifier."""

    result = await session.execute(select(Source).where(Source.id == source_id))
    return result.scalar_one_or_none()


def _hamming_distance(left: int, right: int) -> int:
    """Compute the Hamming distance between two 64-bit integers."""

    return (left ^ right).bit_count()


DEFAULT_EMBEDDING_SPACE = "mistral-embed"
DEFAULT_EMBEDDING_PROVIDER = "mistral"
DEFAULT_EMBEDDING_DIMS = 1024


async def _get_or_create_embedding_space(session: AsyncSession) -> EmbeddingSpace:
    stmt = select(EmbeddingSpace).where(EmbeddingSpace.name == DEFAULT_EMBEDDING_SPACE)
    result = await session.execute(stmt)
    space = result.scalar_one_or_none()
    if space is not None:
        return space

    space = EmbeddingSpace(
        name=DEFAULT_EMBEDDING_SPACE,
        provider=DEFAULT_EMBEDDING_PROVIDER,
        dims=DEFAULT_EMBEDDING_DIMS,
        version="system",
        notes="Default embedding space created automatically.",
    )
    session.add(space)
    await session.flush()
    return space


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

    embed_and_cluster_article.delay(article_id=created_id)

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


@app.task(name="tasks.embed_and_cluster_article")
async def embed_and_cluster_article(article_id: int) -> dict[str, Any]:
    """Generate an embedding for an article and schedule clustering."""

    async with AsyncSessionLocal() as session:
        article = await session.get(Article, article_id)
        if article is None:
            logger.warning(
                "Article not found for embedding",
                extra={"article_id": article_id},
            )
            return {"status": "missing"}

        if not article.text_content:
            logger.info(
                "Article has no text content; skipping embedding",
                extra={"article_id": article_id},
            )
            return {"status": "skipped", "reason": "no-text"}

        space = await _get_or_create_embedding_space(session)
        space_id = space.id

        existing = await session.get(ArticleEmbedding, (space_id, article_id))
        if existing is not None:
            logger.info(
                "Embedding already exists",
                extra={"article_id": article_id, "space_id": space_id},
            )
            return {"status": "exists", "space_id": space.id}

        summary_parts = [article.title or "", article.text_content[:2000]]
        embedding_input = "\n\n".join(part for part in summary_parts if part).strip()
        if not embedding_input:
            logger.info(
                "Embedding input empty for article",
                extra={"article_id": article_id},
            )
            return {"status": "skipped", "reason": "empty-input"}

        client = get_mistral_client()

        try:
            response = await asyncio.to_thread(
                client.embeddings.create,
                model=space.name,
                input=[embedding_input],
            )
        except Exception as exc:  # pragma: no cover - network
            logger.error(
                "Failed to generate embedding",
                exc_info=exc,
                extra={"article_id": article_id, "space_id": space_id},
            )
            return {"status": "error", "reason": "embedding"}

        embedding_data = response.data[0].embedding
        if len(embedding_data) != space.dims:
            logger.warning(
                "Embedding dimension mismatch",
                extra={
                    "article_id": article_id,
                    "expected_dims": space.dims,
                    "received_dims": len(embedding_data),
                },
            )
            space.dims = len(embedding_data)

        article_embedding = ArticleEmbedding(
            space_id=space_id,
            article_id=article_id,
            embedding=embedding_data,
        )
        session.add(article_embedding)
        await session.commit()

    logger.info(
        "Clustering pending implementation",
        extra={"article_id": article_id},
    )

    return {"status": "embedded", "space_id": space_id}
