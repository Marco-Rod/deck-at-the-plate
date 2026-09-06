"""Agrega distribuciones de métricas de liga versionadas.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "league_metric_distributions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("population_size", sa.Integer(), nullable=False),
        sa.Column("sample_size_total", sa.Integer(), nullable=False),
        sa.Column("mean", sa.Numeric(12, 8), nullable=False),
        sa.Column("median", sa.Numeric(12, 8), nullable=False),
        sa.Column("stddev", sa.Numeric(12, 8), nullable=False),
        sa.Column("p05", sa.Numeric(12, 8), nullable=False),
        sa.Column("p10", sa.Numeric(12, 8), nullable=False),
        sa.Column("p25", sa.Numeric(12, 8), nullable=False),
        sa.Column("p50", sa.Numeric(12, 8), nullable=False),
        sa.Column("p75", sa.Numeric(12, 8), nullable=False),
        sa.Column("p90", sa.Numeric(12, 8), nullable=False),
        sa.Column("p95", sa.Numeric(12, 8), nullable=False),
        sa.Column("minimum", sa.Numeric(12, 8), nullable=False),
        sa.Column("maximum", sa.Numeric(12, 8), nullable=False),
        sa.Column("distribution_version", sa.String(length=40), nullable=False),
        sa.Column("data_start_date", sa.Date(), nullable=False),
        sa.Column("data_end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("season >= 1900 AND season <= 2100", name="ck_league_metric_distributions_season"),
        sa.CheckConstraint("population_size > 0", name="ck_league_metric_distributions_population"),
        sa.CheckConstraint("sample_size_total >= population_size", name="ck_league_metric_distributions_sample"),
        sa.CheckConstraint("data_end_date >= data_start_date", name="ck_league_metric_distributions_window"),
        sa.CheckConstraint(
            "minimum <= p05 AND p05 <= p10 AND p10 <= p25 AND p25 <= p50 "
            "AND p50 <= p75 AND p75 <= p90 AND p90 <= p95 AND p95 <= maximum",
            name="ck_league_metric_distributions_percentiles",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "season", "role", "metric", "distribution_version", "data_start_date", "data_end_date",
            name="uq_league_metric_distributions_identity",
        ),
    )
    op.create_index("ix_league_metric_distributions_season", "league_metric_distributions", ["season"])
    op.create_index("ix_league_metric_distributions_role", "league_metric_distributions", ["role"])
    op.create_index("ix_league_metric_distributions_metric", "league_metric_distributions", ["metric"])
    op.create_index("ix_league_metric_distributions_distribution_version", "league_metric_distributions", ["distribution_version"])
    op.create_index("ix_league_metric_distributions_data_end_date", "league_metric_distributions", ["data_end_date"])


def downgrade() -> None:
    op.drop_index("ix_league_metric_distributions_data_end_date", table_name="league_metric_distributions")
    op.drop_index("ix_league_metric_distributions_distribution_version", table_name="league_metric_distributions")
    op.drop_index("ix_league_metric_distributions_metric", table_name="league_metric_distributions")
    op.drop_index("ix_league_metric_distributions_role", table_name="league_metric_distributions")
    op.drop_index("ix_league_metric_distributions_season", table_name="league_metric_distributions")
    op.drop_table("league_metric_distributions")
