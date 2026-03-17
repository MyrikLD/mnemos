"""Multi-user workspace support

Revision ID: a1b2c3d4e5f6
Revises: 2a6c4515f145
Create Date: 2026-03-17 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "2a6c4515f145"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create new tables
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "workspace_members",
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role", sa.String(50), nullable=False, server_default="member"
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "workspace_invites",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "used_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
    )
    op.create_index(
        "ix_workspace_invites_workspace_id", "workspace_invites", ["workspace_id"]
    )

    # 2. Add new columns to existing tables
    op.add_column(
        "memories",
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_memories_workspace_id", "memories", ["workspace_id"])

    op.add_column(
        "oauth_clients",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # 3. Insert _legacy user, workspace, and owner membership
    op.execute(
        sa.text(
            """
            INSERT INTO users (username, password_hash)
            VALUES ('_legacy', '$2b$12$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO workspaces (name, owner_id)
            SELECT '_legacy', id FROM users WHERE username = '_legacy'
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO workspace_members (workspace_id, user_id, role)
            SELECT w.id, u.id, 'owner'
            FROM workspaces w
            JOIN users u ON w.owner_id = u.id
            WHERE w.name = '_legacy'
            """
        )
    )

    # 4. Assign all existing memories to _legacy workspace
    op.execute(
        sa.text(
            """
            UPDATE memories
            SET workspace_id = (SELECT id FROM workspaces WHERE name = '_legacy')
            WHERE workspace_id IS NULL
            """
        )
    )

    # 5. Make workspace_id NOT NULL
    op.alter_column("memories", "workspace_id", nullable=False)


def downgrade() -> None:
    op.alter_column("memories", "workspace_id", nullable=True)
    op.drop_index("ix_memories_workspace_id", table_name="memories")
    op.drop_column("memories", "workspace_id")
    op.drop_column("oauth_clients", "user_id")
    op.drop_index("ix_workspace_invites_workspace_id", table_name="workspace_invites")
    op.drop_table("workspace_invites")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("users")
