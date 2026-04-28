from app.api_routes.assets import router as assets_router
from app.api_routes.chat import router as chat_router
from app.api_routes.health import router as health_router
from app.api_routes.models import router as models_router
from app.api_routes.terminal import router as terminal_router

__all__ = ["assets_router", "chat_router", "health_router", "models_router", "terminal_router"]
