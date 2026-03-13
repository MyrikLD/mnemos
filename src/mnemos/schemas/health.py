from pydantic import BaseModel


class HealthResult(BaseModel):
    status: str
    total_memories: int
    db_path: str
    db_size_bytes: int
    schema_version: int | None
    vec_extension: str
    fts_extension: str
