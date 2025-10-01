"""Search API endpoints using Meilisearch."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.meili import search_articles

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    lang: str | None = Query(None, description="Filter by language (e.g., 'fr', 'en')"),
    source_id: int | None = Query(None, description="Filter by source ID"),
) -> dict[str, Any]:
    """Search articles using full-text search with typo tolerance.
    
    Returns:
        - hits: List of matching articles
        - query: The search query
        - processingTimeMs: Search duration
        - limit: Results per page
        - offset: Current offset
        - estimatedTotalHits: Total matching documents
    """
    
    # Build Meilisearch filter string
    filters = []
    if lang:
        filters.append(f"lang = {lang}")
    if source_id is not None:
        filters.append(f"source_id = {source_id}")
    
    filter_string = " AND ".join(filters) if filters else None
    
    try:
        results = await search_articles(
            query=q,
            limit=limit,
            offset=offset,
            filters=filter_string,
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        ) from e


@router.get("/health")
async def search_health() -> dict[str, str]:
    """Health check endpoint for search service."""
    
    from app.core.meili import get_meili_client
    
    try:
        client = await get_meili_client()
        health = await client.health()
        # health is a Health object, access its status attribute
        return {"status": "ok", "meilisearch": health.status if hasattr(health, 'status') else "available"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
