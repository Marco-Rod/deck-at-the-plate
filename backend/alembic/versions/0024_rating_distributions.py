"""Agrega distribuciones de ratings oficiales para calibrar rarity.

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rating_distributions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("rating_model_version", sa.String(40), nullable=False),
        sa.Column("source_distribution_version", sa.String(40), nullable=False),
        sa.Column("rarity_model_version", sa.String(40), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("population_size", sa.Integer(), nullable=False),
        sa.Column("minimum", sa.Numeric(12, 8), nullable=False),
        sa.Column("p05", sa.Numeric(12, 8), nullable=False),
        sa.Column("p10", sa.Numeric(12, 8), nullable=False),
        sa.Column("p25", sa.Numeric(12, 8), nullable=False),
        sa.Column("p50", sa.Numeric(12, 8), nullable=False),
        sa.Column("p75", sa.Numeric(12, 8), nullable=False),
        sa.Column("p90", sa.Numeric(12, 8), nullable=False),
        sa.Column("p95", sa.Numeric(12, 8), nullable=False),
        sa.Column("maximum", sa.Numeric(12, 8), nullable=False),
        sa.Column("population_mean", sa.Numeric(12, 8), nullable=False),
        sa.Column("data_start_date", sa.Date(), nullable=False),
        sa.Column("data_end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("season >= 1900 AND season <= 2100", name="ck_rating_distributions_season"),
        sa.CheckConstraint("role IN ('BATTER', 'PITCHER')", name="ck_rating_distributions_role"),
        sa.CheckConstraint("population_size > 0", name="ck_rating_distributions_population"),
        sa.CheckConstraint("data_end_date >= data_start_date", name="ck_rating_distributions_window"),
        sa.CheckConstraint(
            "minimum <= p05 AND p05 <= p10 AND p10 <= p25 AND p25 <= p50 "
            "AND p50 <= p75 AND p75 <= p90 AND p90 <= p95 AND p95 <= maximum",
            name="ck_rating_distributions_percentiles",
        ),
        sa.CheckConstraint("minimum >= 40 AND maximum <= 99", name="ck_rating_distributions_range"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_rating_distributions_identity",
        "rating_distributions",
        [
            "season", "role", "metric", "rating_model_version",
            "source_distribution_version", "rarity_model_version",
            "data_start_date", "data_end_date",
        ],
        unique=True,
    )
    for column in (
        "season", "role", "rating_model_version", "source_distribution_version",
        "rarity_model_version", "metric", "data_end_date",
    ):
        op.create_index(f"ix_rating_distributions_{column}", "rating_distributions", [column])


def downgrade() -> None:
    for column in reversed((
        "season", "role", "rating_model_version", "source_distribution_version",
        "rarity_model_version", "metric", "data_end_date",
    )):
        op.drop_index(f"ix_rating_distributions_{column}", table_name="rating_distributions")
    op.drop_index("uq_rating_distributions_identity", table_name="rating_distributions")
    op.drop_table("rating_distributions")
