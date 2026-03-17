import sqlalchemy as sa

from .base import Base


class WorkspaceInvite(Base):
    __tablename__ = "workspace_invites"

    token = sa.Column(sa.String(64), primary_key=True)  # secrets.token_hex(32)
    workspace_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    expires_at = sa.Column(sa.DateTime(timezone=False), nullable=False)
    used_at = sa.Column(sa.DateTime(timezone=False), nullable=True)
    used_by = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=True)

    __table_args__ = (sa.Index("ix_workspace_invites_workspace_id", "workspace_id"),)
