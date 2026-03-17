import math

import sqlalchemy as sa
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
)
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from mnemos.dao import MemoryDao
from mnemos.db import APISessionDep
from mnemos.models import Memory, MemoryTag, Tag
from mnemos.models.workspace import Workspace
from mnemos.models.workspace_member import WorkspaceMember
from mnemos.schemas import MemoryType, UpdateMemoryRequest
from mnemos.search import hybrid_search
from mnemos.ui.utils import UIAuthDep, UIUsernameDep, require_auth, templates
from mnemos.utils.dt import utcnow

router = APIRouter()

_UNSET = object()

_COLS = (
    Memory.id,
    Memory.content,
    Memory.memory_type,
    Memory.created_at,
)

_COLS_WS = (
    Memory.id,
    Memory.content,
    Memory.memory_type,
    Memory.created_at,
    Memory.workspace_id,
    Workspace.name.label("workspace_name"),
)


async def _all_ws_ids(s, user_id: int | None) -> list[int] | None:
    """Return all workspace IDs the user is a member of, or None if not in auth mode."""
    if user_id is None or user_id <= 0:
        return None
    rows = await s.execute(
        select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
    )
    ids = [r[0] for r in rows.all()]
    return ids or None


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def index(
    request: Request,
    s: APISessionDep,
    auth: UIAuthDep,
    username: UIUsernameDep,
    page: int = 1,
    page_size: int = 20,
    memory_type: str | None = None,
    tag: str = "",
    workspace_filter: str | None = None,  # type: ignore[assignment]
) -> HTMLResponse:
    user_id = auth[0] if auth and auth[0] > 0 else None
    workspace_id = auth[1] if auth and auth[1] > 0 else None
    all_ws_ids = await _all_ws_ids(s, user_id)
    workspace_filter = int(workspace_filter) if workspace_filter else None
    # Load workspace list for filter dropdown
    user_workspaces: list[dict] = []
    if user_id and user_id > 0:
        from mnemos.dao.user import UserDao

        user_workspaces = await UserDao(s).get_user_workspaces(user_id)

    show_workspace_badge = len(all_ws_ids or []) > 1

    # Validate workspace_filter is in user's allowed workspaces
    if (
        workspace_filter is not None
        and all_ws_ids
        and workspace_filter not in all_ws_ids
    ):
        workspace_filter = None

    # Determine effective workspace filter
    if workspace_filter is not None:
        q_ws_ids: list[int] | None = [workspace_filter]
    elif all_ws_ids:
        q_ws_ids = all_ws_ids
    else:
        q_ws_ids = None

    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    q = select(*_COLS_WS).outerjoin(Workspace, Memory.workspace_id == Workspace.id)
    if q_ws_ids:
        q = q.where(Memory.workspace_id.in_(q_ws_ids))
    elif workspace_id is not None:
        q = q.where(Memory.workspace_id == workspace_id)

    if memory_type:
        q = q.where(Memory.memory_type == MemoryType(memory_type))
    if tag:
        tag_subq = (
            select(MemoryTag.memory_id)
            .join(Tag, MemoryTag.tag_id == Tag.id)
            .where(Tag.name == tag.lower().strip())
        )
        q = q.where(Memory.id.in_(tag_subq))

    total = await s.scalar(select(sa.func.count()).select_from(q.subquery())) or 0
    rows = (
        (
            await s.execute(
                q.order_by(Memory.created_at.desc()).limit(page_size).offset(offset)
            )
        )
        .mappings()
        .all()
    )
    total_pages = math.ceil(total / page_size) if total else 0
    ids = [row["id"] for row in rows]
    tags_map = await MemoryDao(s, workspace_id, all_ws_ids).fetch_tags(ids)

    memories = [{"tags": tags_map.get(row["id"], []), **row} for row in rows]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "memories": memories,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "memory_type": memory_type,
            "tag": tag,
            "username": username,
            "user_workspaces": user_workspaces,
            "workspace_filter": workspace_filter,
            "show_workspace_badge": show_workspace_badge,
        },
    )


@router.get(
    "/search", response_class=HTMLResponse, dependencies=[Depends(require_auth)]
)
async def search(
    request: Request,
    s: APISessionDep,
    auth: UIAuthDep,
    username: UIUsernameDep,
    q: str = "",
) -> HTMLResponse:
    user_id = auth[0] if auth and auth[0] > 0 else None
    workspace_id = auth[1] if auth and auth[1] > 0 else None
    all_ws_ids = await _all_ws_ids(s, user_id)
    show_workspace_badge = len(all_ws_ids or []) > 1

    results = []
    if q:
        raw = await hybrid_search(
            s,
            query=q,
            limit=20,
            similarity_threshold=0.0,
            workspace_id=workspace_id,
            workspace_ids=all_ws_ids,
        )
        if raw:
            dao = MemoryDao(s, workspace_id, all_ws_ids)
            ids = [r.id for r in raw]
            tags_map = await dao.fetch_tags(ids)
            created_rows = (
                await s.execute(
                    select(Memory.id, Memory.created_at).where(Memory.id.in_(ids))
                )
            ).fetchall()
            created_map = {row[0]: row[1] for row in created_rows}

            ws_name_map: dict[int, str | None] = {}
            if show_workspace_badge:
                ws_rows = await s.execute(
                    select(Memory.id, Workspace.name.label("workspace_name"))
                    .outerjoin(Workspace, Memory.workspace_id == Workspace.id)
                    .where(Memory.id.in_(ids))
                )
                ws_name_map = {row.id: row.workspace_name for row in ws_rows.fetchall()}

            for r in raw:
                results.append(
                    {
                        "id": r.id,
                        "content": r.content,
                        "memory_type": r.memory_type,
                        "tags": tags_map.get(r.id, []),
                        "created_at": created_map.get(r.id, utcnow()),
                        "rrf_score": round(r.rrf_score, 4),
                        "workspace_name": ws_name_map.get(r.id),
                    }
                )

    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "q": q,
            "results": results,
            "username": username,
            "show_workspace_badge": show_workspace_badge,
        },
    )


@router.get(
    "/memory/{id}", response_class=HTMLResponse, dependencies=[Depends(require_auth)]
)
async def memory_detail(
    request: Request,
    id: int,
    s: APISessionDep,
    auth: UIAuthDep,
    username: UIUsernameDep,
) -> HTMLResponse:
    user_id = auth[0] if auth and auth[0] > 0 else None
    owned_ws_id = auth[1] if auth and auth[1] > 0 else None
    all_ws_ids = await _all_ws_ids(s, user_id)
    memory = await MemoryDao(s, owned_ws_id, all_ws_ids).get(id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    # can_edit: only if memory lives in the user's owned workspace (or no-auth dev mode)
    if owned_ws_id is None:
        can_edit = True
    else:
        mem_ws = await s.scalar(select(Memory.workspace_id).where(Memory.id == id))
        can_edit = mem_ws == owned_ws_id

    return templates.TemplateResponse(
        request,
        "memory.html",
        {
            "memory": memory,
            "username": username,
            "can_edit": can_edit,
        },
    )


@router.put(
    "/memory/{id}", response_class=HTMLResponse, dependencies=[Depends(require_auth)]
)
async def update_memory(
    request: Request,
    id: int,
    s: APISessionDep,
    auth: UIAuthDep,
    body: UpdateMemoryRequest,
) -> HTMLResponse:
    workspace_id = auth[1] if auth and auth[1] > 0 else None
    dao = MemoryDao(s, workspace_id)
    existing = await dao.get(id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    new_content = (body.content or "").strip() or existing.content
    new_type = (body.memory_type or "").strip() or None
    new_tags = [t.lower().strip() for t in (body.tags or []) if t.strip()]

    data: dict = {
        "id": id,
        "memory_type": new_type,
        "metadata": body.metadata,
        "tags": new_tags,
    }
    if new_content != existing.content:
        data["content"] = new_content

    await dao.update(**data)

    return templates.TemplateResponse(
        request,
        "_memory_content.html",
        {
            "memory": {
                "id": id,
                "content": new_content,
                "memory_type": new_type or "",
                "metadata": body.metadata,
                "tags": new_tags,
                "created_at": existing.created_at,
            },
            "success": "Saved.",
            "can_edit": True,
        },
    )


@router.delete("/memory/{id}", dependencies=[Depends(require_auth)])
async def delete_memory_ui(id: int, s: APISessionDep, auth: UIAuthDep) -> Response:
    workspace_id = auth[1] if auth and auth[1] > 0 else None
    try:
        await MemoryDao(s, workspace_id).delete(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found")
    return Response(content="", status_code=200)
