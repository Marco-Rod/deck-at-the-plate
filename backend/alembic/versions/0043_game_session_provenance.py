"""Provenance estructural de partida (GAMEPLAY-PROVENANCE-001).

Una partida deja de ser "metadata incidental" y pasa a ser parte de su
identidad histórica: con qué catálogo, qué modelo de ratings, qué reglas y
qué build se jugó.

Por qué columnas y no claves dentro de ``state_data``:

``state_data`` es JSON sin índices. Con provenance en columnas se pueden
hacer las consultas que este bloque existe para habilitar:

    games by engine version
    games by rules version
    games by catalog
    compare engine A vs engine B
    reproduce games from catalog v2

Decisiones de la migración:

*   Las cinco columnas son NULLABLE. No hay backfill: la tabla estaba vacía
    (0 sesiones) y, aun cuando no lo estuviera, no existe provenance
    retroactivo que inventar. Preferimos NULL explícito a un valor inventado
    que parecería verificable.
*   ``catalog_id`` con FK a ``card_catalogs.id`` ON DELETE RESTRICT, igual
    que ``player_cards.catalog_id``. Una partida no puede quedar apuntando a
    un catálogo borrado.
*   ``rating_model_version`` se persiste aunque sea derivable del catálogo.
    Es denormalización deliberada de provenance: permite responder la
    pregunta sin join y convierte la igualdad
    ``catalog.rating_model_version == game_session.rating_model_version``
    en un invariante verificable en vez de una reconstrucción.
*   Índices en ``catalog_id``, ``rating_model_version`` y ``engine_build``.
    Postgres no indexa las columnas FK automáticamente, así que ``catalog_id``
    se indexa explícito (igual que ``player_cards.catalog_id``).
*   ``engine_version`` (semántica, p. ej. ``engine-1.0``) y ``engine_build``
    (código desplegado, p. ej. ``engine-20261001-datap4``) son columnas
    distintas a propósito: responden a preguntas diferentes y P4 las separa
    ahora para no necesitar otra migración cuando exista una versión
    semántica real del motor.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0043"
down_revision: Union[str, None] = "0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_sessions",
        sa.Column("catalog_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("rating_model_version", sa.String(30), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("rules_version", sa.String(30), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("engine_version", sa.String(30), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("engine_build", sa.String(30), nullable=True),
    )

    op.create_foreign_key(
        "fk_game_sessions_catalog",
        "game_sessions",
        "card_catalogs",
        ["catalog_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_game_sessions_catalog_id",
        "game_sessions",
        ["catalog_id"],
    )
    op.create_index(
        "ix_game_sessions_rating_model_version",
        "game_sessions",
        ["rating_model_version"],
    )
    op.create_index(
        "ix_game_sessions_engine_build",
        "game_sessions",
        ["engine_build"],
    )


def downgrade() -> None:
    op.drop_index("ix_game_sessions_engine_build", table_name="game_sessions")
    op.drop_index(
        "ix_game_sessions_rating_model_version", table_name="game_sessions"
    )
    op.drop_index("ix_game_sessions_catalog_id", table_name="game_sessions")
    op.drop_constraint(
        "fk_game_sessions_catalog", "game_sessions", type_="foreignkey"
    )
    op.drop_column("game_sessions", "engine_build")
    op.drop_column("game_sessions", "engine_version")
    op.drop_column("game_sessions", "rules_version")
    op.drop_column("game_sessions", "rating_model_version")
    op.drop_column("game_sessions", "catalog_id")
