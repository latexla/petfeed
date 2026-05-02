"""meal_builder: food_items table, drop food_category_id, nullable ration grams

Revision ID: a1b2c3
Revises: b2c3d4e5f6a7
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'food_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('name_aliases', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('species', sa.String(50), nullable=False),
        sa.Column('kcal_per_100g', sa.Numeric(6, 2), nullable=False),
        sa.Column('protein_g', sa.Numeric(5, 2), nullable=False),
        sa.Column('fat_g', sa.Numeric(5, 2), nullable=False),
        sa.Column('carb_g', sa.Numeric(5, 2), nullable=False),
        sa.Column('calcium_mg', sa.Numeric(7, 2), nullable=True),
        sa.Column('phosphorus_mg', sa.Numeric(7, 2), nullable=True),
        sa.Column('omega3_mg', sa.Numeric(7, 2), nullable=True),
        sa.Column('taurine_mg', sa.Numeric(7, 2), nullable=True),
        sa.Column('source', sa.String(50), server_default='USDA'),
    )
    # food_category_id was never applied to the DB, so no drop needed here
    op.alter_column('rations', 'daily_food_grams', nullable=True)
    op.alter_column('rations', 'food_per_meal_grams', nullable=True)


def downgrade() -> None:
    op.alter_column('rations', 'daily_food_grams', nullable=False)
    op.alter_column('rations', 'food_per_meal_grams', nullable=False)
    op.drop_table('food_items')
