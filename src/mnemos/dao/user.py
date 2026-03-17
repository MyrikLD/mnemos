import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.models.user import User
from mnemos.models.workspace import Workspace
from mnemos.models.workspace_invite import WorkspaceInvite
from mnemos.models.workspace_member import WorkspaceMember


class UserDao:
    def __init__(self, s: AsyncSession) -> None:
        self._s = s

    async def create_user_with_workspace(
        self, username: str, password: str
    ) -> tuple[int, int]:
        """Create user + personal workspace + owner membership.

        Returns (user_id, workspace_id). Raises ValueError if username taken.
        """
        existing = await self._s.scalar(
            sa.select(User.id).where(User.username == username)
        )
        if existing is not None:
            raise ValueError(f"Username '{username}' is already taken")

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        user_id: int = await self._s.scalar(  # type: ignore[assignment]
            sa.insert(User)
            .values(username=username, password_hash=password_hash)
            .returning(User.id)
        )

        workspace_id: int = await self._s.scalar(  # type: ignore[assignment]
            sa.insert(Workspace)
            .values(name=f"{username}'s workspace", owner_id=user_id)
            .returning(Workspace.id)
        )

        await self._s.execute(
            sa.insert(WorkspaceMember).values(
                workspace_id=workspace_id, user_id=user_id, role="owner"
            )
        )

        return user_id, workspace_id

    async def authenticate(
        self, username: str, password: str
    ) -> tuple[int, int] | None:
        """Verify credentials. Returns (user_id, workspace_id) or None."""
        row = (
            await self._s.execute(
                sa.select(User.id, User.password_hash).where(User.username == username)
            )
        ).one_or_none()

        if row is None:
            return None

        user_id, password_hash = row
        if not bcrypt.checkpw(password.encode(), password_hash.encode()):
            return None

        workspace_id = await self._s.scalar(
            sa.select(WorkspaceMember.workspace_id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.joined_at)
            .limit(1)
        )
        if workspace_id is None:
            return None

        return user_id, workspace_id

    async def create_invite(
        self, workspace_id: int, created_by: int, ttl_hours: int = 72
    ) -> str:
        """Create an invite token for a workspace. Returns the token."""
        token = secrets.token_hex(32)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            hours=ttl_hours
        )
        await self._s.execute(
            sa.insert(WorkspaceInvite).values(
                token=token,
                workspace_id=workspace_id,
                created_by=created_by,
                expires_at=expires_at,
            )
        )
        return token

    async def use_invite(self, token: str, user_id: int) -> int | None:
        """Use an invite token. Returns workspace_id on success, None if invalid/used/expired."""
        invite = (
            await self._s.execute(
                sa.select(
                    WorkspaceInvite.workspace_id,
                    WorkspaceInvite.expires_at,
                    WorkspaceInvite.used_at,
                ).where(WorkspaceInvite.token == token)
            )
        ).one_or_none()

        if invite is None:
            return None

        workspace_id, expires_at, used_at = invite
        if used_at is not None:
            return None
        if expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            return None

        # Check if user is already a member
        existing = await self._s.scalar(
            sa.select(WorkspaceMember.workspace_id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if existing is None:
            await self._s.execute(
                sa.insert(WorkspaceMember).values(
                    workspace_id=workspace_id, user_id=user_id, role="member"
                )
            )

        await self._s.execute(
            sa.update(WorkspaceInvite)
            .where(WorkspaceInvite.token == token)
            .values(
                used_at=datetime.now(timezone.utc).replace(tzinfo=None), used_by=user_id
            )
        )

        return workspace_id

    async def get_workspace_members(self, workspace_id: int) -> list[dict]:
        rows = (
            (
                await self._s.execute(
                    sa.select(
                        User.id,
                        User.username,
                        WorkspaceMember.role,
                        WorkspaceMember.joined_at,
                    )
                    .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
                    .where(WorkspaceMember.workspace_id == workspace_id)
                    .order_by(WorkspaceMember.joined_at)
                )
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    async def get_workspace_invites(self, workspace_id: int) -> list[dict]:
        """Return only unexpired, unused invites."""
        rows = (
            (
                await self._s.execute(
                    sa.select(
                        WorkspaceInvite.token,
                        WorkspaceInvite.expires_at,
                        WorkspaceInvite.created_by,
                    ).where(
                        WorkspaceInvite.workspace_id == workspace_id,
                        WorkspaceInvite.used_at.is_(None),
                        WorkspaceInvite.expires_at > datetime.utcnow(),
                    )
                )
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    async def get_workspace_name(self, workspace_id: int) -> str | None:
        return await self._s.scalar(
            sa.select(Workspace.name).where(Workspace.id == workspace_id)
        )

    async def is_workspace_owner(self, workspace_id: int, user_id: int) -> bool:
        role = await self._s.scalar(
            sa.select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return role == "owner"

    async def get_username(self, user_id: int) -> str | None:
        return await self._s.scalar(sa.select(User.username).where(User.id == user_id))

    async def get_user_workspaces(self, user_id: int) -> list[dict]:
        """Return all workspaces the user belongs to (owned + joined), ordered by join date."""
        rows = (
            (
                await self._s.execute(
                    sa.select(
                        Workspace.id,
                        Workspace.name,
                        WorkspaceMember.role,
                        WorkspaceMember.joined_at,
                    )
                    .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
                    .where(WorkspaceMember.user_id == user_id)
                    .order_by(WorkspaceMember.joined_at)
                )
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    async def leave_workspace(self, user_id: int, workspace_id: int) -> None:
        """Remove user from a workspace. Raises ValueError if owner or not a member."""
        role = await self._s.scalar(
            sa.select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if role is None:
            raise ValueError("Not a member of this workspace")
        if role == "owner":
            raise ValueError("Workspace owners cannot leave their own workspace")
        await self._s.execute(
            sa.delete(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
