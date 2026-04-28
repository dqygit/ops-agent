from app.shared.schemas import TerminalContextAttachment


def build_terminal_context(terminal_session_id: int, selection_label: str, selected_text: str) -> TerminalContextAttachment:
    return TerminalContextAttachment(
        terminal_session_id=terminal_session_id,
        selection_label=selection_label,
        selected_text=selected_text,
    )
