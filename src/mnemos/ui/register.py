from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from mnemos.config import settings
from mnemos.db import APISessionDep
from .utils import _make_cookie, templates

router = APIRouter()


@router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request, invite: str = "") -> HTMLResponse:
    return templates.TemplateResponse(request, "register.html", {"invite": invite})


@router.post("/register")
async def register_post(
    request: Request,
    s: APISessionDep,
    username: str = Form(),
    password: str = Form(),
    confirm: str = Form(),
    invite: str = Form(default=""),
) -> Response:
    if not settings.oauth_jwt_secret:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"invite": invite, "error": "Registration is not enabled."},
            status_code=400,
        )

    if password != confirm:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"invite": invite, "error": "Passwords do not match."},
            status_code=400,
        )

    if len(username.strip()) < 2:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"invite": invite, "error": "Username must be at least 2 characters."},
            status_code=400,
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"invite": invite, "error": "Password must be at least 6 characters."},
            status_code=400,
        )

    from mnemos.dao.user import UserDao

    dao = UserDao(s)
    try:
        user_id, workspace_id = await dao.create_user_with_workspace(
            username.strip(), password
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"invite": invite, "error": str(e)},
            status_code=400,
        )

    # Handle invite token if provided
    if invite:
        invited_ws = await dao.use_invite(invite, user_id)
        if invited_ws is not None:
            workspace_id = invited_ws

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "mnemos_session",
        _make_cookie(user_id, workspace_id),
        httponly=True,
        samesite="lax",
    )
    return response
