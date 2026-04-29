from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.assets import router as assets_router
from app.api.auto_approval import router as auto_approval_router
from app.api.chat import router as chat_router
from app.api.console import router as console_router
from app.api.dependencies import get_chat_service
from app.api.groups import router as groups_router
from app.api.health import router as health_router
from app.api.models import router as models_router
from app.api.terminal import get_terminal_service, router as terminal_router
from app.db.session import Session, engine, init_db
from app.services.asset_service import ensure_default_asset_group


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    with Session(engine) as session:
        ensure_default_asset_group(session)
    yield


app = FastAPI(title="Ops Agent API", lifespan=lifespan)
app.include_router(health_router)
app.include_router(models_router)
app.include_router(assets_router)
app.include_router(chat_router)
app.include_router(terminal_router)
app.include_router(auto_approval_router)
app.include_router(groups_router)
app.include_router(console_router)

__all__ = [
    "app",
    "assets_router",
    "auto_approval_router",
    "chat_router",
    "console_router",
    "get_chat_service",
    "get_terminal_service",
    "groups_router",
    "health_router",
    "lifespan",
    "models_router",
    "terminal_router",
]
