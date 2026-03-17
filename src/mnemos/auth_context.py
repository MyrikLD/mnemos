from contextvars import ContextVar

owned_workspace_id: ContextVar[int | None] = ContextVar(
    "owned_workspace_id", default=None
)
member_workspace_ids: ContextVar[list[int] | None] = ContextVar(
    "member_workspace_ids", default=None
)
current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)
