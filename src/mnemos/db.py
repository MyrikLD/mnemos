from contextlib import asynccontextmanager
from functools import cache
from typing import Annotated

from fastapi import Depends as APIDepends
from fastmcp.dependencies import Depends as MCPDepends
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from mnemos.config import settings


@cache
def get_engine() -> AsyncEngine:
    return create_async_engine(settings.db_url, echo=settings.db_echo)


@cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=True)


async def session_dep():
    session_factory = get_session_factory()
    async with session_factory() as s, s.begin():
        yield s


MCPSessionDep = MCPDepends(asynccontextmanager(session_dep))
# APISessionDep = APIDepends(session_dep)
APISessionDep = Annotated[AsyncSession, APIDepends(session_dep)]

session = asynccontextmanager(session_dep)


async def workspace_session_dep():
    from mnemos.auth_context import owned_workspace_id, member_workspace_ids

    ws_id = owned_workspace_id.get()
    ws_ids = member_workspace_ids.get()
    # When OAuth is not configured, ws_id stays None → no workspace filtering (dev mode).
    # When OAuth is configured and no valid token was found, ws_id is None → raise error.
    if ws_id is None and settings.oauth_jwt_secret:
        raise RuntimeError(
            "No workspace context — unauthenticated request or OAuth not configured"
        )
    session_factory = get_session_factory()
    async with session_factory() as s, s.begin():
        yield s, ws_id, ws_ids


MCPWorkspaceSessionDep = MCPDepends(asynccontextmanager(workspace_session_dep))

__all__ = ["MCPSessionDep", "MCPWorkspaceSessionDep", "APISessionDep", "session"]
