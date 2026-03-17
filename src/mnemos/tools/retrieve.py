from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.dao import MemoryDao
from mnemos.db import MCPWorkspaceSessionDep
from mnemos.schemas import MemoryResult, MemoryType
from mnemos.search import hybrid_search
from mnemos.utils.dt import utcnow

mcp = FastMCP()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
async def retrieve_memory(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.7,
    memory_type: MemoryType | None = None,
    ctx: tuple = MCPWorkspaceSessionDep,  # type: ignore[assignment]
) -> list[MemoryResult]:
    """Hybrid semantic + full-text search over stored memories."""
    s: AsyncSession
    s, workspace_id, workspace_ids = ctx

    results = await hybrid_search(
        s,
        query=query,
        limit=limit,
        similarity_threshold=similarity_threshold,
        memory_type=memory_type,
        workspace_id=workspace_id,
        workspace_ids=workspace_ids,
    )

    if not results:
        return []

    dao = MemoryDao(s, workspace_id, workspace_ids)
    ids = [r.id for r in results]
    tags_map = await dao.fetch_tags(ids)
    meta_map = await dao.fetch_metadata(ids)

    output = []
    for r in results:
        metadata, created_at = meta_map.get(r.id, ({}, utcnow()))
        output.append(
            MemoryResult(
                id=r.id,
                content=r.content,
                memory_type=r.memory_type,
                tags=tags_map.get(r.id, []),
                metadata=metadata,
                created_at=created_at,
                rrf_score=r.rrf_score,
            )
        )
    return output
