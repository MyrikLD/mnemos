from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.auth import UserDep
from mnemos.dao.workspace import WorkspaceDao
from mnemos.db import MCPSessionDep
from mnemos.schemas import WorkspaceInfo

mcp = FastMCP()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def create_workspace(
    name: str,
    s: AsyncSession = MCPSessionDep,  # type: ignore[assignment]
    uid: int = UserDep,  # type: ignore[assignment]
) -> WorkspaceInfo:
    """Create a new workspace and become its owner."""
    return await WorkspaceDao(s).create(name=name, owner_id=uid)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
async def list_workspaces(
    s: AsyncSession = MCPSessionDep,  # type: ignore[assignment]
    uid: int = UserDep,  # type: ignore[assignment]
) -> list[WorkspaceInfo]:
    """List all workspaces you are a member of."""
    return await WorkspaceDao(s).list_workspaces(user_id=uid)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def create_invite(
    workspace_id: int,
    expires_in_hours: int = 72,
    s: AsyncSession = MCPSessionDep,  # type: ignore[assignment]
    uid: int = UserDep,  # type: ignore[assignment]
) -> str:
    """Create an invite token for a workspace. You must be a member."""
    return await WorkspaceDao(s).create_invite(
        workspace_id=workspace_id, created_by=uid, expires_in_hours=expires_in_hours
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def join_workspace(
    invite_token: str,
    s: AsyncSession = MCPSessionDep,  # type: ignore[assignment]
    uid: int = UserDep,  # type: ignore[assignment]
) -> WorkspaceInfo:
    """Join a workspace using an invite token."""
    return await WorkspaceDao(s).use_invite(token=invite_token, user_id=uid)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True))
async def leave_workspace(
    workspace_id: int,
    s: AsyncSession = MCPSessionDep,  # type: ignore[assignment]
    uid: int = UserDep,  # type: ignore[assignment]
) -> None:
    """Leave a workspace. Owners must delete the workspace instead."""
    await WorkspaceDao(s).remove_member(workspace_id=workspace_id, user_id=uid)
