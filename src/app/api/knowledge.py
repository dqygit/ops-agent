from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from app.api.schemas import (
    KnowledgeAssetRefView,
    KnowledgeCommandView,
    KnowledgeDraftView,
    KnowledgeEntryCreateRequest,
    KnowledgeEntryUpdateRequest,
    KnowledgeEntryView,
    KnowledgeGenerateDraftRequest,
    KnowledgeGenerateDraftResponse,
    KnowledgeReindexResponse,
    KnowledgeSearchResponse,
    KnowledgeSourceConversationView,
    KnowledgeSourceRefView,
)
from app.services.knowledge_factory import get_knowledge_service
from app.services.knowledge_models import (
    KnowledgeAssetRef,
    KnowledgeCommand,
    KnowledgeDraft,
    KnowledgeEntry,
    KnowledgeReindexResult,
    KnowledgeSearchFilters,
    KnowledgeSearchPage,
    KnowledgeSourceConversation,
    KnowledgeSourceRef,
)
from app.services.knowledge_service import KnowledgeConversationNotFoundError, RecoverableKnowledgeServiceError

router = APIRouter()


def _command_to_view(command: KnowledgeCommand) -> KnowledgeCommandView:
    return KnowledgeCommandView(
        command=command.command,
        purpose=command.purpose,
        outcome=command.outcome,
    )


def _asset_to_view(asset: KnowledgeAssetRef) -> KnowledgeAssetRefView:
    return KnowledgeAssetRefView(
        assetId=asset.asset_id,
        label=asset.label,
    )


def _source_to_view(source: KnowledgeSourceRef) -> KnowledgeSourceRefView:
    return KnowledgeSourceRefView(
        conversationId=source.conversation_id,
        eventId=source.event_id,
        eventIndex=source.event_index,
        eventType=source.event_type,
        quote=source.quote,
        relevance=source.relevance,
    )


def _source_conversation_to_view(source: KnowledgeSourceConversation) -> KnowledgeSourceConversationView:
    return KnowledgeSourceConversationView(
        id=source.id,
        title=source.title,
        updatedAt=source.updated_at,
    )


def _draft_to_view(draft: KnowledgeDraft) -> KnowledgeDraftView:
    return KnowledgeDraftView(
        title=draft.title,
        summary=draft.summary,
        problem=draft.problem,
        diagnosis=draft.diagnosis,
        resolution=draft.resolution,
        commands=[_command_to_view(command) for command in draft.commands],
        assets=[_asset_to_view(asset) for asset in draft.assets],
        tags=list(draft.tags),
        sources=[_source_to_view(source) for source in draft.sources],
        redactionWarnings=list(draft.redaction_warnings),
    )


def _entry_to_view(entry: KnowledgeEntry) -> KnowledgeEntryView:
    return KnowledgeEntryView(
        id=entry.id,
        title=entry.title,
        summary=entry.summary,
        problem=entry.problem,
        diagnosis=entry.diagnosis,
        resolution=entry.resolution,
        commands=[_command_to_view(command) for command in entry.commands],
        assets=[_asset_to_view(asset) for asset in entry.assets],
        tags=list(entry.tags),
        sources=[_source_to_view(source) for source in entry.sources],
        sourceConversation=_source_conversation_to_view(entry.source_conversation),
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def _search_page_to_response(page: KnowledgeSearchPage) -> KnowledgeSearchResponse:
    return KnowledgeSearchResponse(
        items=[_entry_to_view(entry) for entry in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


def _reindex_result_to_response(result: KnowledgeReindexResult) -> KnowledgeReindexResponse:
    return KnowledgeReindexResponse(indexed=result.indexed, failed=result.failed)


def _request_to_draft(payload: KnowledgeEntryCreateRequest | KnowledgeEntryUpdateRequest) -> KnowledgeDraft:
    return KnowledgeDraft(
        title=payload.title,
        summary=payload.summary,
        problem=payload.problem,
        diagnosis=payload.diagnosis,
        resolution=payload.resolution,
        commands=[
            KnowledgeCommand(
                command=command.command,
                purpose=command.purpose,
                outcome=command.outcome,
            )
            for command in payload.commands
        ],
        assets=[
            KnowledgeAssetRef(
                assetId=asset.assetId,
                label=asset.label,
            )
            for asset in payload.assets
        ],
        tags=list(payload.tags),
        sources=[
            KnowledgeSourceRef(
                conversationId=source.conversationId,
                eventId=source.eventId,
                eventIndex=source.eventIndex,
                eventType=source.eventType,
                quote=source.quote,
                relevance=source.relevance,
            )
            for source in payload.sources
        ],
        redactionWarnings=list(payload.redactionWarnings),
    )


def _request_to_source_conversation(payload: KnowledgeEntryCreateRequest | KnowledgeEntryUpdateRequest) -> KnowledgeSourceConversation:
    return KnowledgeSourceConversation(
        id=payload.sourceConversationId,
        title=payload.sourceConversationTitle,
        updatedAt=payload.sourceConversationUpdatedAt,
    )


@router.post("/api/knowledge/from-conversation/{conversation_id}", response_model=KnowledgeGenerateDraftResponse)
def generate_knowledge_draft(
    conversation_id: str,
    payload: KnowledgeGenerateDraftRequest,
) -> KnowledgeGenerateDraftResponse:
    service = get_knowledge_service()
    try:
        draft, source_conversation = service.generate_draft_from_conversation(
            conversation_id,
            max_source_events=payload.maxSourceEvents,
            model_name=payload.modelName,
        )
    except KnowledgeConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RecoverableKnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return KnowledgeGenerateDraftResponse(
        draft=_draft_to_view(draft),
        sourceConversation=_source_conversation_to_view(source_conversation),
    )


@router.post("/api/knowledge", response_model=KnowledgeEntryView)
def create_knowledge_entry(payload: KnowledgeEntryCreateRequest) -> KnowledgeEntryView:
    service = get_knowledge_service()
    try:
        entry = service.create_entry(
            _request_to_draft(payload),
            _request_to_source_conversation(payload),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge entry not found") from exc
    except RecoverableKnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _entry_to_view(entry)


@router.get("/api/knowledge", response_model=KnowledgeSearchResponse)
def search_knowledge_entries(
    query: str = "",
    assetId: int | None = None,
    tag: str = "",
    sourceConversationId: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> KnowledgeSearchResponse:
    service = get_knowledge_service()
    try:
        page = service.search(
            KnowledgeSearchFilters(
                query=query,
                assetId=assetId,
                tag=tag,
                sourceConversationId=sourceConversationId,
                limit=limit,
                offset=offset,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge entry not found") from exc
    except RecoverableKnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _search_page_to_response(page)


@router.get("/api/knowledge/{entry_id}", response_model=KnowledgeEntryView)
def get_knowledge_entry(entry_id: str) -> KnowledgeEntryView:
    service = get_knowledge_service()
    try:
        entry = service.get_entry(entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge entry not found") from exc
    return _entry_to_view(entry)


@router.put("/api/knowledge/{entry_id}", response_model=KnowledgeEntryView)
def update_knowledge_entry(entry_id: str, payload: KnowledgeEntryUpdateRequest) -> KnowledgeEntryView:
    service = get_knowledge_service()
    try:
        entry = service.update_entry(
            entry_id,
            _request_to_draft(payload),
            _request_to_source_conversation(payload),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge entry not found") from exc
    except RecoverableKnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _entry_to_view(entry)


@router.delete("/api/knowledge/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_knowledge_entry(entry_id: str) -> Response:
    service = get_knowledge_service()
    try:
        service.get_entry(entry_id)
        service.delete_entry(entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge entry not found") from exc
    except RecoverableKnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/knowledge/reindex", response_model=KnowledgeReindexResponse)
def reindex_knowledge_entries() -> KnowledgeReindexResponse:
    service = get_knowledge_service()
    try:
        result = service.reindex()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge entry not found") from exc
    except RecoverableKnowledgeServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _reindex_result_to_response(result)
