from datetime import UTC, datetime

from pydantic import BaseModel, NaiveDatetime, field_serializer

from .memory_type import MemoryType


class SearchResult(BaseModel):
    id: int
    name: str
    content: str
    memory_type: MemoryType
    rrf_score: float
    vec_similarity: float | None
    workspace: str | None = None


class MemoryResult(BaseModel):
    name: str
    memory_type: MemoryType
    tags: set[str]
    metadata: dict
    created_at: NaiveDatetime
    rrf_score: float
    workspace: str | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return v.replace(tzinfo=UTC).isoformat()


class SearchItem(BaseModel):
    id: int
    content: str
    memory_type: str | None
    created_at: str
    workspace_id: int | None
    workspace_name: str | None
    tags: list[str]
    rrf_score: float


class SearchResponse(BaseModel):
    results: list[SearchItem]
    query: str
