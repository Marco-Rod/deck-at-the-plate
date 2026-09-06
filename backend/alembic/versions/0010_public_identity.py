"""capas de identidad publica y re-key de teams a UUID (plan V2)

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-05

Aplica el plan Deck_at_the_Plate_ETL_Card_Catalog_Public_Identity_Plan_V2
(fase "capas de identidad + catalog"):

    - Capa SOURCE: source_teams + source_team_game_team_mappings.
    - Capa GAME: re-key de teams a UUID deterministico
      (uuid5(public_abbreviation)), + abbreviation/slug/logo_asset/is_active.
    - player_cards.team_id y users.favorite_team_id re-apuntados al UUID.
    - player_team_stints pasa a referenciar source_teams (Migration 4 V2).
    - Snapshots de roster re-escritos a la forma source_team_* (V2 §12);
      se descarta team_roster_* (0009, tablas vacias).
    - game_player_identities + card_catalogs + player_cards.game_identity_id
      y player_cards.catalog_id.
    - user_teams.base_franchise -> base_team_id (FK teams.id, nunca SOURCE).

La clasificacion legacy de player_cards es la migracion 0011.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.identities import game_team_id_for


# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _current_team_abbrs(bind) -> list[str]:
    rows = bind.execute(sa.text("SELECT id FROM teams ORDER BY id")).fetchall()
    return [r[0] for r in rows]


def upgrade() -> None:
    bind = op.get_bind()

    # ---------- Snapshots de roster 0009: se reemplaza por la forma V2 ----------
    op.drop_table("team_roster_members")
    op.drop_table("team_roster_snapshots")

    # ---------- Capa SOURCE: source_teams (vive antes que teams legacy) ----------
    op.create_table(
        "source_teams",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="MLB"),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("source_abbreviation", sa.String(length=5), nullable=False),
        sa.Column("league", sa.String(length=10), nullable=False, server_default="MLB"),
        sa.Column("division", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_source_teams_source_external"),
    )
    op.create_index("ix_source_teams_source_abbreviation", "source_teams", ["source_abbreviation"], unique=False)
    op.create_index("ix_source_teams_is_active", "source_teams", ["is_active"], unique=False)

    # ---------- tables de identidad y catalogo ----------
    op.create_table(
        "game_player_identities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("display_first_name", sa.String(length=60), nullable=False),
        sa.Column("display_last_name", sa.String(length=60), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("default_jersey_number", sa.String(length=5), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name="fk_game_player_identities_player", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    # unique=True en el modelo -> índice único en DB (no constraint aparte).
    op.create_index("ix_game_player_identities_player_id", "game_player_identities", ["player_id"], unique=True)
    op.create_index("ix_game_player_identities_display_name", "game_player_identities", ["display_name"], unique=False)

    op.create_table(
        "card_catalogs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("edition_type", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="BUILDING"),
        sa.Column("rating_model_version", sa.String(length=30), nullable=True),
        sa.Column("data_end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season", "edition_type", "version", name="uq_card_catalogs_season_type_version"),
    )
    op.create_index("ix_card_catalogs_season", "card_catalogs", ["season"], unique=False)
    op.create_index("ix_card_catalogs_edition_type", "card_catalogs", ["edition_type"], unique=False)
    op.create_index("ix_card_catalogs_status", "card_catalogs", ["status"], unique=False)
    op.create_index("ix_card_catalogs_published_at", "card_catalogs", ["published_at"], unique=False)
    op.create_index("ix_card_catalogs_rating_model_version", "card_catalogs", ["rating_model_version"], unique=False)
    # Un solo ACTIVE por (season, edition_type)
    op.create_index(
        "uq_card_catalogs_active_per_season_type",
        "card_catalogs",
        ["season", "edition_type"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    # ---------- Re-key de teams: varchar(3) abreviatura -> UUID determinístico ----------
    abbrs = _current_team_abbrs(bind)
    abbr_to_uuid = {abbr: game_team_id_for(abbr) for abbr in abbrs}
    if not abbr_to_uuid:
        raise RuntimeError(
            "teams esta vacio; el re-key espera la semilla previa de 30 franquicias."
        )

    # FKs entrantes que apuntan a teams.id se re-crean al final.
    op.drop_constraint("player_cards_team_id_fkey", "player_cards", type_="foreignkey")
    op.drop_constraint("users_favorite_team_id_fkey", "users", type_="foreignkey")
    op.drop_constraint("fk_player_team_stints_team", "player_team_stints", type_="foreignkey")

    # Se ensanchan antes de escribir UUIDs (varchar(3) -> varchar(36)).
    op.alter_column("player_cards", "team_id", existing_type=sa.String(3), type_=sa.String(36))
    op.alter_column("users", "favorite_team_id", existing_type=sa.String(3), type_=sa.String(36))

    # Los índices de la tabla vieja no se renombran con el rename; se sueltan
    # para no chocar con los de la nueva tabla `teams`.
    op.drop_index("ix_teams_id", table_name="teams")
    op.drop_index("ix_teams_is_cpu", table_name="teams")

    # La tabla vieja (ids = abreviatura) se conserva solo para la copia.
    op.rename_table("teams", "teams_legacy")

    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("abbreviation", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=True),
        sa.Column("logo_asset", sa.String(length=120), nullable=True),
        sa.Column("primary_color", sa.String(length=7), nullable=False, server_default="#121619"),
        sa.Column("secondary_color", sa.String(length=7), nullable=False, server_default="#C5A059"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_cpu", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_abbreviation", "teams", ["abbreviation"], unique=False)
    op.create_index("ix_teams_slug", "teams", ["slug"], unique=False)
    op.create_index("ix_teams_is_active", "teams", ["is_active"], unique=False)
    op.create_index("ix_teams_is_cpu", "teams", ["is_cpu"], unique=False)

    # Copia 1:1 de las franquicias existentes al nuevo PK UUID (sin tocar branding).
    legacy_rows = bind.execute(
        sa.text(
            "SELECT id, name, city, primary_color, secondary_color, is_cpu "
            "FROM teams_legacy ORDER BY id"
        )
    ).fetchall()
    for row in legacy_rows:
        abbr, name, city, primary_color, secondary_color, is_cpu = row
        new_id = abbr_to_uuid[abbr]
        bind.execute(
            sa.text(
                "INSERT INTO teams (id, abbreviation, name, city, slug, logo_asset, "
                "primary_color, secondary_color, is_cpu, is_active) "
                "VALUES (:id, :abbr, :name, :city, :slug, NULL, :pc, :sc, :cpu, true)"
            ).bindparams(
                id=new_id, abbr=abbr, name=name, city=city,
                slug=abbr.lower(), pc=primary_color or "#121619", sc=secondary_color or "#C5A059",
                cpu=bool(is_cpu),
            )
        )

    # Re-apunta FKs de cartas y usuarios al nuevo UUID.
    for abbr, new_id in abbr_to_uuid.items():
        bind.execute(
            sa.text("UPDATE player_cards SET team_id = :new WHERE team_id = :old").bindparams(new=new_id, old=abbr)
        )
        bind.execute(
            sa.text("UPDATE users SET favorite_team_id = :new WHERE favorite_team_id = :old").bindparams(new=new_id, old=abbr)
        )

    op.drop_table("teams_legacy")

    # Restaura FKs de player_cards y users contra el nuevo teams.
    op.create_foreign_key("fk_player_cards_team", "player_cards", "teams", ["team_id"], ["id"])
    op.create_foreign_key("fk_users_favorite_team", "users", "teams", ["favorite_team_id"], ["id"])

    # ---------- player_cards: identidad publica + catalogo (V2, Migration 8) ----------
    op.add_column("player_cards", sa.Column("game_identity_id", sa.String(length=36), nullable=True))
    op.add_column("player_cards", sa.Column("catalog_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_player_cards_game_identity", "player_cards", "game_player_identities",
        ["game_identity_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_player_cards_catalog", "player_cards", "card_catalogs",
        ["catalog_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_player_cards_game_identity_id", "player_cards", ["game_identity_id"], unique=False)
    op.create_index("ix_player_cards_catalog_id", "player_cards", ["catalog_id"], unique=False)

    # ---------- player_team_stints -> SourceTeam (Migration 4 V2) ----------
    # La tabla esta vacia en la transicion; se reemplaza la columna.
    op.drop_constraint("uq_player_team_stint", "player_team_stints", type_="unique")
    op.drop_column("player_team_stints", "team_id")
    op.add_column("player_team_stints", sa.Column("source_team_id", sa.String(length=36), nullable=False))
    op.create_foreign_key(
        "fk_player_team_stints_source_team", "player_team_stints", "source_teams",
        ["source_team_id"], ["id"],
    )
    op.create_index("ix_player_team_stints_source_team_id", "player_team_stints", ["source_team_id"], unique=False)
    op.create_unique_constraint(
        "uq_player_team_stint",
        "player_team_stints",
        ["player_id", "season", "source_team_id", "start_date"],
    )

    # ---------- Mapping SOURCE <-> GAME ----------
    op.create_table(
        "source_team_game_team_mappings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_team_id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=36), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_team_id"], ["source_teams.id"], name="fk_source_game_mapping_source_team", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name="fk_source_game_mapping_team", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_team_id", "team_id", name="uq_source_team_game_team_mappings_pair"),
    )
    op.create_index("ix_source_team_game_team_mappings_source_team_id", "source_team_game_team_mappings", ["source_team_id"], unique=False)
    op.create_index("ix_source_team_game_team_mappings_team_id", "source_team_game_team_mappings", ["team_id"], unique=False)
    # Una sola mapping activa (valid_to IS NULL) por source_team.
    op.create_index(
        "uq_source_team_game_team_mappings_active",
        "source_team_game_team_mappings",
        ["source_team_id"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
    )

    # ---------- Snapshots de roster re-escritos (forma V2) ----------
    op.create_table(
        "source_team_roster_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_team_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("roster_type", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="MLB_STATS_API"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("season >= 1900 AND season <= 2100", name="ck_source_roster_snapshots_season_range"),
        sa.ForeignKeyConstraint(["source_team_id"], ["source_teams.id"], name="fk_source_roster_snapshots_team"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_team_id", "season", "as_of_date", "roster_type", name="uq_source_roster_snapshots_team_date_type"),
    )
    op.create_index("ix_source_team_roster_snapshots_source_team_id", "source_team_roster_snapshots", ["source_team_id"], unique=False)
    op.create_index("ix_source_team_roster_snapshots_season", "source_team_roster_snapshots", ["season"], unique=False)
    op.create_index("ix_source_team_roster_snapshots_as_of_date", "source_team_roster_snapshots", ["as_of_date"], unique=False)
    op.create_index("ix_source_team_roster_snapshots_roster_type", "source_team_roster_snapshots", ["roster_type"], unique=False)

    op.create_table(
        "source_team_roster_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("roster_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("position", sa.String(length=5), nullable=True),
        sa.Column("jersey_number", sa.String(length=5), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["roster_snapshot_id"], ["source_team_roster_snapshots.id"],
            name="fk_source_roster_members_snapshot", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name="fk_source_roster_members_player", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roster_snapshot_id", "player_id", name="uq_source_roster_members_snapshot_player"),
    )
    op.create_index("ix_source_team_roster_members_roster_snapshot_id", "source_team_roster_members", ["roster_snapshot_id"], unique=False)
    op.create_index("ix_source_team_roster_members_player_id", "source_team_roster_members", ["player_id"], unique=False)

    # ---------- user_teams: base_franchise (codigo SOURCE) -> base_team_id (GAME) ----------
    op.add_column("user_teams", sa.Column("base_team_id", sa.String(length=36), nullable=True))

    base_rows = bind.execute(
        sa.text("SELECT id, base_franchise FROM user_teams WHERE base_franchise IS NOT NULL")
    ).fetchall()
    for row in base_rows:
        row_id, base_franchise = row
        new_team_id = abbr_to_uuid.get(base_franchise.upper())
        if new_team_id is None:
            continue
        bind.execute(
            sa.text("UPDATE user_teams SET base_team_id = :new WHERE id = :id").bindparams(new=new_team_id, id=row_id)
        )
    op.drop_column("user_teams", "base_franchise")
    op.create_foreign_key("fk_user_teams_base_team", "user_teams", "teams", ["base_team_id"], ["id"])
    op.create_index("ix_user_teams_base_team_id", "user_teams", ["base_team_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_teams_base_team_id", table_name="user_teams")
    op.drop_constraint("fk_user_teams_base_team", "user_teams", type_="foreignkey")
    op.add_column("user_teams", sa.Column("base_franchise", sa.String(length=10), nullable=False, server_default="LAD"))
    op.drop_column("user_teams", "base_team_id")

    op.drop_table("source_team_roster_members")
    op.drop_table("source_team_roster_snapshots")
    op.drop_index("uq_source_team_game_team_mappings_active", table_name="source_team_game_team_mappings")
    op.drop_index("ix_source_team_game_team_mappings_team_id", table_name="source_team_game_team_mappings")
    op.drop_index("ix_source_team_game_team_mappings_source_team_id", table_name="source_team_game_team_mappings")
    op.drop_table("source_team_game_team_mappings")

    op.drop_constraint("uq_player_team_stint", "player_team_stints", type_="unique")
    op.drop_index("ix_player_team_stints_source_team_id", table_name="player_team_stints")
    op.drop_constraint("fk_player_team_stints_source_team", "player_team_stints", type_="foreignkey")
    op.drop_column("player_team_stints", "source_team_id")
    op.add_column("player_team_stints", sa.Column("team_id", sa.String(length=3), nullable=False))
    op.create_unique_constraint(
        "uq_player_team_stint", "player_team_stints",
        ["player_id", "season", "team_id", "start_date"],
    )

    op.drop_index("ix_player_cards_catalog_id", table_name="player_cards")
    op.drop_index("ix_player_cards_game_identity_id", table_name="player_cards")
    op.drop_constraint("fk_player_cards_catalog", "player_cards", type_="foreignkey")
    op.drop_constraint("fk_player_cards_game_identity", "player_cards", type_="foreignkey")
    op.drop_column("player_cards", "catalog_id")
    op.drop_column("player_cards", "game_identity_id")

    op.drop_constraint("fk_users_favorite_team", "users", type_="foreignkey")
    op.drop_constraint("fk_player_cards_team", "player_cards", type_="foreignkey")

    # Rebuild teams legacy desde el UUID actual.
    bind = op.get_bind()
    op.rename_table("teams", "teams_game")
    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("primary_color", sa.String(length=7), nullable=True),
        sa.Column("secondary_color", sa.String(length=7), nullable=True),
        sa.Column("is_cpu", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_id"), "teams", ["id"], unique=False)
    op.create_index(op.f("ix_teams_is_cpu"), "teams", ["is_cpu"], unique=False)
    game_rows = bind.execute(
        sa.text("SELECT id, abbreviation, name, city, primary_color, secondary_color, is_cpu FROM teams_game ORDER BY id")
    ).fetchall()
    for row in game_rows:
        bind.execute(
            sa.text(
                "INSERT INTO teams (id, name, city, primary_color, secondary_color, is_cpu) "
                "VALUES (:abbr, :name, :city, :pc, :sc, :cpu)"
            ).bindparams(
                abbr=row[1], name=row[2], city=row[3],
                pc=row[4], sc=row[5], cpu=bool(row[6]),
            )
        )
    # Restaura FK-relink (data original no recuperable).
    bind.execute(sa.text("UPDATE player_cards SET team_id = NULL WHERE team_id IS NOT NULL"))
    bind.execute(sa.text("UPDATE users SET favorite_team_id = NULL WHERE favorite_team_id IS NOT NULL"))
    op.drop_table("teams_game")

    op.alter_column("player_cards", "team_id", existing_type=sa.String(36), type_=sa.String(3))
    op.alter_column("users", "favorite_team_id", existing_type=sa.String(36), type_=sa.String(3))
    op.create_foreign_key("player_cards_team_id_fkey", "player_cards", "teams", ["team_id"], ["id"])
    op.create_foreign_key("users_favorite_team_id_fkey", "users", "teams", ["favorite_team_id"], ["id"])
    op.create_foreign_key("fk_player_team_stints_team", "player_team_stints", "teams", ["team_id"], ["id"])

    op.drop_index("uq_card_catalogs_active_per_season_type", table_name="card_catalogs")
    op.drop_index("ix_card_catalogs_rating_model_version", table_name="card_catalogs")
    op.drop_index("ix_card_catalogs_published_at", table_name="card_catalogs")
    op.drop_index("ix_card_catalogs_status", table_name="card_catalogs")
    op.drop_index("ix_card_catalogs_edition_type", table_name="card_catalogs")
    op.drop_index("ix_card_catalogs_season", table_name="card_catalogs")
    op.drop_table("card_catalogs")
    op.drop_index("ix_game_player_identities_display_name", table_name="game_player_identities")
    op.drop_index("ix_game_player_identities_player_id", table_name="game_player_identities")
    op.drop_table("game_player_identities")
    op.drop_index("ix_source_teams_is_active", table_name="source_teams")
    op.drop_index("ix_source_teams_source_abbreviation", table_name="source_teams")
    op.drop_table("source_teams")

    op.create_table(
        "team_roster_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=3), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("roster_type", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="MLB_STATS_API"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("season >= 1900 AND season <= 2100", name="ck_team_roster_snapshots_season_range"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name="fk_team_roster_snapshots_team"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "season", "as_of_date", "roster_type", name="uq_team_roster_snapshots_team_date_type"),
    )
    op.create_index(op.f("ix_team_roster_snapshots_roster_type"), "team_roster_snapshots", ["roster_type"], unique=False)
    op.create_index(op.f("ix_team_roster_snapshots_as_of_date"), "team_roster_snapshots", ["as_of_date"], unique=False)
    op.create_index(op.f("ix_team_roster_snapshots_season"), "team_roster_snapshots", ["season"], unique=False)
    op.create_index(op.f("ix_team_roster_snapshots_team_id"), "team_roster_snapshots", ["team_id"], unique=False)
    op.create_table(
        "team_roster_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("roster_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("position", sa.String(length=5), nullable=True),
        sa.Column("jersey_number", sa.String(length=5), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["roster_snapshot_id"], ["team_roster_snapshots.id"],
            name="fk_team_roster_members_snapshot", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name="fk_team_roster_members_player", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roster_snapshot_id", "player_id", name="uq_team_roster_members_snapshot_player"),
    )
    op.create_index(op.f("ix_team_roster_members_player_id"), "team_roster_members", ["player_id"], unique=False)
    op.create_index(op.f("ix_team_roster_members_roster_snapshot_id"), "team_roster_members", ["roster_snapshot_id"], unique=False)