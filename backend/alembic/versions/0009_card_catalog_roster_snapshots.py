"""catalogo de cartas versionado y snapshots de roster (plan Card Catalog V1)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-05

Aplica el plan Deck_at_the_Plate_ETL_Card_Catalog_CPU_Rosters_Integration_Plan_V1:

    - Migration B: player_cards versiona ediciones.
        * `edition` → `edition_type` (mismo contenido, "BASE").
        * + `season` (SmallInteger), `edition_version` (Integer >= 1),
          `is_active`, `is_pack_eligible`, `published_at`.
        * UNIQUE (player_id, season, edition_type, edition_version).
        * Backfill: legacy → season=2026, published_at=now() (catalog vivo).
    - Migration C/D: tablas team_roster_snapshots y team_roster_members para
      el roster CPU (fuente de verdad = MLB roster, no Statcast participants).

La migración A (player_cards.player_id FK) ya existe (0006). La E (card_role)
queda pendiente: V1 mantiene is_two_way.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- Migration B: ediciones versionadas en player_cards ----------
    # Renombrar `edition` (legacy, sin consumidores en runtime) a `edition_type`.
    op.alter_column("player_cards", "edition", new_column_name="edition_type", existing_type=sa.String(50))
    op.drop_index("ix_player_cards_edition", table_name="player_cards")
    op.create_index("ix_player_cards_edition_type", "player_cards", ["edition_type"], unique=False)

    op.add_column("player_cards", sa.Column("season", sa.SmallInteger(), nullable=True))
    op.add_column("player_cards", sa.Column("edition_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("player_cards", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("player_cards", sa.Column("is_pack_eligible", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("player_cards", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))

    # Backfill para cartas existentes (legacy del seed 2026, catalog vivo).
    op.execute("UPDATE player_cards SET season = 2026 WHERE season IS NULL")
    op.execute("UPDATE player_cards SET published_at = now() WHERE published_at IS NULL")

    op.create_index(op.f("ix_player_cards_season"), "player_cards", ["season"], unique=False)
    op.create_index(op.f("ix_player_cards_is_active"), "player_cards", ["is_active"], unique=False)
    op.create_index(op.f("ix_player_cards_is_pack_eligible"), "player_cards", ["is_pack_eligible"], unique=False)
    op.create_index(op.f("ix_player_cards_published_at"), "player_cards", ["published_at"], unique=False)

    op.create_unique_constraint(
        "uq_player_cards_edition",
        "player_cards",
        ["player_id", "season", "edition_type", "edition_version"],
    )
    op.create_check_constraint(
        "ck_player_cards_season_range",
        "player_cards",
        "season IS NULL OR (season >= 1900 AND season <= 2100)",
    )
    op.create_check_constraint(
        "ck_player_cards_edition_version",
        "player_cards",
        "edition_version >= 1",
    )

    # ---------- Migration C: team_roster_snapshots ----------
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
    op.create_index(op.f("ix_team_roster_snapshots_team_id"), "team_roster_snapshots", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_roster_snapshots_season"), "team_roster_snapshots", ["season"], unique=False)
    op.create_index(op.f("ix_team_roster_snapshots_as_of_date"), "team_roster_snapshots", ["as_of_date"], unique=False)
    op.create_index(op.f("ix_team_roster_snapshots_roster_type"), "team_roster_snapshots", ["roster_type"], unique=False)

    # ---------- Migration D: team_roster_members ----------
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
    op.create_index(op.f("ix_team_roster_members_roster_snapshot_id"), "team_roster_members", ["roster_snapshot_id"], unique=False)
    op.create_index(op.f("ix_team_roster_members_player_id"), "team_roster_members", ["player_id"], unique=False)


def downgrade() -> None:
    # Migration D
    op.drop_index(op.f("ix_team_roster_members_player_id"), table_name="team_roster_members")
    op.drop_index(op.f("ix_team_roster_members_roster_snapshot_id"), table_name="team_roster_members")
    op.drop_table("team_roster_members")
    # Migration C
    op.drop_index(op.f("ix_team_roster_snapshots_roster_type"), table_name="team_roster_snapshots")
    op.drop_index(op.f("ix_team_roster_snapshots_as_of_date"), table_name="team_roster_snapshots")
    op.drop_index(op.f("ix_team_roster_snapshots_season"), table_name="team_roster_snapshots")
    op.drop_index(op.f("ix_team_roster_snapshots_team_id"), table_name="team_roster_snapshots")
    op.drop_table("team_roster_snapshots")

    # Migration B
    op.drop_constraint("ck_player_cards_edition_version", "player_cards", type_="check")
    op.drop_constraint("ck_player_cards_season_range", "player_cards", type_="check")
    op.drop_constraint("uq_player_cards_edition", "player_cards", type_="unique")
    op.drop_index(op.f("ix_player_cards_published_at"), table_name="player_cards")
    op.drop_index(op.f("ix_player_cards_is_pack_eligible"), table_name="player_cards")
    op.drop_index(op.f("ix_player_cards_is_active"), table_name="player_cards")
    op.drop_index(op.f("ix_player_cards_season"), table_name="player_cards")
    op.drop_column("player_cards", "published_at")
    op.drop_column("player_cards", "is_pack_eligible")
    op.drop_column("player_cards", "is_active")
    op.drop_column("player_cards", "edition_version")
    op.drop_column("player_cards", "season")
    op.drop_index("ix_player_cards_edition_type", table_name="player_cards")
    op.alter_column("player_cards", "edition_type", new_column_name="edition", existing_type=sa.String(50))
    op.create_index("ix_player_cards_edition", "player_cards", ["edition"], unique=False)