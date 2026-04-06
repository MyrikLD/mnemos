from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from sqlalchemy.ext.asyncio import AsyncSession

from memlord.auth import MCPUserDep
from memlord.dao import MemoryDao
from memlord.db import MCPSessionDep
from memlord.schemas import MemoryListItem

mcp = FastMCP()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
async def get_memory(
    id: int,
    s: AsyncSession = MCPSessionDep,  # type: ignore[assignment]
    uid: int = MCPUserDep,  # type: ignore[assignment]
) -> MemoryListItem:
    """Fetch full content of a single memory by numeric ID.

    Use only when you already know the ID — e.g. after retrieve_memory() or recall_memory()
    which return IDs in their results alongside compact snippets.
    Do NOT use for search — use retrieve_memory() for semantic/text search
    or recall_memory() for time-based queries like 'last week'.
    """
    result = await MemoryDao(s, uid).get(id)
    if result is None:
        raise ValueError(f"Memory with id={id} not found")
    return result
