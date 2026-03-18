from datetime import datetime

from pydantic import BaseModel


class WorkspaceInfo(BaseModel):
    id: int
    name: str
    role: str  # caller's role: 'owner' | 'editor' | 'member' | 'viewer'
    member_count: int


class WorkspaceMemberInfo(BaseModel):
    user_id: int
    display_name: str
    email: str
    role: str
    joined_at: datetime
