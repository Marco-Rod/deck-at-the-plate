"""Add nullable per-attribute evidence; no statistical ratings are changed."""

from alembic import op
import sqlalchemy as sa

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

EVIDENCE_COLUMNS = (
    "contact_evidence", "power_evidence", "vision_evidence", "clutch_evidence",
    "velocity_evidence", "control_evidence", "movement_evidence", "stuff_evidence",
)


def upgrade():
    for column in EVIDENCE_COLUMNS:
        op.add_column("player_ratings", sa.Column(column, sa.Numeric(6, 5), nullable=True))
        op.create_check_constraint(
            f"ck_player_ratings_{column}_range", "player_ratings",
            f"{column} IS NULL OR ({column} >= 0 AND {column} <= 1)",
        )


def downgrade():
    for column in reversed(EVIDENCE_COLUMNS):
        op.drop_constraint(f"ck_player_ratings_{column}_range", "player_ratings", type_="check")
    for column in reversed(EVIDENCE_COLUMNS):
        op.drop_column("player_ratings", column)
