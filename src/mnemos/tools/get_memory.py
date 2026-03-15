from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mnemos.dao import MemoryDao
from mnemos.db import MCPSessionDep
from mnemos.schemas import MemoryListItem
from sqlalchemy.ext.asyncio import AsyncSession

mcp = FastMCP()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
async def get_memory(
    id: int,
    s: AsyncSession = MCPSessionDep,  # type: ignore[assignment]
) -> MemoryListItem:
    """Fetch a single memory by ID with full details (tags, metadata)."""
    result = await MemoryDao(s).get(id)
    if result is None:
        raise ValueError(f"Memory with id={id} not found")
    return result
