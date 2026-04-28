from app.core.terminal.context_bridge import build_terminal_context
from app.core.terminal.session_manager import TerminalSessionManager


class TerminalService:
    def __init__(self, connector_factory, persistence):
        self._connector_factory = connector_factory
        self._persistence = persistence
        self._sessions = {}

    def open_session(self, asset):
        asset_id = getattr(asset, "id", None)
        if asset_id is None and isinstance(asset, dict):
            asset_id = asset.get("id")
        terminal_session_id = self._persistence.create_session(asset_id or 0)
        try:
            connector = self._connector_factory(asset)
            session_manager = TerminalSessionManager(connector)
            channel = session_manager.open()
        except Exception as exc:
            self._persistence.update_session(
                terminal_session_id,
                status="error",
                last_error=str(exc),
            )
            self._persistence.record_event(terminal_session_id, "error", str(exc))
            return {"terminal_session_id": None, "channel": None, "error": str(exc)}
        self._sessions[terminal_session_id] = session_manager
        self._persistence.record_event(terminal_session_id, "connected", "")
        return {"terminal_session_id": terminal_session_id, "channel": channel, "error": ""}

    def close_session(self, terminal_session_id: int) -> bool:
        session_manager = self._sessions.pop(terminal_session_id, None)
        if session_manager is None:
            return False
        session_manager.close()
        self._persistence.update_session(terminal_session_id, status="disconnected", ended=True)
        self._persistence.record_event(terminal_session_id, "disconnected", "")
        return True

    def get_session(self, terminal_session_id: int):
        return self._sessions.get(terminal_session_id)

    def attach_context(self, terminal_session_id: int, selection_label: str, selected_text: str):
        attachment = build_terminal_context(terminal_session_id, selection_label, selected_text)
        self._persistence.record_event(
            terminal_session_id,
            "context_attached",
            {"selection_label": selection_label, "selected_text": selected_text},
        )
        return attachment
