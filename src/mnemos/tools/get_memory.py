from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mnemos.dao import MemoryDao
from mnemos.db import MCPWorkspaceSessionDep
from mnemos.schemas import MemoryListItem
from sqlalchemy.ext.asyncio import AsyncSession

mcp = FastMCP()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
async def get_memory(
    id: int,
    ctx: tuple = MCPWorkspaceSessionDep,  # type: ignore[assignment]
) -> MemoryListItem:
    """Fetch a single memory by ID with full details (tags, metadata)."""
    s: AsyncSession
    s, workspace_id, workspace_ids = ctx
    result = await MemoryDao(s, workspace_id, workspace_ids).get(id)
    if result is None:
        raise ValueError(f"Memory with id={id} not found")
    return result
