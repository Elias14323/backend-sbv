"""Add embedding and clustering tables

Revision ID: 22211ae2db72
Revises: f73907598549
Create Date: 2025-09-30 08:43:26.795331

"""
from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '22211ae2db72'
down_revision: Union[str, Sequence[str], None] = 'f73907598549'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "embedding_spaces",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("dims", sa.Integer(), nullable=False),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("name", "version", name="uq_embedding_spaces_name_version"),
    )

    op.create_table(
        "article_embeddings",
        sa.Column(
            "space_id",
            sa.BigInteger(),
            sa.ForeignKey("embedding_spaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "article_id",
            sa.BigInteger(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(dim=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "cluster_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "space_id",
            sa.BigInteger(),
            sa.ForeignKey("embedding_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("algo", sa.Text(), nullable=False),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="running",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status in ('running','complete','failed')",
            name="ck_cluster_runs_status_valid",
        ),
    )

    op.create_table(
        "clusters",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "run_id",
            sa.BigInteger(),
            sa.ForeignKey("cluster_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "article_clusters",
        sa.Column(
            "run_id",
            sa.BigInteger(),
            sa.ForeignKey("cluster_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "cluster_id",
            sa.BigInteger(),
            sa.ForeignKey("clusters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "article_id",
            sa.BigInteger(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("similarity", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("article_clusters")
    op.drop_table("clusters")
    op.drop_table("cluster_runs")
    op.drop_table("article_embeddings")
    op.drop_table("embedding_spaces")

    op.execute("DROP EXTENSION IF EXISTS vector")
