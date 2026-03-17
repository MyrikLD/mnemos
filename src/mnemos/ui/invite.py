from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from mnemos.db import APISessionDep
from .utils import UIAuthDep, _make_cookie, templates

router = APIRouter()


@router.get("/invite/{token}", response_class=HTMLResponse)
async def invite_get(
    request: Request, token: str, s: APISessionDep, auth: UIAuthDep
) -> Response:
    from mnemos.dao.user import UserDao

    dao = UserDao(s)

    # If already logged in, use the invite immediately
    if auth and auth[0] > 0:
        user_id, workspace_id = auth
        invited_ws = await dao.use_invite(token, user_id)
        if invited_ws is not None:
            # Update cookie to new workspace
            response = RedirectResponse("/", status_code=303)
            response.set_cookie(
                "mnemos_session",
                _make_cookie(user_id, invited_ws),
                httponly=True,
                samesite="lax",
            )
            return response
        # Invalid/used/expired invite
        return templates.TemplateResponse(
            request,
            "invite.html",
            {
                "token": token,
                "error": "This invite link is invalid or has already been used.",
            },
        )

    # Not logged in: show landing page with register/sign-in links
    # Validate the token exists and is not expired
    from mnemos.models.workspace_invite import WorkspaceInvite
    from mnemos.models.workspace import Workspace
    import sqlalchemy as sa
    from datetime import datetime

    row = (
        await s.execute(
            sa.select(
                WorkspaceInvite.workspace_id,
                WorkspaceInvite.used_at,
                WorkspaceInvite.expires_at,
            ).where(WorkspaceInvite.token == token)
        )
    ).one_or_none()

    if row is None or row.used_at is not None or row.expires_at < datetime.utcnow():
        return templates.TemplateResponse(
            request,
            "invite.html",
            {
                "token": token,
                "error": "This invite link is invalid or has already been used.",
            },
        )

    ws_name = await s.scalar(
        sa.select(Workspace.name).where(Workspace.id == row.workspace_id)
    )

    return templates.TemplateResponse(
        request,
        "invite.html",
        {"token": token, "workspace_name": ws_name},
    )
