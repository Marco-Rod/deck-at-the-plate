"""CardEdition declara la policy de elegibilidad de publicación.

NULL conserva el comportamiento legacy. No hay backfill global: una edición
moderna debe declarar la versión explícitamente antes de materializar perfiles.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0039"
down_revision: Union[str, None] = "0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "card_editions",
        sa.Column("eligibility_policy_version", sa.String(length=40), nullable=True),
    )
    op.create_index(
        "ix_card_editions_eligibility_policy_version",
        "card_editions",
        ["eligibility_policy_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_card_editions_eligibility_policy_version",
        table_name="card_editions",
    )
    op.drop_column("card_editions", "eligibility_policy_version")
