"""Models for embeddings and clustering workflow."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .article import Article


class EmbeddingSpace(Base):
    """Registry of available embedding spaces."""

    __tablename__ = "embedding_spaces"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    dims: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_embedding_spaces_name_version"),
    )

    embeddings: Mapped[list["ArticleEmbedding"]] = relationship(
        back_populates="space",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list["ClusterRun"]] = relationship(
        back_populates="space",
        cascade="all, delete-orphan",
    )


class ArticleEmbedding(Base):
    """Stores vector representations for articles."""

    __tablename__ = "article_embeddings"

    space_id: Mapped[int] = mapped_column(
        ForeignKey("embedding_spaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(dim=1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    space: Mapped[EmbeddingSpace] = relationship(back_populates="embeddings")
    article: Mapped["Article"] = relationship(back_populates="embedding_entry")


class ClusterRun(Base):
    """Represents a clustering pass for a given embedding space."""

    __tablename__ = "cluster_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    space_id: Mapped[int] = mapped_column(
        ForeignKey("embedding_spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    algo: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="running")
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status in ('running','complete','failed')",
            name="ck_cluster_runs_status_valid",
        ),
    )

    space: Mapped[EmbeddingSpace] = relationship(back_populates="runs")
    clusters: Mapped[list["Cluster"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list["ArticleCluster"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class Cluster(Base):
    """Describes a group of related articles produced by a run."""

    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("cluster_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str | None] = mapped_column(Text)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped[ClusterRun] = relationship(back_populates="clusters")
    assignments: Mapped[list["ArticleCluster"]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
    )


class ArticleCluster(Base):
    """Associates articles to clusters with similarity information."""

    __tablename__ = "article_clusters"

    run_id: Mapped[int] = mapped_column(
        ForeignKey("cluster_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"),
        primary_key=True,
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    similarity: Mapped[float | None] = mapped_column(Float)

    run: Mapped[ClusterRun] = relationship(back_populates="assignments")
    cluster: Mapped[Cluster] = relationship(back_populates="assignments")
    article: Mapped["Article"] = relationship(back_populates="cluster_assignments")


class ClusterSummary(Base):
    """Stores AI-generated summaries and bias analysis for clusters."""

    __tablename__ = "cluster_summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[int] = mapped_column(
        ForeignKey("cluster_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    summarizer_engine: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="mistral-large-latest",
    )
    engine_version: Mapped[str | None] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    summary_md: Mapped[str | None] = mapped_column(Text)
    bias_analysis_md: Mapped[str | None] = mapped_column(Text)
    timeline_md: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    generation_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "cluster_id",
            "version",
            name="uq_cluster_summaries_cluster_version",
        ),
    )

    cluster: Mapped[Cluster] = relationship()
    run: Mapped[ClusterRun] = relationship()


class TrendMetric(Base):
    """Stores trending metrics for clusters over time."""

    __tablename__ = "trend_metrics"

    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
    )
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"),
        primary_key=True,
    )
    run_id: Mapped[int] = mapped_column(
        ForeignKey("cluster_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    doc_count: Mapped[int | None] = mapped_column(Integer)
    unique_sources: Mapped[int | None] = mapped_column(Integer)
    velocity: Mapped[float | None] = mapped_column(Float)
    acceleration: Mapped[float | None] = mapped_column(Float)
    novelty: Mapped[float | None] = mapped_column(Float)
    locality: Mapped[float | None] = mapped_column(Float)

    cluster: Mapped[Cluster] = relationship()
    run: Mapped[ClusterRun] = relationship()


class Event(Base):
    """Stores detected trending events (breaking news, anomalies)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("cluster_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"),
        nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    locality: Mapped[float | None] = mapped_column(Float)
    label: Mapped[str | None] = mapped_column(Text)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "severity in ('low','medium','high','critical')",
            name="ck_events_severity_valid",
        ),
    )

    cluster: Mapped[Cluster] = relationship()
    run: Mapped[ClusterRun] = relationship()


__all__ = [
    "ArticleCluster",
    "ArticleEmbedding",
    "Cluster",
    "ClusterRun",
    "ClusterSummary",
    "EmbeddingSpace",
    "Event",
    "TrendMetric",
]
