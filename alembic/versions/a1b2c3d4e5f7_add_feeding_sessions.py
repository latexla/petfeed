"""add_feeding_sessions

Revision ID: a1b2c3d4e5f7
Revises: e4f5a6b7c8d9
Create Date: 2026-05-16 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'feeding_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pet_id', sa.Integer(), nullable=False),
        sa.Column('session_date', sa.Date(), nullable=False),
        sa.Column('total_kcal', sa.Numeric(7, 2), nullable=False, server_default='0'),
        sa.Column('protein_g', sa.Numeric(6, 2), nullable=False, server_default='0'),
        sa.Column('fat_g', sa.Numeric(6, 2), nullable=False, server_default='0'),
        sa.Column('calcium_pct', sa.Numeric(5, 1), nullable=True),
        sa.Column('phosphorus_pct', sa.Numeric(5, 1), nullable=True),
        sa.Column('taurine_pct', sa.Numeric(5, 1), nullable=True),
        sa.Column('omega3_pct', sa.Numeric(5, 1), nullable=True),
        sa.Column('kcal_pct', sa.Numeric(5, 1), nullable=True),
        sa.Column('items_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('quality', sa.String(10), nullable=False),
        sa.Column('tips', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['pet_id'], ['pets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pet_id', 'session_date', name='uq_feeding_sessions_pet_date'),
    )


def downgrade() -> None:
    op.drop_table('feeding_sessions')
