"""CardEdition declara la política de rareza coleccionable (nullable).

NULL conserva la ruta legacy (CardGenerationProfile.calculated_rarity);
declarada, la publicación DEBE resolver una rareza o falla el catálogo, sin
COMMON silencioso. Análogo al contrato Edition -> Rating Policy de 0037.
Sin backfill: en esta fase ninguna edición existente declara la política.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0038"
down_revision: Union[str, None] = "0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "card_editions",
        sa.Column("rarity_policy_version", sa.String(length=40), nullable=True),
    )
    op.create_index(
        "ix_card_editions_rarity_policy_version",
        "card_editions",
        ["rarity_policy_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_card_editions_rarity_policy_version", table_name="card_editions"
    )
    op.drop_column("card_editions", "rarity_policy_version")