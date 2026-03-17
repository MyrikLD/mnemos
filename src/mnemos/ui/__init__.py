from fastapi import APIRouter

from .base import router
from .data import router as data_router
from .invite import router as invite_router
from .login import router as login_router
from .register import router as register_router
from .workspace import router as workspace_router

ui_router = APIRouter(prefix="/ui")
ui_router.include_router(data_router)
ui_router.include_router(login_router)
ui_router.include_router(register_router)
ui_router.include_router(workspace_router)
ui_router.include_router(invite_router)
router.include_router(ui_router)
