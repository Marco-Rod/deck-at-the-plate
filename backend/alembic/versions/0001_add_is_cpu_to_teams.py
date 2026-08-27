"""Add is_cpu flag to teams table

Revision ID: 0001
Revises: 
Create Date: 2025-03-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar columna is_cpu a la tabla teams
    op.add_column('teams', sa.Column('is_cpu', sa.Boolean(), nullable=False, server_default='false', index=True))


def downgrade() -> None:
    # Remover columna is_cpu de la tabla teams
    op.drop_column('teams', 'is_cpu')
