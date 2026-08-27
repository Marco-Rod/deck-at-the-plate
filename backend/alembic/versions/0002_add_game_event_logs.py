"""Add game_event_logs table for game statistics

Revision ID: 0002
Revises: 0001
Create Date: 2025-03-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla game_event_logs
    op.create_table(
        'game_event_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('game_id', sa.String(), nullable=False, index=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('inning', sa.Integer(), nullable=False),
        sa.Column('is_top_inning', sa.Boolean(), nullable=False),
        sa.Column('batter_id', sa.String(), nullable=False),
        sa.Column('pitcher_id', sa.String(), nullable=False),
        sa.Column('batter_name', sa.String(), nullable=True),
        sa.Column('pitcher_name', sa.String(), nullable=True),
        sa.Column('balls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('strikes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('outs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('runners_on_base', sa.JSON(), nullable=True),
        sa.Column('runs_scored', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rbi', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    # Remover tabla game_event_logs
    op.drop_table('game_event_logs')
