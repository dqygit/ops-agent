from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.assets import router as assets_router
from app.api.groups import router as groups_router
from app.api.health import router as health_router
from app.api.models import router as models_router
from app.api.console import router as console_router
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
app.include_router(terminal_router)
app.include_router(groups_router)
app.include_router(console_router)


__all__ = [
    "app",
    "assets_router",
    "get_terminal_service",
    "groups_router",
    "health_router",
    "console_router",
    "lifespan",
    "models_router",
    "terminal_router",
]
