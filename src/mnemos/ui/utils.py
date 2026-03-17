import hashlib
import hmac
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from starlette.templating import Jinja2Templates

from mnemos.config import settings

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def _make_cookie(user_id: int, workspace_id: int) -> str:
    """Create a signed cookie value: '{user_id}:{workspace_id}:{hmac}'."""
    if not settings.oauth_jwt_secret:
        raise RuntimeError("No secret configured for cookie signing")
    payload = f"{user_id}:{workspace_id}"
    sig = hmac.new(
        settings.oauth_jwt_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}:{sig}"


def _decode_cookie(value: str) -> tuple[int, int] | None:
    """Decode and verify a signed cookie. Returns (user_id, workspace_id) or None."""
    if not settings.oauth_jwt_secret:
        return None
    parts = value.split(":")
    if len(parts) != 3:
        return None
    user_id_str, workspace_id_str, sig = parts
    try:
        user_id = int(user_id_str)
        workspace_id = int(workspace_id_str)
    except ValueError:
        return None
    payload = f"{user_id}:{workspace_id}"
    expected = hmac.new(
        settings.oauth_jwt_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return user_id, workspace_id


def _legacy_session_token() -> str:
    """Legacy single-password session token (for no-auth mode)."""
    if not settings.password:
        return ""
    return hmac.new(
        settings.password.encode(), b"mnemos-ui-session", hashlib.sha256
    ).hexdigest()


def get_ui_auth(request: Request) -> tuple[int, int] | None:
    """Extract (user_id, workspace_id) from session cookie, or None if not authenticated."""
    # Multi-user mode: signed cookie with user_id:workspace_id
    token = request.cookies.get("mnemos_session")
    if token and settings.oauth_jwt_secret:
        decoded = _decode_cookie(token)
        if decoded:
            return decoded
        return None

    # Legacy single-password mode: just check token matches
    if token and settings.password:
        expected = _legacy_session_token()
        if expected and hmac.compare_digest(token, expected):
            # Return sentinel values for single-user mode
            return (-1, -1)

    return None


UIAuthDep = Annotated[tuple[int, int] | None, Depends(get_ui_auth)]


async def get_ui_username(
    request: Request,
) -> str:
    """Return the logged-in username for nav display, or empty string."""
    from mnemos.db import session as db_session
    from mnemos.dao.user import UserDao

    auth = get_ui_auth(request)
    if auth is None or auth[0] <= 0:
        return ""
    user_id = auth[0]
    try:
        async with db_session() as s:
            return await UserDao(s).get_username(user_id) or ""
    except Exception:
        return ""


UIUsernameDep = Annotated[str, Depends(get_ui_username)]


def require_auth(request: Request) -> None:
    """Dependency: raise 307 redirect to login if not authenticated."""
    # No password/jwt configured → open access
    if not settings.password and not settings.oauth_jwt_secret:
        return

    token = request.cookies.get("mnemos_session")
    if not token:
        raise HTTPException(
            status_code=307, headers={"Location": f"/ui/login?next={request.url.path}"}
        )

    # Multi-user mode
    if settings.oauth_jwt_secret:
        if not _decode_cookie(token):
            raise HTTPException(
                status_code=307,
                headers={"Location": f"/ui/login?next={request.url.path}"},
            )
        return

    # Legacy single-password mode
    if settings.password:
        expected = _legacy_session_token()
        if not expected or not hmac.compare_digest(token, expected):
            raise HTTPException(
                status_code=307,
                headers={"Location": f"/ui/login?next={request.url.path}"},
            )
