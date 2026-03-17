from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.dao import MemoryDao
from mnemos.db import MCPWorkspaceSessionDep
from mnemos.schemas import MemoryType, StoreResult

mcp = FastMCP()


@mcp.tool(
    output_schema=StoreResult.model_json_schema(),
    annotations=ToolAnnotations(idempotentHint=True, destructiveHint=False),
)
async def store_memory(
    content: str,
    memory_type: MemoryType,
    tags: list[str] | None = None,
    metadata: dict | None = None,
    ctx: tuple = MCPWorkspaceSessionDep,  # type: ignore[assignment]
) -> StoreResult:
    """Save a new memory. Idempotent: returns existing if content already stored."""
    s: AsyncSession
    s, workspace_id, _workspace_ids = ctx
    dao = MemoryDao(s, workspace_id)
    memory_id, created = await dao.create(
        content=content,
        memory_type=memory_type,
        metadata=metadata or {},
        tags=tags or [],
    )
    return StoreResult(id=memory_id, created=created)
