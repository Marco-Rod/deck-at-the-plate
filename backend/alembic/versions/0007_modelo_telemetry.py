"""modelo game telemetry: pitch_event_logs

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-05

Fase 7 del doc: registro telemetry por pitch. UNIQUE (game_id,
plate_appearance_id, pitch_number) para idempotencia del loader de datos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _batterapproach():
    return pg.ENUM("FASTBALL", "BREAKING", "REACT", "TAKE", name="batterapproach", create_type=False)


def _pitchfamily():
    return pg.ENUM("FASTBALL", "BREAKING", "OFFSPEED", "OTHER", name="pitchfamily", create_type=False)


def upgrade() -> None:
    op.create_table(
        "pitch_event_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("plate_appearance_id", sa.String(length=36), nullable=False),
        sa.Column("pitch_number", sa.SmallInteger(), nullable=False),
        sa.Column("batter_card_id", sa.String(), nullable=False),
        sa.Column("pitcher_card_id", sa.String(), nullable=False),
        sa.Column("batter_player_id", sa.String(length=36), nullable=True),
        sa.Column("pitcher_player_id", sa.String(length=36), nullable=True),
        sa.Column("batter_zone_choice", sa.SmallInteger(), nullable=True),
        sa.Column("batter_approach", _batterapproach(), nullable=False),
        sa.Column("pitcher_zone_choice", sa.SmallInteger(), nullable=False),
        sa.Column("pitch_type", sa.String(length=20), nullable=False),
        sa.Column("pitch_family", _pitchfamily(), nullable=False),
        sa.Column("zone_match", sa.Boolean(), nullable=False),
        sa.Column("approach_match", sa.Boolean(), nullable=True),
        sa.Column("balls_before", sa.SmallInteger(), nullable=False),
        sa.Column("strikes_before", sa.SmallInteger(), nullable=False),
        sa.Column("outs_before", sa.SmallInteger(), nullable=False),
        sa.Column("pitcher_fatigue", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("tactical_modifiers", sa.JSON(), nullable=True),
        sa.Column("matchup_inputs", sa.JSON(), nullable=True),
        sa.Column("probability_distribution", sa.JSON(), nullable=False),
        sa.Column("rng_value", sa.Numeric(precision=10, scale=9), nullable=True),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("engine_version", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("pitch_number >= 1", name="ck_pitch_event_logs_pitch_number_min"),
        sa.CheckConstraint("batter_zone_choice >= 1 AND batter_zone_choice <= 9", name="ck_pitch_event_logs_batter_zone"),
        sa.CheckConstraint("pitcher_zone_choice >= 1 AND pitcher_zone_choice <= 9", name="ck_pitch_event_logs_pitcher_zone"),
        sa.CheckConstraint("balls_before >= 0 AND balls_before <= 3", name="ck_pitch_event_logs_balls_before"),
        sa.CheckConstraint("strikes_before >= 0 AND strikes_before <= 2", name="ck_pitch_event_logs_strikes_before"),
        sa.CheckConstraint("outs_before >= 0 AND outs_before <= 2", name="ck_pitch_event_logs_outs_before"),
        sa.ForeignKeyConstraint(["batter_card_id"], ["player_cards.id"], ondelete="RESTRICT", name="fk_pitch_event_logs_batter_card"),
        sa.ForeignKeyConstraint(["pitcher_card_id"], ["player_cards.id"], ondelete="RESTRICT", name="fk_pitch_event_logs_pitcher_card"),
        sa.ForeignKeyConstraint(["batter_player_id"], ["players.id"], name="fk_pitch_event_logs_batter_player"),
        sa.ForeignKeyConstraint(["pitcher_player_id"], ["players.id"], name="fk_pitch_event_logs_pitcher_player"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "plate_appearance_id", "pitch_number", name="uq_pitch_event_logs_pa_pitch"),
    )
    op.create_index(op.f("ix_pitch_event_logs_game_id"), "pitch_event_logs", ["game_id"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_plate_appearance_id"), "pitch_event_logs", ["plate_appearance_id"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_batter_card_id"), "pitch_event_logs", ["batter_card_id"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_pitcher_card_id"), "pitch_event_logs", ["pitcher_card_id"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_batter_player_id"), "pitch_event_logs", ["batter_player_id"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_pitcher_player_id"), "pitch_event_logs", ["pitcher_player_id"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_batter_approach"), "pitch_event_logs", ["batter_approach"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_pitch_family"), "pitch_event_logs", ["pitch_family"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_pitch_type"), "pitch_event_logs", ["pitch_type"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_zone_match"), "pitch_event_logs", ["zone_match"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_approach_match"), "pitch_event_logs", ["approach_match"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_result"), "pitch_event_logs", ["result"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_engine_version"), "pitch_event_logs", ["engine_version"], unique=False)
    op.create_index(op.f("ix_pitch_event_logs_created_at"), "pitch_event_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pitch_event_logs_pitch_type"), table_name="pitch_event_logs")
    op.drop_table("pitch_event_logs")