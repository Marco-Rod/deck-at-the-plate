"""modelos nucleo: enums compartidos, players, player_seasons, stints, data_import_runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-05

Creación aditiva de la capa CORE/ETL (ref. referencias/nuevos_modelos.docx):

    Fase 1. CORE      → players, player_seasons, player_team_stints
    Fase 2. ETL       → data_import_runs

Los tipos ENUM compartidos se crean UNA sola vez aquí para que las tablas de
migraciones posteriores los referencien con create_type=False (evita el error
"type <x> already exists" de PostgreSQL).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tipos ENUM "str" compartidos (valores estables en inglés, ver §13 del doc).
ENUM_SPECS = [
    ("handedness", ["L", "R", "S"]),
    ("throwhand", ["L", "R"]),
    ("sorthand", ["ALL", "L", "R"]),
    ("pitchfamily", ["FASTBALL", "BREAKING", "OFFSPEED", "OTHER"]),
    ("pitchfamilysplit", ["ALL", "FASTBALL", "BREAKING", "OFFSPEED"]),
    ("batterapproach", ["FASTBALL", "BREAKING", "REACT", "TAKE"]),
    ("importstatus", ["RUNNING", "SUCCESS", "PARTIAL", "FAILED"]),
]


def _create_enum_types() -> None:
    bind = op.get_bind()
    for name, values in ENUM_SPECS:
        pg.ENUM(*values, name=name).create(bind, checkfirst=True)


def _drop_enum_types() -> None:
    bind = op.get_bind()
    for name, _ in reversed(ENUM_SPECS):
        pg.ENUM(name=name).drop(bind, checkfirst=True)


def _handedness():
    return pg.ENUM("L", "R", "S", name="handedness", create_type=False)


def _throwhand():
    return pg.ENUM("L", "R", name="throwhand", create_type=False)


def _importstatus():
    return pg.ENUM("RUNNING", "SUCCESS", "PARTIAL", "FAILED", name="importstatus", create_type=False)


def upgrade() -> None:
    _create_enum_types()

    op.create_table(
        "data_import_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("pipeline_version", sa.String(length=30), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=True),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("status", _importstatus(), nullable=False),
        sa.Column("rows_extracted", sa.Integer(), nullable=False),
        sa.Column("rows_inserted", sa.Integer(), nullable=False),
        sa.Column("rows_updated", sa.Integer(), nullable=False),
        sa.Column("rows_rejected", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_import_runs_source"), "data_import_runs", ["source"], unique=False)
    op.create_index(op.f("ix_data_import_runs_pipeline_version"), "data_import_runs", ["pipeline_version"], unique=False)
    op.create_index(op.f("ix_data_import_runs_season"), "data_import_runs", ["season"], unique=False)
    op.create_index(op.f("ix_data_import_runs_status"), "data_import_runs", ["status"], unique=False)
    op.create_index(op.f("ix_data_import_runs_started_at"), "data_import_runs", ["started_at"], unique=False)

    op.create_table(
        "players",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mlb_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("first_name", sa.String(length=60), nullable=True),
        sa.Column("last_name", sa.String(length=60), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("primary_position", sa.String(length=5), nullable=True),
        sa.Column("bats", _handedness(), nullable=True),
        sa.Column("throws", _throwhand(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_players_mlb_id"), "players", ["mlb_id"], unique=True)
    op.create_index(op.f("ix_players_full_name"), "players", ["full_name"], unique=False)
    op.create_index(op.f("ix_players_last_name"), "players", ["last_name"], unique=False)
    op.create_index(op.f("ix_players_primary_position"), "players", ["primary_position"], unique=False)
    op.create_index(op.f("ix_players_bats"), "players", ["bats"], unique=False)
    op.create_index(op.f("ix_players_throws"), "players", ["throws"], unique=False)
    op.create_index(op.f("ix_players_is_active"), "players", ["is_active"], unique=False)

    op.create_table(
        "player_seasons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("data_start_date", sa.Date(), nullable=False),
        sa.Column("data_end_date", sa.Date(), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False),
        sa.Column("games", sa.Integer(), nullable=False),
        sa.Column("plate_appearances", sa.Integer(), nullable=False),
        sa.Column("batters_faced", sa.Integer(), nullable=False),
        sa.Column("outs_recorded", sa.Integer(), nullable=False),
        sa.Column("import_run_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("season >= 1900 AND season <= 2100", name="ck_player_seasons_season_range"),
        sa.CheckConstraint("data_end_date >= data_start_date", name="ck_player_seasons_date_window"),
        sa.CheckConstraint("games >= 0", name="ck_player_seasons_games_non_negative"),
        sa.CheckConstraint("plate_appearances >= 0", name="ck_player_seasons_pa_non_negative"),
        sa.CheckConstraint("batters_faced >= 0", name="ck_player_seasons_bf_non_negative"),
        sa.CheckConstraint("outs_recorded >= 0", name="ck_player_seasons_outs_non_negative"),
        sa.ForeignKeyConstraint(["import_run_id"], ["data_import_runs.id"], name="fk_player_seasons_import_run"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="RESTRICT", name="fk_player_seasons_player"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id", "season", "data_start_date", "data_end_date",
            name="uq_player_seasons_player_season_window",
        ),
    )
    op.create_index(op.f("ix_player_seasons_player_id"), "player_seasons", ["player_id"], unique=False)
    op.create_index(op.f("ix_player_seasons_season"), "player_seasons", ["season"], unique=False)
    op.create_index(op.f("ix_player_seasons_data_end_date"), "player_seasons", ["data_end_date"], unique=False)
    op.create_index(op.f("ix_player_seasons_is_complete"), "player_seasons", ["is_complete"], unique=False)

    op.create_table(
        "player_team_stints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("team_id", sa.String(length=3), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("games", sa.Integer(), nullable=False),
        sa.Column("is_primary_at_cutoff", sa.Boolean(), nullable=False),
        sa.CheckConstraint("games >= 0", name="ck_player_team_stints_games_non_negative"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="RESTRICT", name="fk_player_team_stints_player"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name="fk_player_team_stints_team"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_player_team_stints_player_id"), "player_team_stints", ["player_id"], unique=False)
    op.create_index(op.f("ix_player_team_stints_season"), "player_team_stints", ["season"], unique=False)
    op.create_index(op.f("ix_player_team_stints_team_id"), "player_team_stints", ["team_id"], unique=False)
    op.create_index(op.f("ix_player_team_stints_is_primary_at_cutoff"), "player_team_stints", ["is_primary_at_cutoff"], unique=False)


def downgrade() -> None:
    op.drop_table("player_team_stints")
    op.drop_table("player_seasons")
    op.drop_table("players")
    op.drop_table("data_import_runs")
    _drop_enum_types()