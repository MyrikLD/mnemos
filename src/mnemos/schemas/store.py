from pydantic import BaseModel

from .memory_type import MemoryType


class ImportItem(BaseModel):
    content: str
    memory_type: MemoryType | None = None
    tags: list[str] = []
    metadata: dict | None = None
    created_at: str | None = None


class StoreResult(BaseModel):
    id: int
    created_at: str
    created: bool
