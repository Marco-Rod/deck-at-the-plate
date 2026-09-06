"""Separa promedio poblacional y baseline ponderado de liga.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Las distribuciones existentes no conservan los numeradores individuales
    # necesarios para reconstruir el ponderado. Se inicializan con el promedio
    # anterior y el siguiente build idempotente calcula el baseline correcto.
    op.alter_column("league_metric_distributions", "mean", new_column_name="population_mean")
    op.add_column(
        "league_metric_distributions",
        sa.Column("league_baseline", sa.Numeric(12, 8), nullable=True),
    )
    op.execute(
        "UPDATE league_metric_distributions "
        "SET league_baseline = population_mean "
        "WHERE league_baseline IS NULL"
    )
    op.alter_column("league_metric_distributions", "league_baseline", nullable=False)


def downgrade() -> None:
    op.drop_column("league_metric_distributions", "league_baseline")
    op.alter_column("league_metric_distributions", "population_mean", new_column_name="mean")
