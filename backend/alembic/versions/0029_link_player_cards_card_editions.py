"""Vincula cada PlayerCard con una CardEdition explícita.

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "player_cards",
        sa.Column("card_edition_id", sa.String(length=36), nullable=True),
    )

    # Las migraciones previas ya usaban 2026 para legacy; se normalizan filas
    # que hayan sido insertadas después con season NULL antes del backfill.
    op.execute("UPDATE player_cards SET season = 2026 WHERE season IS NULL")
    op.execute("""
        INSERT INTO card_editions (
            id, code, name, edition_type, season, version, is_active,
            source_type, source_reference, starts_at, ends_at, metadata,
            created_at, updated_at
        )
        SELECT DISTINCT
            substr(md5('card-edition:' || season::text || ':' || edition_type || ':' || edition_version::text), 1, 8)
                || '-' || substr(md5('card-edition:' || season::text || ':' || edition_type || ':' || edition_version::text), 9, 4)
                || '-' || substr(md5('card-edition:' || season::text || ':' || edition_type || ':' || edition_version::text), 13, 4)
                || '-' || substr(md5('card-edition:' || season::text || ':' || edition_type || ':' || edition_version::text), 17, 4)
                || '-' || substr(md5('card-edition:' || season::text || ':' || edition_type || ':' || edition_version::text), 21, 12),
            season::text || '_' || edition_type,
            season::text || ' ' || replace(initcap(lower(edition_type)), '_', ' '),
            (CASE
                WHEN edition_type IN (
                    'BASE', 'TEAM_STAR', 'HOT_STREAK', 'MOMENT',
                    'ALL_STAR', 'MILESTONE', 'AWARD', 'POSTSEASON'
                ) THEN edition_type
                ELSE 'BASE'
            END)::cardeditiontype,
            season,
            'edition-' || edition_version::text || '.0',
            true,
            'SYSTEM'::cardeditionsourcetype,
            'migration:0029:' || edition_type,
            NULL::timestamptz,
            NULL::timestamptz,
            jsonb_build_object(
                'backfilled', true,
                'legacy_edition_type', edition_type,
                'legacy_edition_version', edition_version
            ),
            now(),
            now()
        FROM player_cards
        ON CONFLICT (season, code, version) DO NOTHING
    """)
    op.execute("""
        UPDATE player_cards AS card
        SET card_edition_id = edition.id
        FROM card_editions AS edition
        WHERE edition.season = card.season
          AND edition.code = card.season::text || '_' || card.edition_type
          AND edition.version = 'edition-' || card.edition_version::text || '.0'
    """)
    op.alter_column(
        "player_cards",
        "card_edition_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.create_index(
        "ix_player_cards_card_edition_id",
        "player_cards",
        ["card_edition_id"],
    )
    op.create_foreign_key(
        "fk_player_cards_card_edition",
        "player_cards",
        "card_editions",
        ["card_edition_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("uq_player_cards_edition", "player_cards", type_="unique")
    op.create_unique_constraint(
        "uq_player_cards_player_edition",
        "player_cards",
        ["player_id", "card_edition_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_player_cards_player_edition", "player_cards", type_="unique"
    )
    op.create_unique_constraint(
        "uq_player_cards_edition",
        "player_cards",
        ["player_id", "season", "edition_type", "edition_version"],
    )
    op.drop_constraint(
        "fk_player_cards_card_edition", "player_cards", type_="foreignkey"
    )
    op.drop_index("ix_player_cards_card_edition_id", table_name="player_cards")
    op.drop_column("player_cards", "card_edition_id")
