from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api_routes import assets_router, chat_router, health_router, models_router, terminal_router
from app.api_routes.dependencies import get_chat_service
from app.api_routes.terminal import get_terminal_service
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> Iterator[None]:
    init_db()
    yield


app = FastAPI(title="Ops Agent API", lifespan=lifespan)
app.include_router(health_router)
app.include_router(models_router)
app.include_router(assets_router)
app.include_router(chat_router)
app.include_router(terminal_router)

__all__ = ["app", "get_chat_service", "get_terminal_service"]
