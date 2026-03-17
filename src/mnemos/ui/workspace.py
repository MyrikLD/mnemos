from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from mnemos.config import settings
from mnemos.db import APISessionDep
from .utils import UIAuthDep, require_auth, templates

router = APIRouter()


@router.get(
    "/workspace", response_class=HTMLResponse, dependencies=[Depends(require_auth)]
)
async def workspace_get(
    request: Request, s: APISessionDep, auth: UIAuthDep
) -> HTMLResponse:
    if not auth or auth[0] < 0:
        raise HTTPException(status_code=403, detail="Multi-user mode not enabled")

    user_id, workspace_id = auth
    from mnemos.dao.user import UserDao

    dao = UserDao(s)
    members = await dao.get_workspace_members(workspace_id)
    invites = await dao.get_workspace_invites(workspace_id)
    ws_name = await dao.get_workspace_name(workspace_id)
    username = await dao.get_username(user_id)
    all_workspaces = await dao.get_user_workspaces(user_id)
    joined_workspaces = [w for w in all_workspaces if w["role"] != "owner"]

    return templates.TemplateResponse(
        request,
        "workspace.html",
        {
            "owned_workspace_id": workspace_id,
            "workspace_name": ws_name,
            "members": members,
            "invites": invites,
            "joined_workspaces": joined_workspaces,
            "base_url": (settings.base_url or str(request.base_url)).rstrip("/"),
            "username": username,
        },
    )


@router.post("/workspace/invite", dependencies=[Depends(require_auth)])
async def create_invite(
    request: Request, s: APISessionDep, auth: UIAuthDep
) -> JSONResponse:
    if not auth or auth[0] < 0:
        raise HTTPException(status_code=403, detail="Multi-user mode not enabled")

    user_id, workspace_id = auth
    from mnemos.dao.user import UserDao

    dao = UserDao(s)
    is_owner = await dao.is_workspace_owner(workspace_id, user_id)
    if not is_owner:
        raise HTTPException(
            status_code=403, detail="Only workspace owners can create invites"
        )

    token = await dao.create_invite(workspace_id=workspace_id, created_by=user_id)
    base_url = (settings.base_url or str(request.base_url)).rstrip("/")
    invite_url = f"{base_url}/ui/invite/{token}"
    return JSONResponse({"invite_url": invite_url, "token": token})


@router.delete("/workspace/invite/{token}", dependencies=[Depends(require_auth)])
async def delete_invite(token: str, s: APISessionDep, auth: UIAuthDep) -> Response:
    if not auth or auth[0] < 0:
        raise HTTPException(status_code=403, detail="Multi-user mode not enabled")

    import sqlalchemy as sa
    from datetime import datetime
    from mnemos.models.workspace_invite import WorkspaceInvite

    await s.execute(
        sa.update(WorkspaceInvite)
        .where(WorkspaceInvite.token == token)
        .values(expires_at=datetime(2000, 1, 1))
    )
    return Response(content="", status_code=200)


@router.delete("/workspace/{ws_id}/leave", dependencies=[Depends(require_auth)])
async def leave_workspace(ws_id: int, s: APISessionDep, auth: UIAuthDep) -> Response:
    if not auth or auth[0] < 0:
        raise HTTPException(status_code=403, detail="Not supported in legacy mode")

    user_id, owned_ws_id = auth
    if ws_id == owned_ws_id:
        raise HTTPException(status_code=400, detail="Cannot leave your own workspace")

    from mnemos.dao.user import UserDao

    try:
        await UserDao(s).leave_workspace(user_id, ws_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(content="", status_code=200)
