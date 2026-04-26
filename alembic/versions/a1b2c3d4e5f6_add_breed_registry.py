"""add_breed_registry

Revision ID: a1b2c3d4e5f6
Revises: 5cbc1aaf70f2
Create Date: 2026-04-26 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '5cbc1aaf70f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS breed_registry (
            id SERIAL NOT NULL,
            canonical_name VARCHAR(100) NOT NULL,
            canonical_name_ru VARCHAR(100) NOT NULL,
            species VARCHAR(50) NOT NULL,
            aliases VARCHAR(200)[] NOT NULL DEFAULT '{}',
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_breed_registry_species ON breed_registry(species)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_breed_registry_species")
    op.drop_table('breed_registry')
