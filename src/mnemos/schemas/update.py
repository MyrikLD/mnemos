from pydantic import BaseModel


class UpdateMemoryRequest(BaseModel):
    content: str | None = None
    memory_type: str | None = None
    tags: list[str] | None = None
    metadata: dict | None = None
