from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mnemos.db import MCPSessionDep
from mnemos.embeddings import embed
from mnemos.models import Memory, MemoryTag, Tag
from mnemos.schemas import StoreResult
from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

mcp = FastMCP()


@mcp.tool(
    output_schema=StoreResult.model_json_schema(),
    annotations=ToolAnnotations(idempotentHint=False, destructiveHint=False),
)
async def update_memory(
    id: int,
    content: str | None = None,
    memory_type: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
    s: AsyncSession = MCPSessionDep,  # type: ignore[assignment]
) -> StoreResult:
    """Update an existing memory by ID. Only provided fields are changed."""
    row = await s.execute(select(Memory.id, Memory.created_at).where(Memory.id == id))
    existing = row.one_or_none()
    if existing is None:
        raise ValueError(f"Memory with id={id} not found")

    memory_id, created_at = existing

    values: dict = {}
    if content is not None:
        values["content"] = content
    if memory_type is not None:
        values["memory_type"] = memory_type
    if metadata is not None:
        values["extra_data"] = metadata

    if values:
        await s.execute(update(Memory).where(Memory.id == memory_id).values(**values))

    # Re-embed if content changed (FTS5 updated via trigger)
    if content is not None:
        vector = embed(content)
        vec_str = "[" + ",".join(str(v) for v in vector) + "]"
        await s.execute(
            text("UPDATE memories_vec SET embedding = :vec WHERE memory_id = :id"),
            {"vec": vec_str, "id": memory_id},
        )

    # Replace tags if provided
    if tags is not None:
        await s.execute(delete(MemoryTag).where(MemoryTag.memory_id == memory_id))
        for tag_name in tags:
            normalized = tag_name.lower().strip()
            if not normalized:
                continue
            await s.execute(
                sqlite_insert(Tag).values(name=normalized).on_conflict_do_nothing()
            )
            tag_id = await s.scalar(select(Tag.id).where(Tag.name == normalized))
            await s.execute(
                sqlite_insert(MemoryTag)
                .values(memory_id=memory_id, tag_id=tag_id)
                .on_conflict_do_nothing()
            )

    return StoreResult(id=memory_id, created_at=str(created_at), created=False)
