"""create active cluster views

Revision ID: 0fa290b0f956
Revises: 22211ae2db72
Create Date: 2025-09-30 18:41:56.885202

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fa290b0f956'
down_revision: Union[str, Sequence[str], None] = '22211ae2db72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Create view for active clusters
    op.execute("""
        CREATE VIEW v_clusters_active AS
        SELECT c.* 
        FROM clusters c 
        JOIN cluster_runs r ON r.id = c.run_id 
        WHERE r.is_active = true
    """)
    
    # Create view for active article-cluster assignments
    op.execute("""
        CREATE VIEW v_article_cluster_active AS
        SELECT ac.* 
        FROM article_clusters ac 
        JOIN cluster_runs r ON r.id = ac.run_id 
        WHERE r.is_active = true
    """)


def downgrade() -> None:
    """Downgrade schema."""
    
    op.execute("DROP VIEW IF EXISTS v_article_cluster_active")
    op.execute("DROP VIEW IF EXISTS v_clusters_active")
