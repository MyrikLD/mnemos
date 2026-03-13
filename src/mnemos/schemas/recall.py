from pydantic import BaseModel


class RecallResult(BaseModel):
    id: int
    content: str
    memory_type: str | None
    tags: list[str]
    created_at: str
