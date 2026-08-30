"""marcar equipos MLB como franquicias de la liga (is_cpu=True)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-30

Los 30 equipos MLB poblados por el seed representan las franquicias de la
liga (seleccionables como equipo favorito y usadas como rivales CPU). Por
ello deben quedar marcados con is_cpu=True.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Marcar TODOS los equipos MLB como franquicias de la liga.
    op.execute(
        sa.text("UPDATE teams SET is_cpu = TRUE WHERE is_cpu IS DISTINCT FROM TRUE")
    )


def downgrade() -> None:
    # Revertir: los equipos MLB vuelven a no ser franquicias de liga.
    op.execute(
        sa.text("UPDATE teams SET is_cpu = FALSE WHERE is_cpu = TRUE")
    )
