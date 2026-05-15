import { requestJson, requestVoid } from './client'
import type { ConversationContextStatusDto, ConversationCreateResponseDto, ConversationDetailDto, ConversationSummaryDto } from '../types/api'
import type { ConversationContextStatus, ConversationDetail, ConversationSummary, EventItem } from '../types/ops'

export function mapConversationSummary(dto: ConversationSummaryDto): ConversationSummary {
  return {
    id: dto.id,
    title: dto.title,
    selectedModel: dto.selected_model,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    eventCount: dto.event_count,
    lastEventKind: dto.last_event_kind,
  }
}

export function mapConversationDetail(dto: ConversationDetailDto): ConversationDetail {
  return {
    id: dto.id,
    title: dto.title,
    selectedModel: dto.selected_model,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    events: dto.events,
  }
}

export function mapConversationContextStatus(dto: ConversationContextStatusDto): ConversationContextStatus {
  return {
    contextPercent: dto.context_percent,
    contextStatus: dto.context_status,
  }
}

export async function getConversations(): Promise<ConversationSummary[]> {
  const conversations = await requestJson<ConversationSummaryDto[]>('/api/conversations')
  return conversations.map(mapConversationSummary)
}

export async function createConversation(selectedModel: string | null): Promise<{ conversation: ConversationSummary; events: EventItem[] }> {
  const response = await requestJson<ConversationCreateResponseDto>('/api/conversations', {
    method: 'POST',
    body: JSON.stringify({ selected_model: selectedModel }),
  })
  return {
    conversation: mapConversationSummary(response.conversation),
    events: response.events,
  }
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  const conversation = await requestJson<ConversationDetailDto>(`/api/conversations/${conversationId}`)
  return mapConversationDetail(conversation)
}

export async function getConversationContext(conversationId: string): Promise<ConversationContextStatus> {
  const status = await requestJson<ConversationContextStatusDto>(`/api/conversations/${conversationId}/context`)
  return mapConversationContextStatus(status)
}

export async function appendConversationEvents(conversationId: string, events: EventItem[]): Promise<ConversationDetail> {
  const conversation = await requestJson<ConversationDetailDto>(`/api/conversations/${conversationId}/events`, {
    method: 'POST',
    body: JSON.stringify({ events }),
  })
  return mapConversationDetail(conversation)
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await requestVoid(`/api/conversations/${conversationId}`, {
    method: 'DELETE',
  })
}
