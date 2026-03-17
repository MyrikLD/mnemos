from fastmcp import FastMCP
from fastmcp.server.auth import AuthProvider
from mnemos.config import settings
from mnemos.oauth import MnemosOAuthProvider
from mnemos.tools import (
    delete,
    get_memory,
    health,
    list_memories,
    recall,
    retrieve,
    search_by_tag,
    store,
    update,
)

_provider: MnemosOAuthProvider | None = None


def _build_auth() -> AuthProvider | None:
    global _provider
    if settings.oauth_jwt_secret and settings.base_url:
        _provider = MnemosOAuthProvider(
            base_url=settings.base_url,
            jwt_secret=settings.oauth_jwt_secret,
            db_lookup=_lookup_user,
        )
        return _provider
    return None


def get_provider() -> MnemosOAuthProvider | None:
    return _provider


async def _lookup_user(username: str, password: str) -> tuple[int, int] | None:
    from mnemos.dao.user import UserDao
    from mnemos.db import session

    async with session() as s:
        return await UserDao(s).authenticate(username, password)


mcp: FastMCP = FastMCP("Mnemos", auth=_build_auth())

mcp.mount(store)
mcp.mount(retrieve)
mcp.mount(recall)
mcp.mount(get_memory)
mcp.mount(list_memories)
mcp.mount(search_by_tag)
mcp.mount(delete)
mcp.mount(update)
mcp.mount(health)
