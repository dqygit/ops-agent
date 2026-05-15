import { requestJson } from './client'
import type { SkillPackageDto, SkillsResponseDto } from '../types/api'
import type { SkillPackage } from '../types/ops'

export function mapSkillPackage(dto: SkillPackageDto): SkillPackage {
  return {
    name: dto.name,
    description: dto.description,
    path: dto.path,
    valid: dto.valid,
    error: dto.error,
    updatedAt: dto.updated_at,
    bodySize: dto.body_size,
  }
}

export async function getSkills(): Promise<SkillPackage[]> {
  const response = await requestJson<SkillsResponseDto>('/api/skills')
  return response.skills.map(mapSkillPackage)
}
