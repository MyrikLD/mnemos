import sqlalchemy as sa

from .base import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(255), nullable=False)
    owner_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = sa.Column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False
    )
