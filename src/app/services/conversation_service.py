from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4


@dataclass
class ConversationSummary:
    id: str
    title: str
    selected_model: str | None
    created_at: str
    updated_at: str
    event_count: int
    last_event_kind: str | None


@dataclass
class ConversationDetail:
    id: str
    title: str
    selected_model: str | None
    created_at: str
    updated_at: str
    event_count: int
    last_event_kind: str | None
    events: list[dict]


class ConversationService:
    def __init__(self, base_dir: Path, model_service=None):
        self._base_dir = Path(base_dir)
        self._model_service = model_service

    def create_conversation(self, selected_model: str | None) -> ConversationSummary:
        conversation_id = f"conv_{uuid4().hex}"
        timestamp = self._utc_now()
        detail = ConversationDetail(
            id=conversation_id,
            title="New",
            selected_model=selected_model,
            created_at=timestamp,
            updated_at=timestamp,
            event_count=0,
            last_event_kind=None,
            events=[],
        )
        self._ensure_base_dir()
        self._write_detail(detail)
        summaries = self.list_conversations()
        summaries.append(self._to_summary(detail))
        self._write_index(summaries)
        return self._to_summary(detail)

    def list_conversations(self) -> list[ConversationSummary]:
        index_path = self._index_path()
        if not index_path.exists():
            return []
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        summaries = [ConversationSummary(**item) for item in payload]
        return self._sort_summaries(summaries)

    def get_conversation(self, conversation_id: str) -> ConversationDetail:
        payload = json.loads(self._detail_path(conversation_id).read_text(encoding="utf-8"))
        return ConversationDetail(**payload)

    def append_events(self, conversation_id: str, events: list[dict]) -> ConversationDetail:
        detail = self.get_conversation(conversation_id)
        had_user_event = any(event.get("kind") == "user" for event in detail.events)
        detail.events.extend(events)
        detail.event_count = len(detail.events)
        detail.last_event_kind = detail.events[-1].get("kind") if detail.events else None
        detail.updated_at = self._utc_now()

        if not had_user_event:
            first_user_text = next(
                (
                    event.get("text")
                    for event in events
                    if event.get("kind") == "user" and isinstance(event.get("text"), str)
                ),
                None,
            )
            if first_user_text:
                generated_title = self._generate_title(first_user_text, detail.selected_model)
                if generated_title:
                    detail.title = generated_title

        self._write_detail(detail)
        summaries = [item for item in self.list_conversations() if item.id != conversation_id]
        summaries.append(self._to_summary(detail))
        self._write_index(summaries)
        return detail

    def delete_conversation(self, conversation_id: str) -> None:
        detail_path = self._detail_path(conversation_id)
        if not detail_path.exists():
            raise FileNotFoundError(conversation_id)
        detail_path.unlink()
        summaries = [item for item in self.list_conversations() if item.id != conversation_id]
        self._write_index(summaries)

    def _generate_title(self, prompt: str, model_name: str | None) -> str | None:
        if self._model_service is None:
            return None
        generator = getattr(self._model_service, "generate_conversation_title", None)
        if generator is None:
            return None
        try:
            title = generator(prompt, model_name=model_name)
        except Exception:
            return None
        if not isinstance(title, str):
            return None
        title = title.strip()
        return title or None

    def _to_summary(self, detail: ConversationDetail) -> ConversationSummary:
        return ConversationSummary(
            id=detail.id,
            title=detail.title,
            selected_model=detail.selected_model,
            created_at=detail.created_at,
            updated_at=detail.updated_at,
            event_count=detail.event_count,
            last_event_kind=detail.last_event_kind,
        )

    def _ensure_base_dir(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _index_path(self) -> Path:
        return self._base_dir / "index.json"

    def _detail_path(self, conversation_id: str) -> Path:
        return self._base_dir / f"{conversation_id}.json"

    def _write_detail(self, detail: ConversationDetail) -> None:
        self._write_json(self._detail_path(detail.id), asdict(detail))

    def _write_index(self, summaries: list[ConversationSummary]) -> None:
        ordered = self._sort_summaries(summaries)
        self._write_json(self._index_path(), [asdict(item) for item in ordered])

    def _sort_summaries(self, summaries: list[ConversationSummary]) -> list[ConversationSummary]:
        return sorted(summaries, key=lambda item: item.updated_at, reverse=True)

    def _write_json(self, path: Path, payload: dict | list) -> None:
        self._ensure_base_dir()
        with NamedTemporaryFile("w", encoding="utf-8", dir=self._base_dir, delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def _utc_now(self) -> str:
        return datetime.now(UTC).isoformat()
