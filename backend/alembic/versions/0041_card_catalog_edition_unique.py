"""Un catálogo máximo por CardEdition materializada."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0041"
down_revision: Union[str, None] = "0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_card_catalogs_card_edition_id", table_name="card_catalogs")
    op.create_index(
        "uq_card_catalogs_card_edition_id",
        "card_catalogs",
        ["card_edition_id"],
        unique=True,
        postgresql_where=sa.text("card_edition_id IS NOT NULL"),
        sqlite_where=sa.text("card_edition_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_card_catalogs_card_edition_id", table_name="card_catalogs")
    op.create_index(
        "ix_card_catalogs_card_edition_id",
        "card_catalogs",
        ["card_edition_id"],
        unique=False,
    )
