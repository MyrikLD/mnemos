from pydantic import BaseModel


class MemoryListItem(BaseModel):
    id: int
    content: str
    memory_type: str | None
    metadata: dict | None
    tags: list[str]
    created_at: str


class MemoryPage(BaseModel):
    items: list[MemoryListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
