from app.shared.schemas import TerminalContextAttachment


def build_terminal_context(terminal_id: str, selection_label: str, selected_text: str) -> TerminalContextAttachment:
    return TerminalContextAttachment(
        terminal_id=terminal_id,
        selection_label=selection_label,
        selected_text=selected_text,
    )
