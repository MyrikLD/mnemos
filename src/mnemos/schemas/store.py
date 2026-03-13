from pydantic import BaseModel


class StoreResult(BaseModel):
    id: int
    created_at: str
    created: bool
