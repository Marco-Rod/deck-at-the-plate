"""mejoras previas a ETL: constraints, enum batter_side, sample_size y UTC

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-05

Aplica el doc referencias/cambiosprevisoaletl.md sobre los modelos ya creados
(0003-0007). Cambios NO destructivos sobre tabla existente y aplicables también
desde base limpia:

    - PlayerTeamStint: UNIQUE (player_id, season, team_id, start_date) y CHECK
      de ventana de fechas.
    - DataImportRun: contadores no negativos y ventana date_from <= date_to.
    - Nuevo enum batter_side_enum (L/R) para PitcherHandednessSplit.batter_side
      (lado efectivo observado), reemplazando throwhand.
    - BatterPitcherMatchup.data_end_date: DateTime → Date.
    - sample_size ligado por CHECK a su denominador en todos los analytics; se
      agrega la columna donde no existía (pitcher_pitch_profiles y los splits).
    - CHECKs de rango 0..1 sobre todas las columnas de tasa.

Los defaults de timestamp utcnow se aplican solo en Python (app/core/time.py),
no requieren migración.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _batter_side_enum():
    return pg.ENUM("L", "R", name="batter_side_enum", create_type=False)


def upgrade() -> None:
    # --- Nuevo enum BatterSide fundamenta PitcherHandednessSplit.batter_side ---
    bind = op.get_bind()
    pg.ENUM("L", "R", name="batter_side_enum").create(bind, checkfirst=True)

    # --- DataImportRun: contadores y ventana (etl.py) ---
    op.create_check_constraint(
        "ck_data_import_runs_rows_extracted",
        "data_import_runs",
        "rows_extracted >= 0",
    )
    op.create_check_constraint(
        "ck_data_import_runs_rows_inserted",
        "data_import_runs",
        "rows_inserted >= 0",
    )
    op.create_check_constraint(
        "ck_data_import_runs_rows_updated",
        "data_import_runs",
        "rows_updated >= 0",
    )
    op.create_check_constraint(
        "ck_data_import_runs_rows_rejected",
        "data_import_runs",
        "rows_rejected >= 0",
    )
    op.create_check_constraint(
        "ck_data_import_runs_date_range",
        "data_import_runs",
        "date_to IS NULL OR date_from IS NULL OR date_to >= date_from",
    )

    # --- PlayerTeamStint: UNIQUE + ventana (player.py) ---
    op.create_unique_constraint(
        "uq_player_team_stint",
        "player_team_stints",
        ["player_id", "season", "team_id", "start_date"],
    )
    op.create_check_constraint(
        "ck_player_team_stint_dates",
        "player_team_stints",
        "end_date IS NULL OR end_date >= start_date",
    )

    # --- PitcherHandednessSplit.batter_side: throwhand → batter_side_enum ---
    op.execute(
        "ALTER TABLE pitcher_handedness_splits "
        "ALTER COLUMN batter_side TYPE batter_side_enum "
        "USING batter_side::text::batter_side_enum"
    )
    # Añadir sample_size en los splits (= denominador respectivo).
    op.add_column(
        "batter_handedness_splits",
        sa.Column(
            "sample_size",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_batter_handedness_splits_sample_size",
        "batter_handedness_splits",
        "sample_size >= 0",
    )
    op.create_check_constraint(
        "ck_batter_handedness_splits_denom",
        "batter_handedness_splits",
        "sample_size = pa",
    )
    op.add_column(
        "pitcher_handedness_splits",
        sa.Column(
            "sample_size",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_pitcher_handedness_splits_sample_size",
        "pitcher_handedness_splits",
        "sample_size >= 0",
    )
    op.create_check_constraint(
        "ck_pitcher_handedness_splits_denom",
        "pitcher_handedness_splits",
        "sample_size = batters_faced",
    )
    op.create_check_constraint(
        "ck_pitcher_handedness_splits_whiff_rate",
        "pitcher_handedness_splits",
        "whiff_rate >= 0 AND whiff_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_handedness_splits_hhr_rate",
        "pitcher_handedness_splits",
        "hard_hit_rate_allowed >= 0 AND hard_hit_rate_allowed <= 1",
    )
    op.create_check_constraint(
        "ck_batter_handedness_splits_contact_rate",
        "batter_handedness_splits",
        "contact_rate >= 0 AND contact_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_handedness_splits_whiff_rate",
        "batter_handedness_splits",
        "whiff_rate >= 0 AND whiff_rate <= 1",
    )

    # --- BatterPitcherMatchup.data_end_date → Date + sample_size igual PA ---
    op.alter_column(
        "batter_pitcher_matchups",
        "data_end_date",
        type_=sa.Date(),
        postgresql_using="data_end_date::date",
    )
    op.create_check_constraint(
        "ck_batter_pitcher_matchups_sample_size",
        "batter_pitcher_matchups",
        "sample_size >= 0",
    )
    op.create_check_constraint(
        "ck_batter_pitcher_matchups_denom",
        "batter_pitcher_matchups",
        "sample_size = plate_appearances",
    )

    # --- PitcherPitchProfile: nueva columna sample_size = pitch_count ---
    op.add_column(
        "pitcher_pitch_profiles",
        sa.Column(
            "sample_size",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_sample_size",
        "pitcher_pitch_profiles",
        "sample_size >= 0",
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_denom",
        "pitcher_pitch_profiles",
        "sample_size = pitch_count",
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_whiff_rate",
        "pitcher_pitch_profiles",
        "whiff_rate >= 0 AND whiff_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_chase_rate",
        "pitcher_pitch_profiles",
        "chase_rate >= 0 AND chase_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_called_strike_rate",
        "pitcher_pitch_profiles",
        "called_strike_rate >= 0 AND called_strike_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_hhr_rate",
        "pitcher_pitch_profiles",
        "hard_hit_rate_allowed >= 0 AND hard_hit_rate_allowed <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_barrel_rate",
        "pitcher_pitch_profiles",
        "barrel_rate_allowed >= 0 AND barrel_rate_allowed <= 1",
    )

    # --- CHECKs de rango en zonas y familia ---
    op.create_check_constraint(
        "ck_batter_zone_profiles_denom",
        "batter_zone_profiles",
        "sample_size = pitches_seen",
    )
    op.create_check_constraint(
        "ck_batter_zone_profiles_contact_rate",
        "batter_zone_profiles",
        "contact_rate >= 0 AND contact_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_zone_profiles_whiff_rate",
        "batter_zone_profiles",
        "whiff_rate >= 0 AND whiff_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_zone_profiles_hhr_rate",
        "batter_zone_profiles",
        "hard_hit_rate >= 0 AND hard_hit_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_zone_profiles_barrel_rate",
        "batter_zone_profiles",
        "barrel_rate >= 0 AND barrel_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_zone_profiles_denom",
        "pitcher_zone_profiles",
        "sample_size = pitches",
    )
    op.create_check_constraint(
        "ck_pitcher_zone_profiles_whiff_rate",
        "pitcher_zone_profiles",
        "whiff_rate >= 0 AND whiff_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_zone_profiles_called_strike_rate",
        "pitcher_zone_profiles",
        "called_strike_rate >= 0 AND called_strike_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_zone_profiles_hhr_rate",
        "pitcher_zone_profiles",
        "hard_hit_rate_allowed >= 0 AND hard_hit_rate_allowed <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_zone_profiles_barrel_rate",
        "pitcher_zone_profiles",
        "barrel_rate_allowed >= 0 AND barrel_rate_allowed <= 1",
    )
    op.create_check_constraint(
        "ck_batter_pitch_family_profiles_denom",
        "batter_pitch_family_profiles",
        "sample_size = pitches_seen",
    )
    op.create_check_constraint(
        "ck_batter_pitch_family_profiles_contact_rate",
        "batter_pitch_family_profiles",
        "contact_rate >= 0 AND contact_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_pitch_family_profiles_whiff_rate",
        "batter_pitch_family_profiles",
        "whiff_rate >= 0 AND whiff_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_pitch_family_profiles_hhr_rate",
        "batter_pitch_family_profiles",
        "hard_hit_rate >= 0 AND hard_hit_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_pitch_family_profiles_barrel_rate",
        "batter_pitch_family_profiles",
        "barrel_rate >= 0 AND barrel_rate <= 1",
    )

    # --- CHECKs de rango en baselines ---
    op.create_check_constraint(
        "ck_batter_season_stats_swing_rate",
        "batter_season_stats",
        "swing_rate >= 0 AND swing_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_whiff_rate",
        "batter_season_stats",
        "whiff_rate >= 0 AND whiff_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_contact_rate",
        "batter_season_stats",
        "contact_rate >= 0 AND contact_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_chase_rate",
        "batter_season_stats",
        "chase_rate >= 0 AND chase_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_zone_swing_rate",
        "batter_season_stats",
        "zone_swing_rate >= 0 AND zone_swing_rate <= 1",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_zone_contact_rate",
        "batter_season_stats",
        "zone_contact_rate >= 0 AND zone_contact_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_season_stats_whiff_rate",
        "pitcher_season_stats",
        "whiff_rate >= 0 AND whiff_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_season_stats_chase_rate",
        "pitcher_season_stats",
        "chase_rate >= 0 AND chase_rate <= 1",
    )
    op.create_check_constraint(
        "ck_pitcher_season_stats_called_strike_rate",
        "pitcher_season_stats",
        "called_strike_rate >= 0 AND called_strike_rate <= 1",
    )


def downgrade() -> None:
    # Baselines
    for name in (
        "ck_batter_season_stats_swing_rate",
        "ck_batter_season_stats_whiff_rate",
        "ck_batter_season_stats_contact_rate",
        "ck_batter_season_stats_chase_rate",
        "ck_batter_season_stats_zone_swing_rate",
        "ck_batter_season_stats_zone_contact_rate",
    ):
        op.drop_constraint(name, table_name="batter_season_stats", type_="check")
    for name in (
        "ck_pitcher_season_stats_whiff_rate",
        "ck_pitcher_season_stats_chase_rate",
        "ck_pitcher_season_stats_called_strike_rate",
    ):
        op.drop_constraint(name, table_name="pitcher_season_stats", type_="check")

    # Zona y familia
    for table, names in {
        "batter_pitch_family_profiles": (
            "ck_batter_pitch_family_profiles_barrel_rate",
            "ck_batter_pitch_family_profiles_hhr_rate",
            "ck_batter_pitch_family_profiles_whiff_rate",
            "ck_batter_pitch_family_profiles_contact_rate",
            "ck_batter_pitch_family_profiles_denom",
        ),
        "pitcher_zone_profiles": (
            "ck_pitcher_zone_profiles_barrel_rate",
            "ck_pitcher_zone_profiles_hhr_rate",
            "ck_pitcher_zone_profiles_called_strike_rate",
            "ck_pitcher_zone_profiles_whiff_rate",
            "ck_pitcher_zone_profiles_denom",
        ),
        "batter_zone_profiles": (
            "ck_batter_zone_profiles_barrel_rate",
            "ck_batter_zone_profiles_hhr_rate",
            "ck_batter_zone_profiles_whiff_rate",
            "ck_batter_zone_profiles_contact_rate",
            "ck_batter_zone_profiles_denom",
        ),
    }.items():
        for name in names:
            op.drop_constraint(name, table_name=table, type_="check")

    # Arsenal
    for name in (
        "ck_pitcher_pitch_profiles_barrel_rate",
        "ck_pitcher_pitch_profiles_hhr_rate",
        "ck_pitcher_pitch_profiles_called_strike_rate",
        "ck_pitcher_pitch_profiles_chase_rate",
        "ck_pitcher_pitch_profiles_whiff_rate",
        "ck_pitcher_pitch_profiles_denom",
        "ck_pitcher_pitch_profiles_sample_size",
    ):
        op.drop_constraint(name, table_name="pitcher_pitch_profiles", type_="check")
    op.drop_column("pitcher_pitch_profiles", "sample_size")

    # H2H
    op.drop_constraint(
        "ck_batter_pitcher_matchups_denom",
        table_name="batter_pitcher_matchups",
        type_="check",
    )
    op.drop_constraint(
        "ck_batter_pitcher_matchups_sample_size",
        table_name="batter_pitcher_matchups",
        type_="check",
    )
    op.alter_column(
        "batter_pitcher_matchups",
        "data_end_date",
        type_=sa.DateTime(timezone=True),
        postgresql_using="data_end_date::timestamp",
    )

    # Splits
    for name in (
        "ck_batter_handedness_splits_whiff_rate",
        "ck_batter_handedness_splits_contact_rate",
        "ck_batter_handedness_splits_denom",
        "ck_batter_handedness_splits_sample_size",
    ):
        op.drop_constraint(name, table_name="batter_handedness_splits", type_="check")
    op.drop_column("batter_handedness_splits", "sample_size")
    for name in (
        "ck_pitcher_handedness_splits_hhr_rate",
        "ck_pitcher_handedness_splits_whiff_rate",
        "ck_pitcher_handedness_splits_denom",
        "ck_pitcher_handedness_splits_sample_size",
    ):
        op.drop_constraint(name, table_name="pitcher_handedness_splits", type_="check")

    # Restaurar batter_side de pitcher_handedness_splits a throwhand.
    op.execute(
        "ALTER TABLE pitcher_handedness_splits "
        "ALTER COLUMN batter_side TYPE throwhand USING batter_side::text::throwhand"
    )
    op.drop_column("pitcher_handedness_splits", "sample_size")

    # PlayerTeamStint
    op.drop_constraint("ck_player_team_stint_dates", table_name="player_team_stints", type_="check")
    op.drop_constraint("uq_player_team_stint", table_name="player_team_stints", type_="unique")

    # DataImportRun
    for name in (
        "ck_data_import_runs_date_range",
        "ck_data_import_runs_rows_rejected",
        "ck_data_import_runs_rows_updated",
        "ck_data_import_runs_rows_inserted",
        "ck_data_import_runs_rows_extracted",
    ):
        op.drop_constraint(name, table_name="data_import_runs", type_="check")

    # Enum batter_side_enum (debe soltarse tras reverter la columna).
    bind = op.get_bind()
    pg.ENUM(name="batter_side_enum").drop(bind, checkfirst=True)