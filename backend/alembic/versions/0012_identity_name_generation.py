"""identidad game v2_1: perfil linguistico + version del generador (plan V2.1)

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-05

GamePlayerIdentity gana:
- name_profile: perfil lingüístico (JAPANESE, KOREAN, SPANISH, ... UNKNOWN) del
  clasificador determinista (§64, §87). Nullable para no romper filas legadas.
- generator_version: versión del generador de nombres (names-1.0) (§70, §79).
- display_name pasa a ser único: el universo GAME no admite dos caras públicas
  idénticas (§75). La tabla está vacía en esta fase de desarrollo; si hubiera
  duplicados se resuelven regenerando la identidad antes de aplicar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("game_player_identities", sa.Column("name_profile", sa.String(length=30), nullable=True))
    op.add_column("game_player_identities", sa.Column("generator_version", sa.String(length=20), nullable=True))
    op.drop_index("ix_game_player_identities_display_name", table_name="game_player_identities")
    op.create_index("ix_game_player_identities_display_name", "game_player_identities", ["display_name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_game_player_identities_display_name", table_name="game_player_identities")
    op.create_index("ix_game_player_identities_display_name", "game_player_identities", ["display_name"], unique=False)
    op.drop_column("game_player_identities", "generator_version")
    op.drop_column("game_player_identities", "name_profile")