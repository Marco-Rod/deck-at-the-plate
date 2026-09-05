"""modelos analytics: perfiles baseline, zona/familia, splits y H2H

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-05

Fases 4-5 del doc: perfiles derivados + head-to-head. El Matchup Engine V1
consume estas tablas (nunca raw_pitch_events). Todos los UNIQUE compuestos del
apéndice §14.1 están aplicados.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _throwhand():
    return pg.ENUM("L", "R", name="throwhand", create_type=False)


def _sorthand():
    return pg.ENUM("ALL", "L", "R", name="sorthand", create_type=False)


def _pitchfamily():
    return pg.ENUM("FASTBALL", "BREAKING", "OFFSPEED", "OTHER", name="pitchfamily", create_type=False)


def _pitchfamilysplit():
    return pg.ENUM("ALL", "FASTBALL", "BREAKING", "OFFSPEED", name="pitchfamilysplit", create_type=False)


def upgrade() -> None:
    # --- Baseline ---
    op.create_table(
        "batter_season_stats",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("pa", sa.Integer(), nullable=False),
        sa.Column("ab", sa.Integer(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("singles", sa.Integer(), nullable=False),
        sa.Column("doubles", sa.Integer(), nullable=False),
        sa.Column("triples", sa.Integer(), nullable=False),
        sa.Column("home_runs", sa.Integer(), nullable=False),
        sa.Column("walks", sa.Integer(), nullable=False),
        sa.Column("strikeouts", sa.Integer(), nullable=False),
        sa.Column("pitches_seen", sa.Integer(), nullable=False),
        sa.Column("swings", sa.Integer(), nullable=False),
        sa.Column("whiffs", sa.Integer(), nullable=False),
        sa.Column("balls_in_play", sa.Integer(), nullable=False),
        sa.Column("avg", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("obp", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("slg", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("ops", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("woba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("avg_exit_velocity", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("avg_launch_angle", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("hard_hit_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("barrel_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("swing_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("whiff_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("contact_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("chase_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("zone_swing_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("zone_contact_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("pa >= 0 AND ab >= 0", name="ck_batter_season_stats_pa_ab"),
        sa.CheckConstraint("hits >= 0", name="ck_batter_season_stats_hits"),
        sa.CheckConstraint("hard_hit_rate >= 0 AND hard_hit_rate <= 1", name="ck_batter_season_stats_hhr"),
        sa.CheckConstraint("barrel_rate >= 0 AND barrel_rate <= 1", name="ck_batter_season_stats_barrel"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_batter_season_stats_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", name="uq_batter_season_stats_player_season"),
    )
    op.create_index(op.f("ix_batter_season_stats_player_season_id"), "batter_season_stats", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_batter_season_stats_woba"), "batter_season_stats", ["woba"], unique=False)
    op.create_index(op.f("ix_batter_season_stats_xwoba"), "batter_season_stats", ["xwoba"], unique=False)

    op.create_table(
        "pitcher_season_stats",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("games", sa.Integer(), nullable=False),
        sa.Column("starts", sa.Integer(), nullable=False),
        sa.Column("batters_faced", sa.Integer(), nullable=False),
        sa.Column("pitches", sa.Integer(), nullable=False),
        sa.Column("outs_recorded", sa.Integer(), nullable=False),
        sa.Column("hits_allowed", sa.Integer(), nullable=False),
        sa.Column("home_runs_allowed", sa.Integer(), nullable=False),
        sa.Column("walks", sa.Integer(), nullable=False),
        sa.Column("strikeouts", sa.Integer(), nullable=False),
        sa.Column("era", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("whip", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("woba_allowed", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba_allowed", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("avg_velocity", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("whiff_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("chase_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("called_strike_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("hard_hit_rate_allowed", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("barrel_rate_allowed", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("hard_hit_rate_allowed >= 0 AND hard_hit_rate_allowed <= 1", name="ck_pitcher_season_stats_hhr"),
        sa.CheckConstraint("barrel_rate_allowed >= 0 AND barrel_rate_allowed <= 1", name="ck_pitcher_season_stats_barrel"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_pitcher_season_stats_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", name="uq_pitcher_season_stats_player_season"),
    )
    op.create_index(op.f("ix_pitcher_season_stats_player_season_id"), "pitcher_season_stats", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_pitcher_season_stats_woba_allowed"), "pitcher_season_stats", ["woba_allowed"], unique=False)
    op.create_index(op.f("ix_pitcher_season_stats_xwoba_allowed"), "pitcher_season_stats", ["xwoba_allowed"], unique=False)

    # --- Perfil por zona ---
    op.create_table(
        "batter_zone_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("zone", sa.SmallInteger(), nullable=False),
        sa.Column("pitcher_hand", _sorthand(), nullable=False),
        sa.Column("pitch_family", _pitchfamilysplit(), nullable=False),
        sa.Column("pitches_seen", sa.Integer(), nullable=False),
        sa.Column("swings", sa.Integer(), nullable=False),
        sa.Column("takes", sa.Integer(), nullable=False),
        sa.Column("whiffs", sa.Integer(), nullable=False),
        sa.Column("contacts", sa.Integer(), nullable=False),
        sa.Column("balls_in_play", sa.Integer(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("home_runs", sa.Integer(), nullable=False),
        sa.Column("avg", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("slg", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("woba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("contact_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("whiff_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("hard_hit_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("barrel_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("zone >= 1 AND zone <= 9", name="ck_batter_zone_profiles_zone_range"),
        sa.CheckConstraint("sample_size >= 0", name="ck_batter_zone_profiles_sample_size"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_batter_zone_profiles_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", "zone", "pitcher_hand", "pitch_family", name="uq_batter_zone_profiles_dimensions"),
    )
    op.create_index(op.f("ix_batter_zone_profiles_player_season_id"), "batter_zone_profiles", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_batter_zone_profiles_zone"), "batter_zone_profiles", ["zone"], unique=False)
    op.create_index(op.f("ix_batter_zone_profiles_pitcher_hand"), "batter_zone_profiles", ["pitcher_hand"], unique=False)
    op.create_index(op.f("ix_batter_zone_profiles_pitch_family"), "batter_zone_profiles", ["pitch_family"], unique=False)

    op.create_table(
        "pitcher_zone_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("zone", sa.SmallInteger(), nullable=False),
        sa.Column("batter_side", _sorthand(), nullable=False),
        sa.Column("pitch_family", _pitchfamilysplit(), nullable=False),
        sa.Column("pitches", sa.Integer(), nullable=False),
        sa.Column("swings", sa.Integer(), nullable=False),
        sa.Column("takes", sa.Integer(), nullable=False),
        sa.Column("whiffs", sa.Integer(), nullable=False),
        sa.Column("called_strikes", sa.Integer(), nullable=False),
        sa.Column("balls_in_play", sa.Integer(), nullable=False),
        sa.Column("hits_allowed", sa.Integer(), nullable=False),
        sa.Column("home_runs_allowed", sa.Integer(), nullable=False),
        sa.Column("woba_allowed", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba_allowed", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("whiff_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("called_strike_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("hard_hit_rate_allowed", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("barrel_rate_allowed", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("zone >= 1 AND zone <= 9", name="ck_pitcher_zone_profiles_zone_range"),
        sa.CheckConstraint("sample_size >= 0", name="ck_pitcher_zone_profiles_sample_size"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_pitcher_zone_profiles_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", "zone", "batter_side", "pitch_family", name="uq_pitcher_zone_profiles_dimensions"),
    )
    op.create_index(op.f("ix_pitcher_zone_profiles_player_season_id"), "pitcher_zone_profiles", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_pitcher_zone_profiles_zone"), "pitcher_zone_profiles", ["zone"], unique=False)
    op.create_index(op.f("ix_pitcher_zone_profiles_batter_side"), "pitcher_zone_profiles", ["batter_side"], unique=False)
    op.create_index(op.f("ix_pitcher_zone_profiles_pitch_family"), "pitcher_zone_profiles", ["pitch_family"], unique=False)

    # --- Perfil por familia ---
    op.create_table(
        "batter_pitch_family_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("pitch_family", _pitchfamily(), nullable=False),
        sa.Column("pitcher_hand", _sorthand(), nullable=False),
        sa.Column("pitches_seen", sa.Integer(), nullable=False),
        sa.Column("swings", sa.Integer(), nullable=False),
        sa.Column("whiffs", sa.Integer(), nullable=False),
        sa.Column("balls_in_play", sa.Integer(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("home_runs", sa.Integer(), nullable=False),
        sa.Column("woba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("contact_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("whiff_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("hard_hit_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("barrel_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sample_size >= 0", name="ck_batter_pitch_family_profiles_sample_size"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_batter_pitch_family_profiles_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", "pitch_family", "pitcher_hand", name="uq_batter_pitch_family_profiles_dimensions"),
    )
    op.create_index(op.f("ix_batter_pitch_family_profiles_player_season_id"), "batter_pitch_family_profiles", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_batter_pitch_family_profiles_pitch_family"), "batter_pitch_family_profiles", ["pitch_family"], unique=False)
    op.create_index(op.f("ix_batter_pitch_family_profiles_pitcher_hand"), "batter_pitch_family_profiles", ["pitcher_hand"], unique=False)

    # --- Arsenal ---
    op.create_table(
        "pitcher_pitch_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("pitch_type", sa.String(length=12), nullable=False),
        sa.Column("pitch_family", _pitchfamily(), nullable=False),
        sa.Column("batter_side", _sorthand(), nullable=False),
        sa.Column("pitch_count", sa.Integer(), nullable=False),
        sa.Column("usage_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("avg_velocity", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("max_velocity", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("avg_spin_rate", sa.Numeric(precision=7, scale=2), nullable=True),
        sa.Column("avg_horizontal_break", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("avg_vertical_break", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("avg_extension", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("swings", sa.Integer(), nullable=False),
        sa.Column("whiffs", sa.Integer(), nullable=False),
        sa.Column("called_strikes", sa.Integer(), nullable=False),
        sa.Column("balls_in_play", sa.Integer(), nullable=False),
        sa.Column("whiff_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("chase_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("called_strike_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("woba_allowed", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba_allowed", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("hard_hit_rate_allowed", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("barrel_rate_allowed", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("pitch_count >= 0", name="ck_pitcher_pitch_profiles_pitch_count"),
        sa.CheckConstraint("usage_rate >= 0 AND usage_rate <= 1", name="ck_pitcher_pitch_profiles_usage"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_pitcher_pitch_profiles_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", "pitch_type", "batter_side", name="uq_pitcher_pitch_profiles_dimensions"),
    )
    op.create_index(op.f("ix_pitcher_pitch_profiles_player_season_id"), "pitcher_pitch_profiles", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_pitcher_pitch_profiles_pitch_type"), "pitcher_pitch_profiles", ["pitch_type"], unique=False)
    op.create_index(op.f("ix_pitcher_pitch_profiles_pitch_family"), "pitcher_pitch_profiles", ["pitch_family"], unique=False)
    op.create_index(op.f("ix_pitcher_pitch_profiles_batter_side"), "pitcher_pitch_profiles", ["batter_side"], unique=False)

    # --- Splits por handedness ---
    op.create_table(
        "batter_handedness_splits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("pitcher_hand", _throwhand(), nullable=False),
        sa.Column("pa", sa.Integer(), nullable=False),
        sa.Column("pitches_seen", sa.Integer(), nullable=False),
        sa.Column("swings", sa.Integer(), nullable=False),
        sa.Column("whiffs", sa.Integer(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("home_runs", sa.Integer(), nullable=False),
        sa.Column("walks", sa.Integer(), nullable=False),
        sa.Column("strikeouts", sa.Integer(), nullable=False),
        sa.Column("avg", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("slg", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("woba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("contact_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("whiff_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("hard_hit_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("hard_hit_rate >= 0 AND hard_hit_rate <= 1", name="ck_batter_handedness_splits_hhr"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_batter_handedness_splits_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", "pitcher_hand", name="uq_batter_handedness_splits_hand"),
    )
    op.create_index(op.f("ix_batter_handedness_splits_player_season_id"), "batter_handedness_splits", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_batter_handedness_splits_pitcher_hand"), "batter_handedness_splits", ["pitcher_hand"], unique=False)

    op.create_table(
        "pitcher_handedness_splits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("batter_side", _throwhand(), nullable=False),
        sa.Column("batters_faced", sa.Integer(), nullable=False),
        sa.Column("pitches", sa.Integer(), nullable=False),
        sa.Column("swings", sa.Integer(), nullable=False),
        sa.Column("whiffs", sa.Integer(), nullable=False),
        sa.Column("hits_allowed", sa.Integer(), nullable=False),
        sa.Column("home_runs_allowed", sa.Integer(), nullable=False),
        sa.Column("walks", sa.Integer(), nullable=False),
        sa.Column("strikeouts", sa.Integer(), nullable=False),
        sa.Column("woba_allowed", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba_allowed", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("whiff_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("hard_hit_rate_allowed", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("whiff_rate >= 0 AND whiff_rate <= 1", name="ck_pitcher_handedness_splits_whiff"),
        sa.CheckConstraint("hard_hit_rate_allowed >= 0 AND hard_hit_rate_allowed <= 1", name="ck_pitcher_handedness_splits_hhr"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_pitcher_handedness_splits_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", "batter_side", name="uq_pitcher_handedness_splits_side"),
    )
    op.create_index(op.f("ix_pitcher_handedness_splits_player_season_id"), "pitcher_handedness_splits", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_pitcher_handedness_splits_batter_side"), "pitcher_handedness_splits", ["batter_side"], unique=False)

    # --- Head-to-Head ---
    op.create_table(
        "batter_pitcher_matchups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batter_id", sa.String(length=36), nullable=False),
        sa.Column("pitcher_id", sa.String(length=36), nullable=False),
        sa.Column("season_start", sa.SmallInteger(), nullable=False),
        sa.Column("season_end", sa.SmallInteger(), nullable=False),
        sa.Column("data_end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("plate_appearances", sa.Integer(), nullable=False),
        sa.Column("at_bats", sa.Integer(), nullable=False),
        sa.Column("pitches", sa.Integer(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("singles", sa.Integer(), nullable=False),
        sa.Column("doubles", sa.Integer(), nullable=False),
        sa.Column("triples", sa.Integer(), nullable=False),
        sa.Column("home_runs", sa.Integer(), nullable=False),
        sa.Column("walks", sa.Integer(), nullable=False),
        sa.Column("strikeouts", sa.Integer(), nullable=False),
        sa.Column("swings", sa.Integer(), nullable=False),
        sa.Column("whiffs", sa.Integer(), nullable=False),
        sa.Column("avg", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("slg", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("woba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("xwoba", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("hard_hit_rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("hard_hit_rate >= 0 AND hard_hit_rate <= 1", name="ck_batter_pitcher_matchups_hhr"),
        sa.ForeignKeyConstraint(["batter_id"], ["players.id"], name="fk_batter_pitcher_matchups_batter"),
        sa.ForeignKeyConstraint(["pitcher_id"], ["players.id"], name="fk_batter_pitcher_matchups_pitcher"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batter_id", "pitcher_id", "season_start", "season_end", "data_end_date", name="uq_batter_pitcher_matchups_window"),
    )
    op.create_index(op.f("ix_batter_pitcher_matchups_batter_id"), "batter_pitcher_matchups", ["batter_id"], unique=False)
    op.create_index(op.f("ix_batter_pitcher_matchups_pitcher_id"), "batter_pitcher_matchups", ["pitcher_id"], unique=False)
    op.create_index(op.f("ix_batter_pitcher_matchups_season_start"), "batter_pitcher_matchups", ["season_start"], unique=False)
    op.create_index(op.f("ix_batter_pitcher_matchups_season_end"), "batter_pitcher_matchups", ["season_end"], unique=False)
    op.create_index(op.f("ix_batter_pitcher_matchups_data_end_date"), "batter_pitcher_matchups", ["data_end_date"], unique=False)


def downgrade() -> None:
    for table in (
        "batter_pitcher_matchups",
        "pitcher_handedness_splits",
        "batter_handedness_splits",
        "pitcher_pitch_profiles",
        "batter_pitch_family_profiles",
        "pitcher_zone_profiles",
        "batter_zone_profiles",
        "pitcher_season_stats",
        "batter_season_stats",
    ):
        op.drop_table(table)