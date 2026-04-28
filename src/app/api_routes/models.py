from fastapi import APIRouter

from app.api_routes.schemas import ModelsView
from app.services.model_service import ModelService

router = APIRouter()


@router.get("/api/models")
def list_models() -> ModelsView:
    model_service = ModelService()
    config = model_service.load_settings()
    return ModelsView(
        provider=config.provider.value,
        selected_model=config.model_name,
        available_models=model_service.list_available_models(config.provider),
    )
