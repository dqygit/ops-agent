from fastapi import APIRouter

from app.api.schemas import SkillPackageView, SkillsResponse
from app.services.skill_service import SkillService

router = APIRouter()
_skill_service = SkillService()


@router.get("/api/skills")
def list_skills() -> SkillsResponse:
    return SkillsResponse(
        skills=[
            SkillPackageView(
                name=skill.name,
                description=skill.description,
                path=skill.path,
                valid=skill.valid,
                error=skill.error,
                updated_at=skill.updated_at,
                body_size=skill.body_size,
            )
            for skill in _skill_service.list_skills()
        ]
    )
