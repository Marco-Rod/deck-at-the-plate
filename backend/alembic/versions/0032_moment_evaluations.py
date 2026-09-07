"""Agrega evaluaciones versionadas de MomentContext.

Revision ID: 0032
Revises: 0031
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0032"
down_revision: Union[str, None] = "0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    moment_type = postgresql.ENUM(
        "WALK_OFF_HR", name="momenttype", create_type=False
    )
    moment_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "moment_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("moment_context_id", sa.String(length=36), nullable=False),
        sa.Column("moment_type", moment_type, nullable=False),
        sa.Column("significance_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("performance_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("leverage_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column(
            "statistical_uncommonness",
            sa.Numeric(precision=6, scale=5),
            nullable=False,
        ),
        sa.Column("evaluation_version", sa.String(length=40), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "significance_score >= 0 AND significance_score <= 1",
            name="ck_moment_evaluations_significance_score",
        ),
        sa.CheckConstraint(
            "performance_score >= 0 AND performance_score <= 1",
            name="ck_moment_evaluations_performance_score",
        ),
        sa.CheckConstraint(
            "leverage_score >= 0 AND leverage_score <= 1",
            name="ck_moment_evaluations_leverage_score",
        ),
        sa.CheckConstraint(
            "statistical_uncommonness >= 0 AND statistical_uncommonness <= 1",
            name="ck_moment_evaluations_statistical_uncommonness",
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64", name="ck_moment_evaluations_input_hash"
        ),
        sa.ForeignKeyConstraint(
            ["moment_context_id"], ["moment_contexts.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "moment_context_id",
            "evaluation_version",
            name="uq_moment_evaluations_identity",
        ),
    )
    for column in (
        "moment_context_id",
        "moment_type",
        "evaluation_version",
        "input_hash",
    ):
        op.create_index(
            f"ix_moment_evaluations_{column}", "moment_evaluations", [column]
        )


def downgrade() -> None:
    op.drop_table("moment_evaluations")
    postgresql.ENUM(name="momenttype").drop(op.get_bind(), checkfirst=True)
