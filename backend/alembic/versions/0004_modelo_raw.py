"""modelo raw: raw_pitch_events

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-05

Fase 3. RAW → raw_pitch_events con UNIQUE idempotente (game_pk, at_bat_number,
pitch_number) para que el ETL pueda reejecutar ventanas sin duplicados.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _handedness():
    return pg.ENUM("L", "R", "S", name="handedness", create_type=False)


def _throwhand():
    return pg.ENUM("L", "R", name="throwhand", create_type=False)


def _pitchfamily():
    return pg.ENUM("FASTBALL", "BREAKING", "OFFSPEED", "OTHER", name="pitchfamily", create_type=False)


def upgrade() -> None:
    op.create_table(
        "raw_pitch_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("import_run_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("game_pk", sa.BigInteger(), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("at_bat_number", sa.Integer(), nullable=False),
        sa.Column("pitch_number", sa.SmallInteger(), nullable=False),
        sa.Column("batter_mlb_id", sa.Integer(), nullable=False),
        sa.Column("pitcher_mlb_id", sa.Integer(), nullable=False),
        sa.Column("stand", _handedness(), nullable=True),
        sa.Column("p_throws", _throwhand(), nullable=True),
        sa.Column("balls", sa.SmallInteger(), nullable=True),
        sa.Column("strikes", sa.SmallInteger(), nullable=True),
        sa.Column("outs_when_up", sa.SmallInteger(), nullable=True),
        sa.Column("inning", sa.SmallInteger(), nullable=True),
        sa.Column("inning_topbot", sa.String(length=3), nullable=True),
        sa.Column("pitch_type", sa.String(length=12), nullable=True),
        sa.Column("pitch_family", _pitchfamily(), nullable=True),
        sa.Column("release_speed", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("release_spin_rate", sa.Numeric(precision=7, scale=2), nullable=True),
        sa.Column("pfx_x", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("pfx_z", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("plate_x", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("plate_z", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("statcast_zone", sa.SmallInteger(), nullable=True),
        sa.Column("game_zone", sa.SmallInteger(), nullable=True),
        sa.Column("description", sa.String(length=50), nullable=True),
        sa.Column("event", sa.String(length=50), nullable=True),
        sa.Column("bb_type", sa.String(length=20), nullable=True),
        sa.Column("launch_speed", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("launch_angle", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("estimated_woba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("woba_value", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("home_team", sa.String(length=3), nullable=True),
        sa.Column("away_team", sa.String(length=3), nullable=True),
        sa.Column("raw_payload_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("balls >= 0 AND balls <= 3", name="ck_raw_pitch_events_balls_range"),
        sa.CheckConstraint("strikes >= 0 AND strikes <= 2", name="ck_raw_pitch_events_strikes_range"),
        sa.CheckConstraint("outs_when_up >= 0 AND outs_when_up <= 2", name="ck_raw_pitch_events_outs_range"),
        sa.CheckConstraint("inning >= 1", name="ck_raw_pitch_events_inning_min"),
        sa.CheckConstraint("game_zone >= 1 AND game_zone <= 9", name="ck_raw_pitch_events_game_zone_range"),
        sa.ForeignKeyConstraint(["import_run_id"], ["data_import_runs.id"], name="fk_raw_pitch_events_import_run"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_pk", "at_bat_number", "pitch_number", name="uq_raw_pitch_events_unique_pitch"),
    )
    op.create_index(op.f("ix_raw_pitch_events_import_run_id"), "raw_pitch_events", ["import_run_id"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_game_pk"), "raw_pitch_events", ["game_pk"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_game_date"), "raw_pitch_events", ["game_date"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_season"), "raw_pitch_events", ["season"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_batter_mlb_id"), "raw_pitch_events", ["batter_mlb_id"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_pitcher_mlb_id"), "raw_pitch_events", ["pitcher_mlb_id"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_stand"), "raw_pitch_events", ["stand"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_p_throws"), "raw_pitch_events", ["p_throws"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_pitch_type"), "raw_pitch_events", ["pitch_type"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_pitch_family"), "raw_pitch_events", ["pitch_family"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_statcast_zone"), "raw_pitch_events", ["statcast_zone"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_game_zone"), "raw_pitch_events", ["game_zone"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_description"), "raw_pitch_events", ["description"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_event"), "raw_pitch_events", ["event"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_home_team"), "raw_pitch_events", ["home_team"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_away_team"), "raw_pitch_events", ["away_team"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_raw_payload_hash"), "raw_pitch_events", ["raw_payload_hash"], unique=False)
    op.create_index(op.f("ix_raw_pitch_events_source"), "raw_pitch_events", ["source"], unique=False)


def downgrade() -> None:
    op.drop_table("raw_pitch_events")