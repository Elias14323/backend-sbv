"""Database models related to news sources and articles."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:  # pragma: no cover
    from .cluster import ArticleCluster, ArticleEmbedding

from .base import Base


class SourceKind(StrEnum):
    RSS = "rss"
    SITE = "site"
    SOCIAL = "social"
    API = "api"


class SourceScope(StrEnum):
    LOCAL = "local"
    REGIONAL = "regional"
    NATIONAL = "national"
    INTERNATIONAL = "international"


class TrustTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class DuplicateKind(StrEnum):
    EXACT = "exact"
    NEAR = "near"


class Source(Base):
    """Media source metadata and health information."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # 'rss', 'site', 'social', 'api'
    country_code: Mapped[str | None] = mapped_column(Text)
    lang_default: Mapped[str | None] = mapped_column(Text)
    trust_tier: Mapped[str] = mapped_column(Text, nullable=False, server_default="B")  # 'A', 'B', 'C'
    political_axis: Mapped[dict[str, float] | None] = mapped_column(JSONB)
    scope: Mapped[str] = mapped_column(Text, nullable=False, server_default="national")  # 'local', 'regional', 'national', 'international'
    home_area_id: Mapped[int | None] = mapped_column(BigInteger)
    topics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    articles: Mapped[list["Article"]] = relationship(
        "Article",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class Article(Base):
    """Normalized article content fetched from a source."""

    __tablename__ = "articles"

    __table_args__ = (
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_url_canonical", "url_canonical"),
        CheckConstraint(
            "quality_score IS NULL OR quality_score >= 0",
            name="ck_articles_quality_score_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(Text, unique=True)
    url_canonical: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    lang: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_html: Mapped[str | None] = mapped_column(Text)
    text_content: Mapped[str | None] = mapped_column(Text)
    hash_64: Mapped[bytes | None] = mapped_column(LargeBinary(8))
    simhash_64: Mapped[int | None] = mapped_column(BigInteger)
    quality_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    source: Mapped[Source] = relationship(back_populates="articles")
    duplicate_link: Mapped["ArticleDuplicate | None"] = relationship(
        "ArticleDuplicate",
        back_populates="article",
        foreign_keys="ArticleDuplicate.article_id",
        cascade="all, delete-orphan",
        uselist=False,
    )
    incoming_duplicates: Mapped[list["ArticleDuplicate"]] = relationship(
        "ArticleDuplicate",
        back_populates="duplicate_of",
        foreign_keys="ArticleDuplicate.duplicate_of_id",
    )
    embedding_entry: Mapped["ArticleEmbedding | None"] = relationship(
        "ArticleEmbedding",
        back_populates="article",
        cascade="all, delete-orphan",
        uselist=False,
    )
    cluster_assignments: Mapped[list["ArticleCluster"]] = relationship(
        "ArticleCluster",
        back_populates="article",
        cascade="all, delete-orphan",
    )


class ArticleDuplicate(Base):
    """Links articles that are exact or near duplicates."""

    __tablename__ = "article_duplicates"

    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    duplicate_of_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[DuplicateKind] = mapped_column(
        Enum(DuplicateKind, name="article_duplicate_kind"),
        nullable=False,
    )
    distance: Mapped[int | None] = mapped_column(Integer)

    article: Mapped[Article] = relationship(
        "Article",
        foreign_keys=[article_id],
        back_populates="duplicate_link",
    )
    duplicate_of: Mapped[Article] = relationship(
        "Article",
        foreign_keys=[duplicate_of_id],
        back_populates="incoming_duplicates",
    )


__all__ = [
    "Article",
    "ArticleDuplicate",
    "DuplicateKind",
    "Source",
    "SourceKind",
    "SourceScope",
    "TrustTier",
]
