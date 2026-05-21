from __future__ import annotations

import os
from pathlib import Path

from app.services.conversation_service import ConversationService
from app.services.knowledge_document_store import KnowledgeDocumentStore
from app.services.knowledge_search_index import KnowledgeSearchIndex
from app.services.knowledge_service import KnowledgeService
from app.services.model_service import ModelService
from app.services.redaction_service import RedactionService


def _conversation_base_dir() -> Path:
    configured = os.getenv("OPS_AGENT_CONVERSATIONS_DIR", "")
    return Path(configured) if configured else Path.cwd() / ".ops-agent" / "conversations"



def _knowledge_base_dir() -> Path:
    configured = os.getenv("OPS_AGENT_KNOWLEDGE_DIR", "")
    return Path(configured) if configured else Path.cwd() / ".ops-agent" / "knowledge"



def get_knowledge_service() -> KnowledgeService:
    conversation_base_dir = _conversation_base_dir()
    knowledge_base_dir = _knowledge_base_dir()

    return KnowledgeService(
        conversation_service=ConversationService(
            base_dir=conversation_base_dir,
            model_service=ModelService(),
        ),
        model_service=ModelService(),
        redaction_service=RedactionService(),
        document_store=KnowledgeDocumentStore(knowledge_base_dir),
        search_index=KnowledgeSearchIndex(knowledge_base_dir / "index.sqlite"),
    )
