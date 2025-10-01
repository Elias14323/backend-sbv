"""Meilisearch client initialization and configuration."""

from typing import Any

from meilisearch_python_async import Client
from meilisearch_python_async.models.settings import MeilisearchSettings

from app.core.config import settings

# Global client instance
_meili_client: Client | None = None


async def get_meili_client() -> Client:
    """Return cached Meilisearch client, initializing if needed."""
    global _meili_client
    
    if _meili_client is None:
        _meili_client = Client(settings.meili_host, settings.meili_api_key)
    
    return _meili_client


async def setup_articles_index() -> None:
    """Configure the articles search index with proper settings."""
    client = await get_meili_client()
    
    # Create or get the index with explicit primary key
    try:
        index = await client.create_index("articles", primary_key="id")
    except Exception:
        # Index already exists
        index = client.index("articles")
    
    # Configure index settings
    index_settings = MeilisearchSettings(
        filterable_attributes=["lang", "source_id", "published_at"],
        sortable_attributes=["published_at"],
        searchable_attributes=["title", "text_content"],
        stop_words=[
            # French stop words
            "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux",
            "ce", "cette", "ces", "mon", "ton", "son", "ma", "ta", "sa",
            "mes", "tes", "ses", "notre", "votre", "leur", "nos", "vos", "leurs",
            "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
            "me", "te", "se", "moi", "toi", "lui", "eux",
            "est", "sont", "était", "étaient", "sera", "seront",
            "a", "ont", "avait", "avaient", "aura", "auront",
            "et", "ou", "mais", "donc", "or", "ni", "car",
            "dans", "sur", "sous", "avec", "sans", "pour", "par", "vers", "chez",
            "à", "en", "y",
            # English stop words
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "should", "could", "may", "might", "must",
            "i", "you", "he", "she", "it", "we", "they",
            "me", "him", "her", "us", "them",
            "my", "your", "his", "its", "our", "their",
            "this", "that", "these", "those",
        ],
    )
    
    await index.update_settings(index_settings)


async def index_article(article_data: dict[str, Any]) -> None:
    """Add or update a single article in the search index.
    
    Args:
        article_data: Dict with keys: id, title, text_content, lang, source_id, published_at
    """
    client = await get_meili_client()
    index = client.index("articles")
    
    # Prepare document for indexing
    # Truncate text_content to avoid indexing very long articles
    text_content = article_data.get("text_content", "")
    if text_content and len(text_content) > 5000:
        text_content = text_content[:5000] + "..."
    
    document = {
        "id": article_data["id"],
        "title": article_data.get("title", ""),
        "text_content": text_content,
        "lang": article_data.get("lang", ""),
        "source_id": article_data.get("source_id"),
        "published_at": article_data.get("published_at").isoformat() if article_data.get("published_at") else None,
    }
    
    await index.add_documents([document])


async def search_articles(
    query: str,
    limit: int = 20,
    offset: int = 0,
    filters: str | None = None,
) -> dict[str, Any]:
    """Search articles in Meilisearch.
    
    Args:
        query: Search query string
        limit: Maximum number of results
        offset: Pagination offset
        filters: Meilisearch filter string (e.g., "lang = fr")
    
    Returns:
        Search results with hits, total count, etc.
    """
    client = await get_meili_client()
    index = client.index("articles")
    
    search_params = {
        "limit": limit,
        "offset": offset,
    }
    
    if filters:
        search_params["filter"] = filters
    
    results = await index.search(query, **search_params)
    
    # Convert SearchResults object to dict
    return {
        "hits": results.hits,
        "query": results.query,
        "processingTimeMs": results.processing_time_ms,
        "limit": results.limit,
        "offset": results.offset,
        "estimatedTotalHits": results.estimated_total_hits,
    }


__all__ = [
    "get_meili_client",
    "setup_articles_index",
    "index_article",
    "search_articles",
]
