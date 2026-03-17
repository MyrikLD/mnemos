import json
import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from starlette import status

from mnemos.dao import MemoryDao
from mnemos.db import APISessionDep
from mnemos.models import Memory
from mnemos.models.workspace_member import WorkspaceMember
from mnemos.schemas import ImportItem
from mnemos.ui.utils import UIAuthDep, require_auth

router = APIRouter()


@router.get("/export", dependencies=[Depends(require_auth)])
async def export_memories_ui(s: APISessionDep, auth: UIAuthDep) -> Response:
    user_id = auth[0] if auth and auth[0] > 0 else None
    workspace_id = auth[1] if auth and auth[1] > 0 else None
    all_ws_ids: list[int] | None = None
    if user_id is not None:
        ws_rows = await s.execute(
            select(WorkspaceMember.workspace_id).where(
                WorkspaceMember.user_id == user_id
            )
        )
        ids_list = [r[0] for r in ws_rows.all()]
        all_ws_ids = ids_list or None

    q = select(
        Memory.id,
        Memory.content,
        Memory.memory_type,
        Memory.created_at,
        Memory.extra_data.label("metadata"),
    ).order_by(Memory.created_at)
    if all_ws_ids:
        q = q.where(Memory.workspace_id.in_(all_ws_ids))
    elif workspace_id is not None:
        q = q.where(Memory.workspace_id == workspace_id)

    rows = (await s.execute(q)).mappings().all()
    ids = [r["id"] for r in rows]
    tags_map = await MemoryDao(s, workspace_id, all_ws_ids).fetch_tags(ids) if ids else {}
    data = [
        ImportItem(
            **r,
            tags=tags_map.get(r["id"], []),
        ).model_dump(mode="json")
        for r in rows
    ]
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=memories.json"},
    )


@router.post("/import", dependencies=[Depends(require_auth)])
async def import_memories_ui(
    s: APISessionDep, auth: UIAuthDep, file: UploadFile = File()
) -> Response:
    workspace_id = auth[1] if auth and auth[1] > 0 else None
    try:
        items = json.loads(await file.read())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array")

    dao = MemoryDao(s, workspace_id)
    imported = skipped = 0
    for item in items:
        try:
            parsed = ImportItem.model_validate(item)
        except Exception as e:
            logging.warning(f"Error {e} during import: {item}")
            skipped += 1
            continue
        _, created = await dao.create(
            content=parsed.content,
            memory_type=parsed.memory_type,
            metadata=parsed.metadata,
            tags=parsed.tags,
        )
        if created:
            imported += 1
        else:
            skipped += 1

    return RedirectResponse(
        f"/?imported={imported}&skipped={skipped}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
