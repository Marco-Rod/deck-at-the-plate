"""CardEdition declara la política de ratings que sus perfiles deben usar.

Cierra el contrato Edition -> Rating Policy: la publicación resuelve
CardRatingProfile filtrando por rating_policy_version de la edición, de modo
que versiones de política coexistentes (base-card-ratings-1.0, 1.1, ...) no
generan ambigüedad. Nullable para ediciones legacy sin política implementada;
backfill idempotente para BASE/MOMENT (las únicas con política definida).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0037"
down_revision: Union[str, None] = "0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "card_editions",
        sa.Column("rating_policy_version", sa.String(length=40), nullable=True),
    )
    op.create_index(
        "ix_card_editions_rating_policy_version",
        "card_editions",
        ["rating_policy_version"],
    )
    op.execute(
        "UPDATE card_editions SET rating_policy_version = "
        "'base-card-ratings-1.0' WHERE edition_type = 'BASE'"
    )
    op.execute(
        "UPDATE card_editions SET rating_policy_version = "
        "'moment-card-ratings-1.0' WHERE edition_type = 'MOMENT'"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_card_editions_rating_policy_version", table_name="card_editions"
    )
    op.drop_column("card_editions", "rating_policy_version")