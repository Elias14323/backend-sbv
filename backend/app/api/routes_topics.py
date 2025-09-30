"""API routes for topic/cluster management."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.article import Article
from app.models.cluster import Cluster, ClusterRun

router = APIRouter(prefix="/topics", tags=["topics"])


# ========== Pydantic Models ==========


class ClusterBase(BaseModel):
    """Base cluster information."""

    id: int
    run_id: int
    label: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClusterListItem(ClusterBase):
    """Cluster item in list view with article count."""

    article_count: int = Field(..., description="Number of articles in this cluster")


class ArticleInCluster(BaseModel):
    """Article information within a cluster."""

    id: int
    title: str | None = None
    url: str | None = None
    source_id: int
    published_at: datetime | None = None
    lang: str | None = None
    similarity: float | None = Field(None, description="Similarity score to cluster")

    model_config = {"from_attributes": True}


class ClusterDetail(ClusterBase):
    """Detailed cluster information with articles."""

    articles: list[ArticleInCluster] = Field(
        default_factory=list, description="Articles in this cluster"
    )


class TopicsListResponse(BaseModel):
    """Response for topics list endpoint."""

    total: int = Field(..., description="Total number of active clusters")
    topics: list[ClusterListItem] = Field(..., description="List of cluster topics")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")


# ========== Endpoints ==========


@router.get("", response_model=TopicsListResponse)
async def list_topics(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
) -> TopicsListResponse:
    """
    Get a paginated list of active cluster topics.

    Returns clusters from the active cluster run with article counts.
    """

    # Query active clusters using the view
    # We use raw SQL for the view since SQLAlchemy doesn't have ORM models for views
    query = text("""
        SELECT 
            c.id,
            c.run_id,
            c.label,
            c.window_start,
            c.window_end,
            c.created_at,
            COUNT(ac.article_id) as article_count
        FROM v_clusters_active c
        LEFT JOIN v_article_cluster_active ac ON ac.cluster_id = c.id
        GROUP BY c.id, c.run_id, c.label, c.window_start, c.window_end, c.created_at
        ORDER BY c.created_at DESC
        LIMIT :limit OFFSET :skip
    """)

    result = await db.execute(query, {"limit": limit, "skip": skip})
    rows = result.fetchall()

    # Get total count
    count_query = text("SELECT COUNT(*) FROM v_clusters_active")
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    topics = [
        ClusterListItem(
            id=row.id,
            run_id=row.run_id,
            label=row.label,
            window_start=row.window_start,
            window_end=row.window_end,
            created_at=row.created_at,
            article_count=row.article_count or 0,
        )
        for row in rows
    ]

    return TopicsListResponse(
        total=total,
        topics=topics,
        skip=skip,
        limit=limit,
    )


@router.get("/{cluster_id}", response_model=ClusterDetail)
async def get_topic_detail(
    cluster_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClusterDetail:
    """
    Get detailed information about a specific cluster topic.

    Returns the cluster information along with all associated articles.
    """

    # First, verify the cluster exists and is active
    cluster_query = text("""
        SELECT id, run_id, label, window_start, window_end, created_at
        FROM v_clusters_active
        WHERE id = :cluster_id
    """)

    cluster_result = await db.execute(cluster_query, {"cluster_id": cluster_id})
    cluster_row = cluster_result.fetchone()

    if cluster_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster {cluster_id} not found or not active",
        )

    # Get articles in this cluster
    articles_query = text("""
        SELECT 
            a.id,
            a.title,
            a.url,
            a.source_id,
            a.published_at,
            a.lang,
            ac.similarity
        FROM v_article_cluster_active ac
        JOIN articles a ON a.id = ac.article_id
        WHERE ac.cluster_id = :cluster_id
        ORDER BY a.published_at DESC NULLS LAST
    """)

    articles_result = await db.execute(articles_query, {"cluster_id": cluster_id})
    article_rows = articles_result.fetchall()

    articles = [
        ArticleInCluster(
            id=row.id,
            title=row.title,
            url=row.url,
            source_id=row.source_id,
            published_at=row.published_at,
            lang=row.lang,
            similarity=row.similarity,
        )
        for row in article_rows
    ]

    return ClusterDetail(
        id=cluster_row.id,
        run_id=cluster_row.run_id,
        label=cluster_row.label,
        window_start=cluster_row.window_start,
        window_end=cluster_row.window_end,
        created_at=cluster_row.created_at,
        articles=articles,
    )
