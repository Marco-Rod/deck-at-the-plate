"""sequence_no estructural en game_event_logs (RUNTIME TELEMETRY P5-A).

Cada jugada de la partida recibe un número de secuencia monótono. Sin él, el
único orden disponible es ``created_at`` (reloj del servidor) o el ``id``
(UUID), ninguno de los cuales garantiza el orden causal de las jugadas.

Decisiones de la migración:

*   ``sequence_no`` NULLABLE y SIN backfill: los eventos legados no tienen un
    orden reconstructible fiable; inventar uno parecería verificable. NULL
    explícito es la afirmación honesta de "no sé la posición".
*   Índice único ``(game_id, sequence_no)``: (un juego, una jugada) ⇒ un solo
    sequence_no. Protege a nivel de BD el invariante del runtime; la otra pata
    del orden (``plate_appearance_id`` + ``pitch_number``) vive en
    ``pitch_event_logs`` y ya tiene su propio unique (0007).
*   Se usa constraint único en lugar de índice único para que el catálogo de
    ``metadata`` de SQLAlchemy coincida con el modelo ``GameEventLog``
    (``__table_args__``) y las autoconsistencias de autogenerate no marquen
    diff en el futuro.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0044"
down_revision: Union[str, None] = "0043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_event_logs",
        sa.Column("sequence_no", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_game_event_logs_game_sequence_no",
        "game_event_logs",
        ["game_id", "sequence_no"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_game_event_logs_game_sequence_no", "game_event_logs", type_="unique"
    )
    op.drop_column("game_event_logs", "sequence_no")