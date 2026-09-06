"""clasificacion legacy de cartas del seed (plan V2 §25)

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-05

Las cartas generadas por el seed (player_id IS NULL, sin Player real) se
marcan LEGACY: edition_type='LEGACY' y is_pack_eligible=false. Siguen
visibles en inventarios/lineups pero no entran al pack pool ni a starters;
el catalogo publicado (publish-card-catalog) generara las ediciones BASE
reales sobre Players.

No toca cartas con player_id (futuro vertical slice / catalogo).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE player_cards "
        "SET edition_type = 'LEGACY', is_pack_eligible = false "
        "WHERE player_id IS NULL AND edition_type = 'BASE'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE player_cards "
        "SET edition_type = 'BASE', is_pack_eligible = true "
        "WHERE player_id IS NULL AND edition_type = 'LEGACY'"
    )