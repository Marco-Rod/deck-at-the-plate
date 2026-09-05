"""card generation y migraciones aditivas sobre tablas existentes

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-05

Fase 6 del doc:
    - card_generation_profiles (perfiles inmutables de ratings).
    - player_cards: + player_id / player_season_id / generation_profile_id /
      vision / clutch / edition / rating_model_version (aditivo, sin borrar
      columnas legacy ni cambiar la PK).
    - tactic_cards: + effect_schema_version (contrato JSON versionado).
    - game_event_logs: + plate_appearance_id / engine_version (telemetría).

NOT NULL con server_default para poblar la fila existente en ALTER.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cardrarity():
    return pg.ENUM("COMMON", "BRONZE", "SILVER", "GOLD", "DIAMOND", name="cardrarity", create_type=False)


def upgrade() -> None:
    # --- CardGenerationProfile ---
    op.create_table(
        "card_generation_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_season_id", sa.String(length=36), nullable=False),
        sa.Column("rating_model_version", sa.String(length=30), nullable=False),
        sa.Column("contact_rating", sa.SmallInteger(), nullable=False),
        sa.Column("power_rating", sa.SmallInteger(), nullable=False),
        sa.Column("vision_rating", sa.SmallInteger(), nullable=False),
        sa.Column("clutch_rating", sa.SmallInteger(), nullable=False),
        sa.Column("velocity_rating", sa.SmallInteger(), nullable=False),
        sa.Column("control_rating", sa.SmallInteger(), nullable=False),
        sa.Column("movement_rating", sa.SmallInteger(), nullable=False),
        sa.Column("overall_rating", sa.SmallInteger(), nullable=False),
        sa.Column("calculated_rarity", _cardrarity(), nullable=False),
        sa.Column("primary_batter_trait", sa.String(length=40), nullable=True),
        sa.Column("primary_pitcher_trait", sa.String(length=40), nullable=True),
        sa.Column("repertoire_payload", sa.JSON(), nullable=True),
        sa.Column("calculation_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("contact_rating >= 0 AND contact_rating <= 99", name="ck_card_generation_contact"),
        sa.CheckConstraint("power_rating >= 0 AND power_rating <= 99", name="ck_card_generation_power"),
        sa.CheckConstraint("vision_rating >= 0 AND vision_rating <= 99", name="ck_card_generation_vision"),
        sa.CheckConstraint("clutch_rating >= 0 AND clutch_rating <= 99", name="ck_card_generation_clutch"),
        sa.CheckConstraint("velocity_rating >= 0 AND velocity_rating <= 99", name="ck_card_generation_velocity"),
        sa.CheckConstraint("control_rating >= 0 AND control_rating <= 99", name="ck_card_generation_control"),
        sa.CheckConstraint("movement_rating >= 0 AND movement_rating <= 99", name="ck_card_generation_movement"),
        sa.CheckConstraint("overall_rating >= 0 AND overall_rating <= 99", name="ck_card_generation_overall"),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], name="fk_card_generation_profiles_season"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_season_id", "rating_model_version", name="uq_card_generation_profiles_season_version"),
    )
    op.create_index(op.f("ix_card_generation_profiles_player_season_id"), "card_generation_profiles", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_card_generation_profiles_rating_model_version"), "card_generation_profiles", ["rating_model_version"], unique=False)
    op.create_index(op.f("ix_card_generation_profiles_calculated_rarity"), "card_generation_profiles", ["calculated_rarity"], unique=False)
    op.create_index(op.f("ix_card_generation_profiles_primary_batter_trait"), "card_generation_profiles", ["primary_batter_trait"], unique=False)
    op.create_index(op.f("ix_card_generation_profiles_primary_pitcher_trait"), "card_generation_profiles", ["primary_pitcher_trait"], unique=False)
    op.create_index(op.f("ix_card_generation_profiles_created_at"), "card_generation_profiles", ["created_at"], unique=False)

    # --- TacticCard: contrato JSON versionado ---
    op.add_column(
        "tactic_cards",
        sa.Column("effect_schema_version", sa.Integer(), nullable=False, server_default="1"),
    )

    # --- PlayerCardModel: campos aditivos (no borrar name/number/position/team_id) ---
    op.add_column("player_cards", sa.Column("vision", sa.Integer(), nullable=False, server_default="50"))
    op.add_column("player_cards", sa.Column("clutch", sa.Integer(), nullable=False, server_default="50"))
    op.add_column("player_cards", sa.Column("player_id", sa.String(length=36), nullable=True))
    op.add_column("player_cards", sa.Column("player_season_id", sa.String(length=36), nullable=True))
    op.add_column("player_cards", sa.Column("generation_profile_id", sa.String(length=36), nullable=True))
    op.add_column("player_cards", sa.Column("edition", sa.String(length=50), nullable=False, server_default="BASE"))
    op.add_column("player_cards", sa.Column("rating_model_version", sa.String(length=30), nullable=True))

    op.create_check_constraint("ck_player_cards_vision_range", "player_cards", "vision >= 0 AND vision <= 99")
    op.create_check_constraint("ck_player_cards_clutch_range", "player_cards", "clutch >= 0 AND clutch <= 99")

    op.create_index(op.f("ix_player_cards_player_id"), "player_cards", ["player_id"], unique=False)
    op.create_index(op.f("ix_player_cards_player_season_id"), "player_cards", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_player_cards_generation_profile_id"), "player_cards", ["generation_profile_id"], unique=False)
    op.create_index(op.f("ix_player_cards_edition"), "player_cards", ["edition"], unique=False)
    op.create_index(op.f("ix_player_cards_rating_model_version"), "player_cards", ["rating_model_version"], unique=False)

    op.create_foreign_key("fk_player_cards_player", "player_cards", "players", ["player_id"], ["id"])
    op.create_foreign_key("fk_player_cards_player_season", "player_cards", "player_seasons", ["player_season_id"], ["id"])
    op.create_foreign_key("fk_player_cards_generation_profile", "player_cards", "card_generation_profiles", ["generation_profile_id"], ["id"])

    # --- GameEventLog: telemetría pitch-by-pitch (backward-compatible) ---
    op.add_column("game_event_logs", sa.Column("plate_appearance_id", sa.String(length=36), nullable=True))
    op.add_column("game_event_logs", sa.Column("engine_version", sa.String(length=30), nullable=True))
    op.create_index(op.f("ix_game_event_logs_plate_appearance_id"), "game_event_logs", ["plate_appearance_id"], unique=False)
    op.create_index(op.f("ix_game_event_logs_engine_version"), "game_event_logs", ["engine_version"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_game_event_logs_engine_version"), table_name="game_event_logs")
    op.drop_index(op.f("ix_game_event_logs_plate_appearance_id"), table_name="game_event_logs")
    op.drop_column("game_event_logs", "engine_version")
    op.drop_column("game_event_logs", "plate_appearance_id")

    op.drop_constraint("fk_player_cards_generation_profile", "player_cards", type_="foreignkey")
    op.drop_constraint("fk_player_cards_player_season", "player_cards", type_="foreignkey")
    op.drop_constraint("fk_player_cards_player", "player_cards", type_="foreignkey")

    op.drop_index(op.f("ix_player_cards_rating_model_version"), table_name="player_cards")
    op.drop_index(op.f("ix_player_cards_edition"), table_name="player_cards")
    op.drop_index(op.f("ix_player_cards_generation_profile_id"), table_name="player_cards")
    op.drop_index(op.f("ix_player_cards_player_season_id"), table_name="player_cards")
    op.drop_index(op.f("ix_player_cards_player_id"), table_name="player_cards")

    op.drop_constraint("ck_player_cards_clutch_range", "player_cards", type_="check")
    op.drop_constraint("ck_player_cards_vision_range", "player_cards", type_="check")

    op.drop_column("player_cards", "rating_model_version")
    op.drop_column("player_cards", "edition")
    op.drop_column("player_cards", "generation_profile_id")
    op.drop_column("player_cards", "player_season_id")
    op.drop_column("player_cards", "player_id")
    op.drop_column("player_cards", "clutch")
    op.drop_column("player_cards", "vision")

    op.drop_column("tactic_cards", "effect_schema_version")

    op.drop_index(op.f("ix_card_generation_profiles_created_at"), table_name="card_generation_profiles")
    op.drop_index(op.f("ix_card_generation_profiles_primary_pitcher_trait"), table_name="card_generation_profiles")
    op.drop_index(op.f("ix_card_generation_profiles_primary_batter_trait"), table_name="card_generation_profiles")
    op.drop_index(op.f("ix_card_generation_profiles_calculated_rarity"), table_name="card_generation_profiles")
    op.drop_index(op.f("ix_card_generation_profiles_rating_model_version"), table_name="card_generation_profiles")
    op.drop_index(op.f("ix_card_generation_profiles_player_season_id"), table_name="card_generation_profiles")
    op.drop_table("card_generation_profiles")