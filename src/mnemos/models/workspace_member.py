import sqlalchemy as sa

from .base import Base


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role = sa.Column(
        sa.String(50), nullable=False, server_default="member"
    )  # "owner" | "member"
    joined_at = sa.Column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False
    )
