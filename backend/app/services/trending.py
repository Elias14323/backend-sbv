"""Service for calculating trending metrics and detecting anomalies."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models.cluster import Cluster, TrendMetric

logger = logging.getLogger(__name__)


async def calculate_cluster_metrics(
    session: AsyncSession,
    cluster_id: int,
    run_id: int,
    timestamp: datetime,
) -> dict[str, int | float]:
    """
    Calculate trending metrics for a specific cluster at a given timestamp.
    
    Args:
        session: Async database session
        cluster_id: ID of the cluster to analyze
        run_id: ID of the cluster run
        timestamp: Timestamp for this measurement
        
    Returns:
        Dictionary with metrics: doc_count, unique_sources, velocity, novelty
    """
    from app.models.article import Article
    from app.models.cluster import ArticleCluster
    
    # 1. Calculate doc_count: total number of articles in cluster
    doc_count_result = await session.execute(
        select(func.count(ArticleCluster.article_id))
        .where(
            ArticleCluster.cluster_id == cluster_id,
            ArticleCluster.run_id == run_id,
        )
    )
    doc_count = doc_count_result.scalar() or 0
    
    # 2. Calculate unique_sources: number of distinct sources
    unique_sources_result = await session.execute(
        select(func.count(func.distinct(Article.source_id)))
        .join(ArticleCluster, ArticleCluster.article_id == Article.id)
        .where(
            ArticleCluster.cluster_id == cluster_id,
            ArticleCluster.run_id == run_id,
        )
    )
    unique_sources = unique_sources_result.scalar() or 0
    
    # 3. Calculate velocity: articles added in last hour
    one_hour_ago = timestamp - timedelta(hours=1)
    velocity_result = await session.execute(
        select(func.count(Article.id))
        .join(ArticleCluster, ArticleCluster.article_id == Article.id)
        .where(
            ArticleCluster.cluster_id == cluster_id,
            ArticleCluster.run_id == run_id,
            Article.created_at >= one_hour_ago,
            Article.created_at <= timestamp,
        )
    )
    velocity = float(velocity_result.scalar() or 0)
    
    # 4. Calculate novelty: proportion of recent articles (< 6 hours)
    six_hours_ago = timestamp - timedelta(hours=6)
    recent_count_result = await session.execute(
        select(func.count(Article.id))
        .join(ArticleCluster, ArticleCluster.article_id == Article.id)
        .where(
            ArticleCluster.cluster_id == cluster_id,
            ArticleCluster.run_id == run_id,
            Article.created_at >= six_hours_ago,
            Article.created_at <= timestamp,
        )
    )
    recent_count = recent_count_result.scalar() or 0
    novelty = float(recent_count / doc_count) if doc_count > 0 else 0.0
    
    logger.debug(
        f"Metrics for cluster {cluster_id}: "
        f"doc_count={doc_count}, unique_sources={unique_sources}, "
        f"velocity={velocity}, novelty={novelty:.2f}"
    )
    
    return {
        "doc_count": doc_count,
        "unique_sources": unique_sources,
        "velocity": velocity,
        "novelty": novelty,
    }


async def calculate_acceleration(
    session: AsyncSession,
    cluster_id: int,
    run_id: int,
    current_velocity: float,
    timestamp: datetime,
) -> float:
    """
    Calculate acceleration (change in velocity over time).
    
    Args:
        session: Async database session
        cluster_id: ID of the cluster
        run_id: ID of the cluster run
        current_velocity: Current velocity value
        timestamp: Current timestamp
        
    Returns:
        Acceleration value (articles/hour²) or 0.0 if no previous data
    """
    from app.models.cluster import TrendMetric
    
    # Get the most recent previous metric (within last 2 hours)
    two_hours_ago = timestamp - timedelta(hours=2)
    
    previous_metric_result = await session.execute(
        select(TrendMetric)
        .where(
            TrendMetric.cluster_id == cluster_id,
            TrendMetric.run_id == run_id,
            TrendMetric.ts < timestamp,
            TrendMetric.ts >= two_hours_ago,
        )
        .order_by(TrendMetric.ts.desc())
        .limit(1)
    )
    previous_metric = previous_metric_result.scalar_one_or_none()
    
    if not previous_metric or previous_metric.velocity is None:
        return 0.0
    
    # Calculate time delta in hours
    time_delta = (timestamp - previous_metric.ts).total_seconds() / 3600
    
    if time_delta == 0:
        return 0.0
    
    # Acceleration = change in velocity / time
    acceleration = (current_velocity - previous_metric.velocity) / time_delta
    
    logger.debug(
        f"Acceleration for cluster {cluster_id}: "
        f"{acceleration:.2f} articles/h² "
        f"(Δv={current_velocity - previous_metric.velocity:.1f}, Δt={time_delta:.2f}h)"
    )
    
    return acceleration


async def detect_anomaly(
    session: AsyncSession,
    cluster_id: int,
    run_id: int,
    current_metrics: dict[str, int | float],
) -> tuple[bool, float, str]:
    """
    Detect if current metrics indicate an anomalous trending event.
    
    Args:
        session: Async database session
        cluster_id: ID of the cluster
        run_id: ID of the cluster run
        current_metrics: Current metrics dictionary with velocity, acceleration, etc.
        
    Returns:
        Tuple of (is_anomaly, score, severity)
        - is_anomaly: True if anomaly detected
        - score: Anomaly score (higher = more significant)
        - severity: 'low', 'medium', 'high', or 'critical'
    """
    velocity = current_metrics.get("velocity", 0.0)
    acceleration = current_metrics.get("acceleration", 0.0)
    doc_count = current_metrics.get("doc_count", 0)
    
    # Thresholds for detection
    VELOCITY_THRESHOLD_LOW = 3.0  # 3 articles/hour
    VELOCITY_THRESHOLD_MEDIUM = 7.0
    VELOCITY_THRESHOLD_HIGH = 15.0
    VELOCITY_THRESHOLD_CRITICAL = 30.0
    
    ACCELERATION_THRESHOLD = 2.0  # 2 articles/hour² increase
    MIN_DOC_COUNT = 3  # Minimum articles to consider for events
    
    # Don't trigger for very small clusters
    if doc_count < MIN_DOC_COUNT:
        return False, 0.0, "low"
    
    # Calculate anomaly score: velocity + 2 * acceleration
    score = velocity + (2.0 * abs(acceleration))
    
    # Check if this is an anomaly
    is_anomaly = (
        velocity >= VELOCITY_THRESHOLD_LOW or
        acceleration >= ACCELERATION_THRESHOLD
    )
    
    if not is_anomaly:
        return False, score, "low"
    
    # Determine severity based on velocity
    if velocity >= VELOCITY_THRESHOLD_CRITICAL:
        severity = "critical"
    elif velocity >= VELOCITY_THRESHOLD_HIGH:
        severity = "high"
    elif velocity >= VELOCITY_THRESHOLD_MEDIUM:
        severity = "medium"
    else:
        severity = "low"
    
    logger.info(
        f"Anomaly detected for cluster {cluster_id}: "
        f"velocity={velocity:.1f}, acceleration={acceleration:.2f}, "
        f"score={score:.2f}, severity={severity}"
    )
    
    return True, score, severity


__all__ = [
    "calculate_acceleration",
    "calculate_cluster_metrics",
    "detect_anomaly",
]
