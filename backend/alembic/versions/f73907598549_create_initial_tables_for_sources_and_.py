"""Create initial tables for sources and articles.

Revision ID: f73907598549
Revises:
Create Date: 2025-01-20 01:17:24.349893

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "f73907598549"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create ENUM types only if they don't exist
    # Using raw SQL because Supabase pooler has issues with SQLAlchemy's checkfirst
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE source_kind AS ENUM ('rss', 'site', 'social', 'api');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE source_trust_tier AS ENUM ('A', 'B', 'C');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE source_scope AS ENUM ('local', 'regional', 'national', 'international');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE article_duplicate_kind AS ENUM ('exact', 'near');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("kind", pg.ENUM("rss", "site", "social", "api", name="source_kind", create_type=False), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=True),
        sa.Column("lang_default", sa.Text(), nullable=True),
        sa.Column(
            "trust_tier",
            pg.ENUM("A", "B", "C", name="source_trust_tier", create_type=False),
            nullable=False,
            server_default=sa.text("'B'"),
        ),
        sa.Column("political_axis", pg.JSONB(), nullable=True),
        sa.Column(
            "scope",
            pg.ENUM("local", "regional", "national", "international", name="source_scope", create_type=False),
            nullable=False,
            server_default=sa.text("'national'"),
        ),
        sa.Column("home_area_id", sa.BigInteger(), nullable=True),
        sa.Column("topics", pg.JSONB(), nullable=True),
        sa.Column("last_fetch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "error_rate",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "source_id",
            sa.BigInteger(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("url_canonical", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("lang", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("hash_64", sa.LargeBinary(length=8), nullable=True),
        sa.Column("simhash_64", sa.BigInteger(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "quality_score IS NULL OR quality_score >= 0",
            name="ck_articles_quality_score_non_negative",
        ),
        sa.UniqueConstraint("url", name="uq_articles_url"),
    )

    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_url_canonical", "articles", ["url_canonical"])

    op.create_table(
        "article_duplicates",
        sa.Column(
            "article_id",
            sa.BigInteger(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "duplicate_of_id",
            sa.BigInteger(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", pg.ENUM("exact", "near", name="article_duplicate_kind", create_type=False), nullable=False),
        sa.Column("distance", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("article_duplicates")
    op.drop_index("ix_articles_url_canonical", table_name="articles")
    op.drop_index("ix_articles_published_at", table_name="articles")
    op.drop_table("articles")
    op.drop_table("sources")

    bind = op.get_bind()
    sa.Enum("exact", "near", name="article_duplicate_kind").drop(
        bind,
        checkfirst=True,
    )
    sa.Enum(
        "local",
        "regional",
        "national",
        "international",
        name="source_scope",
    ).drop(bind, checkfirst=True)
    sa.Enum("A", "B", "C", name="source_trust_tier").drop(bind, checkfirst=True)
    sa.Enum("rss", "site", "social", "api", name="source_kind").drop(
        bind,
        checkfirst=True,
    )
