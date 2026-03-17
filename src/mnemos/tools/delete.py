from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mnemos.dao import MemoryDao
from mnemos.db import MCPWorkspaceSessionDep
from mnemos.schemas import DeleteResult
from sqlalchemy.ext.asyncio import AsyncSession

mcp = FastMCP()


@mcp.tool(
    output_schema=DeleteResult.model_json_schema(),
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False),
)
async def delete_memory(
    id: int,
    ctx: tuple = MCPWorkspaceSessionDep,  # type: ignore[assignment]
) -> DeleteResult:
    """Delete a memory by ID. Removes from vec index and FTS (via trigger)."""
    s: AsyncSession
    s, workspace_id, _workspace_ids = ctx
    dao = MemoryDao(s, workspace_id)
    await dao.delete(id)
    return DeleteResult(success=True, id=id)
