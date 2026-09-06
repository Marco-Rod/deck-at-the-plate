"""Agrega scopes por pitch type/family a distribuciones de liga.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("league_metric_distributions", sa.Column("pitch_type", sa.String(12), nullable=True))
    op.add_column("league_metric_distributions", sa.Column("pitch_family", sa.String(20), nullable=True))
    op.drop_constraint("uq_league_metric_distributions_identity", "league_metric_distributions", type_="unique")
    op.create_index(
        "uq_league_metric_distributions_identity",
        "league_metric_distributions",
        [
            "season", "role", "metric", "distribution_version", "data_start_date", "data_end_date",
            sa.text("COALESCE(pitch_type, '')"), sa.text("COALESCE(pitch_family, '')"),
        ],
        unique=True,
    )
    op.create_index("ix_league_metric_distributions_pitch_type", "league_metric_distributions", ["pitch_type"])
    op.create_index("ix_league_metric_distributions_pitch_family", "league_metric_distributions", ["pitch_family"])


def downgrade() -> None:
    # La identidad anterior no puede representar scopes. Se eliminan únicamente
    # las filas que dependen de las columnas introducidas por esta migración.
    op.execute(
        "DELETE FROM league_metric_distributions "
        "WHERE pitch_type IS NOT NULL OR pitch_family IS NOT NULL"
    )
    op.drop_index("ix_league_metric_distributions_pitch_family", table_name="league_metric_distributions")
    op.drop_index("ix_league_metric_distributions_pitch_type", table_name="league_metric_distributions")
    op.drop_index("uq_league_metric_distributions_identity", table_name="league_metric_distributions")
    op.create_unique_constraint(
        "uq_league_metric_distributions_identity",
        "league_metric_distributions",
        ["season", "role", "metric", "distribution_version", "data_start_date", "data_end_date"],
    )
    op.drop_column("league_metric_distributions", "pitch_family")
    op.drop_column("league_metric_distributions", "pitch_type")
