"""add_breed_knowledge

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS breed_knowledge (
            id SERIAL PRIMARY KEY,
            canonical_name VARCHAR(100) NOT NULL,
            canonical_name_ru VARCHAR(100) NOT NULL,
            species VARCHAR(50) NOT NULL,
            weight_range VARCHAR(100),
            key_risks TEXT,
            adult_meals_per_day INTEGER,
            full_content TEXT NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_breed_knowledge_canonical_name "
        "ON breed_knowledge (canonical_name)"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS breed_knowledge")
