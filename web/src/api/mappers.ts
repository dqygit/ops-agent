export type TimestampDto = {
  created_at: string | null
  updated_at: string | null
}

export type RequiredTimestampDto = {
  created_at: string
  updated_at: string
}

export type UpdatedAtDto = {
  updated_at: string | null
}

export type RequiredUpdatedAtDto = {
  updated_at: string
}

export function mapTimestamps(dto: TimestampDto) {
  return {
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  }
}

export function mapRequiredTimestamps(dto: RequiredTimestampDto) {
  return {
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  }
}

export function mapUpdatedAt(dto: UpdatedAtDto) {
  return {
    updatedAt: dto.updated_at,
  }
}

export function mapRequiredUpdatedAt(dto: RequiredUpdatedAtDto) {
  return {
    updatedAt: dto.updated_at,
  }
}
