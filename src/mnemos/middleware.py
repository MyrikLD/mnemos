import logging
from typing import Callable

import sqlalchemy as sa
from authlib.jose.errors import JoseError

from mnemos.auth_context import (
    current_user_id,
    owned_workspace_id,
    member_workspace_ids,
)
from mnemos.db import session
from mnemos.models.oauth_client import OAuthClient
from mnemos.models.workspace_member import WorkspaceMember

logger = logging.getLogger(__name__)


class WorkspaceMiddleware:
    """Pure ASGI middleware — does NOT buffer responses, safe for SSE/streaming."""

    def __init__(self, app, provider) -> None:
        self._app = app
        self._provider = provider

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                token = auth_header[len("Bearer ") :]
                await self._resolve(token)

        await self._app(scope, receive, send)

    async def _resolve(self, token: str) -> None:
        try:
            claims = self._provider._jwt.verify_token(token)
            client_id = claims.get("client_id")
            if not client_id:
                return

            async with session() as s:
                user_id = await s.scalar(
                    sa.select(OAuthClient.user_id).where(
                        OAuthClient.client_id == client_id
                    )
                )

            if user_id is None:
                return

            async with session() as s:
                rows = (
                    await s.execute(
                        sa.select(WorkspaceMember.workspace_id, WorkspaceMember.role)
                        .where(WorkspaceMember.user_id == user_id)
                        .order_by(WorkspaceMember.joined_at)
                    )
                ).all()

            all_ids = [r[0] for r in rows]
            owned_id = next(
                (r[0] for r in rows if r[1] == "owner"), all_ids[0] if all_ids else None
            )

            if owned_id is not None:
                current_user_id.set(user_id)
                owned_workspace_id.set(owned_id)
                member_workspace_ids.set(all_ids)

        except (JoseError, Exception) as exc:
            logger.debug("WorkspaceMiddleware: token resolution failed: %s", exc)
