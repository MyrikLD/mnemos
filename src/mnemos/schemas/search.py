from pydantic import BaseModel


class SearchResult(BaseModel):
    id: int
    content: str
    memory_type: str | None
    rrf_score: float
    vec_similarity: float | None


class MemoryResult(BaseModel):
    id: int
    content: str
    memory_type: str | None
    tags: list[str]
    metadata: dict | None
    created_at: str | None
    rrf_score: float
