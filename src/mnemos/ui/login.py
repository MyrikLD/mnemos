import secrets

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from mnemos.config import settings
from mnemos.db import APISessionDep
from .utils import _make_cookie, _legacy_session_token, templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_get(
    request: Request, next: str = "/", invite: str = ""
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "login.html", {"next": next, "invite": invite}
    )


@router.post("/login")
async def login_post(
    request: Request,
    s: APISessionDep,
    password: str = Form(default=""),
    username: str = Form(default=""),
    next: str = Form(default="/"),
    invite: str = Form(default=""),
) -> Response:
    # Multi-user mode: verify against DB
    if settings.oauth_jwt_secret:
        from mnemos.dao.user import UserDao

        result = await UserDao(s).authenticate(username, password)
        if result is None:
            return templates.TemplateResponse(
                request,
                "login.html",
                {
                    "next": next,
                    "invite": invite,
                    "error": "Incorrect username or password.",
                },
                status_code=401,
            )
        user_id, workspace_id = result

        # Handle invite token if provided
        if invite:
            dao = UserDao(s)
            invited_ws = await dao.use_invite(invite, user_id)
            if invited_ws is not None:
                workspace_id = invited_ws

        redirect_to = next if next.startswith("/") else "/"
        response = RedirectResponse(redirect_to, status_code=303)
        response.set_cookie(
            "mnemos_session",
            _make_cookie(user_id, workspace_id),
            httponly=True,
            samesite="lax",
        )
        return response

    # Legacy single-password mode
    if not settings.password or not secrets.compare_digest(
        password.encode(), settings.password.encode()
    ):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"next": next, "invite": invite, "error": "Incorrect password."},
            status_code=401,
        )
    redirect_to = next if next.startswith("/") else "/"
    response = RedirectResponse(redirect_to, status_code=303)
    response.set_cookie(
        "mnemos_session", _legacy_session_token(), httponly=True, samesite="lax"
    )
    return response


@router.get("/logout")
async def logout() -> Response:
    response = RedirectResponse("/ui/login", status_code=303)
    response.delete_cookie("mnemos_session")
    return response
