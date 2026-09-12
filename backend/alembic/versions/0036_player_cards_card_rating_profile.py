"""Vínculo aditivo PlayerCard -> CardRatingProfile.

La publicación puede consumir CardRatingProfile como fuente autoritativa de
atributos; generation_profile_id permanece para el enlace legacy y la
procedencia de Analytics. Nullable: ratings-1.0 y cortes sin rating profile
continúan publicando desde CardGenerationProfile.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0036"
down_revision: Union[str, None] = "0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "player_cards",
        sa.Column("card_rating_profile_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_player_cards_card_rating_profile_id",
        "player_cards",
        ["card_rating_profile_id"],
    )
    op.create_foreign_key(
        "fk_player_cards_card_rating_profile",
        "player_cards",
        "card_rating_profiles",
        ["card_rating_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_player_cards_card_rating_profile", "player_cards", type_="foreignkey"
    )
    op.drop_index(
        "ix_player_cards_card_rating_profile_id", table_name="player_cards"
    )
    op.drop_column("player_cards", "card_rating_profile_id")