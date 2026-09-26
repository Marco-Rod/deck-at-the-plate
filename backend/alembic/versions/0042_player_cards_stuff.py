"""Stuff del pitcher en player_cards (GAMEPLAY-ENGINE-003B-6A).

`stuff` es la única columna que falta para que la semántica de Stuff (contact-
quality suppression, k=.30 / α=.50) pueda existir en la ruta PRODUCTIVA. Hasta
003B-6 el atributo vivía solo en el harness LAB.

Decisiones de la migración:

*   `server_default="70"` = STUFF_BASELINE. Un pitcher sin Stuff publicado queda
    EXACTAMENTE neutro (delta = 0, supresión 0) en vez de sesgar hacia abajo.
    Es la misma philosophy que el fallback del mapper: transición neutral.
*   NOT NULL desde el alta. `stuff` es obligatorio para el motor: un NULL
    obligaría a ramificar la fórmula y reintroduce el estado indeterminado que
    003B-2/003B-5A ya descartaron.
*   CHECK 0-99, igual que vision/clutch (rango de carta, no de league).
*   No hace backfill de datos: el reparto de valores reales desde ratings-2.0
    (`player_ratings.stuff_rating` → `card_rating_profiles.stuff_rating`) es un
    paso de datos aparte, idempotente, en `app/seeds/backfill_cards.py`. La
    migración sólo instala la columna y su restricción; ejecutar el backfill es
    una decisión operativa posterior (idempotente, se puede correr en cualquier
    momento sin riesgo de gameplay parcial).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0042"
down_revision: Union[str, None] = "0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "player_cards",
        sa.Column("stuff", sa.Integer(), nullable=False, server_default="70"),
    )
    op.create_check_constraint(
        "ck_player_cards_stuff_range", "player_cards", "stuff >= 0 AND stuff <= 99"
    )


def downgrade() -> None:
    op.drop_constraint("ck_player_cards_stuff_range", "player_cards", type_="check")
    op.drop_column("player_cards", "stuff")
