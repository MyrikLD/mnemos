"""drop_client_hostname

Revision ID: 3bf8f4d8e272
Revises: 688fbe55788c
Create Date: 2026-03-15 17:31:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3bf8f4d8e272"
down_revision: Union[str, Sequence[str], None] = "688fbe55788c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop client_hostname column from memories."""
    with op.batch_alter_table("memories") as batch_op:
        batch_op.drop_column("client_hostname")


def downgrade() -> None:
    """Restore client_hostname column."""
    with op.batch_alter_table("memories") as batch_op:
        batch_op.add_column(sa.Column("client_hostname", sa.String(255), nullable=True))
