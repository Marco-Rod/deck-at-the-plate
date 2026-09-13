"""Lifecycle de catálogos: origen de edición + cadena de reversión.

card_edition_id      -> de qué CardEdition salió este catálogo (no-op por
                        edición, no por season+edition_type).
supersedes_catalog_id-> catálogo al que sustituyó al pasar a ACTIVE; es la
                        cadena reversible (retract devuelve ACTIVE al
                        predecesor). NULL = catálogo primigenio.

Backfill: los catálogos históricos apuntan a la edición de sus cartas.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0040"
down_revision: Union[str, None] = "0039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "card_catalogs",
        sa.Column("card_edition_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "card_catalogs",
        sa.Column("supersedes_catalog_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_card_catalogs_card_edition_id",
        "card_catalogs",
        ["card_edition_id"],
    )
    op.create_index(
        "ix_card_catalogs_supersedes_catalog_id",
        "card_catalogs",
        ["supersedes_catalog_id"],
    )
    op.create_foreign_key(
        "fk_card_catalogs_card_edition",
        "card_catalogs",
        "card_editions",
        ["card_edition_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_card_catalogs_supersedes",
        "card_catalogs",
        "card_catalogs",
        ["supersedes_catalog_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Backfill: el origen de los catálogos históricos es la edición de sus cartas.
    op.execute(
        """
        UPDATE card_catalogs cc
        SET card_edition_id = pc.card_edition_id
        FROM player_cards pc
        WHERE pc.catalog_id = cc.id
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_card_catalogs_supersedes", "card_catalogs", type_="foreignkey")
    op.drop_constraint("fk_card_catalogs_card_edition", "card_catalogs", type_="foreignkey")
    op.drop_index("ix_card_catalogs_supersedes_catalog_id", table_name="card_catalogs")
    op.drop_index("ix_card_catalogs_card_edition_id", table_name="card_catalogs")
    op.drop_column("card_catalogs", "supersedes_catalog_id")
    op.drop_column("card_catalogs", "card_edition_id")