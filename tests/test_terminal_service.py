from sqlmodel import Session, SQLModel, create_engine, select
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from app.db.models import TerminalEvent, TerminalSession
from app.db.repositories import create_terminal_event, create_terminal_session, update_terminal_session
from app.services.terminal_service import TerminalService
from app.ui.terminal_panel import TerminalPanel


class FakePersistence:
    def __init__(self):
        self.next_session_id = 1
        self.sessions = []
        self.session_updates = []
        self.events = []

    def create_session(self, asset_id: int) -> int:
        session_id = self.next_session_id
        self.next_session_id += 1
        self.sessions.append({"id": session_id, "asset_id": asset_id})
        return session_id

    def update_session(self, terminal_session_id: int, *, status: str | None = None, last_error: str | None = None, ended: bool = False):
        self.session_updates.append(
            {
                "terminal_session_id": terminal_session_id,
                "status": status,
                "last_error": last_error,
                "ended": ended,
            }
        )

    def record_event(self, terminal_session_id: int, event_type: str, metadata=""):
        self.events.append((terminal_session_id, event_type, metadata))


class DbPersistence:
    def __init__(self, engine):
        self._engine = engine

    def create_session(self, asset_id: int) -> int:
        with Session(self._engine) as session:
            row = create_terminal_session(session, asset_id)
            return row.id or 0

    def update_session(self, terminal_session_id: int, *, status: str | None = None, last_error: str | None = None, ended: bool = False):
        from datetime import UTC, datetime

        with Session(self._engine) as session:
            update_terminal_session(
                session,
                terminal_session_id,
                status=status,
                last_error=last_error,
                ended_at=datetime.now(UTC) if ended else None,
            )

    def record_event(self, terminal_session_id: int, event_type: str, metadata=""):
        with Session(self._engine) as session:
            create_terminal_event(session, terminal_session_id, event_type, metadata)


class FakeConnector:
    def __init__(self):
        self.close_calls = 0

    def open_interactive(self):
        return "channel-1"

    def close(self):
        self.close_calls += 1
        return None


class FailingConnector:
    def open_interactive(self):
        raise RuntimeError("credential missing")

    def close(self):
        return None


def test_terminal_service_records_connection_and_context_attachment_events():
    persistence = FakePersistence()
    service = TerminalService(
        connector_factory=lambda _asset: FakeConnector(),
        persistence=persistence,
    )

    session = service.open_session(asset={"id": 3, "asset_type": "linux"})
    attachment = service.attach_context(
        terminal_session_id=session["terminal_session_id"],
        selection_label="selected route block",
        selected_text="default via 10.0.0.1",
    )

    assert session["channel"] == "channel-1"
    assert attachment.selection_label == "selected route block"
    assert persistence.events[0][1] == "connected"
    assert persistence.events[1][1] == "context_attached"


def test_terminal_service_tracks_and_closes_open_sessions():
    persistence = FakePersistence()
    connector = FakeConnector()
    service = TerminalService(
        connector_factory=lambda _asset: connector,
        persistence=persistence,
    )

    session = service.open_session(asset={"id": 3, "asset_type": "linux"})
    session_manager = service.get_session(session["terminal_session_id"])

    assert session_manager is not None
    assert session_manager.is_open is True
    assert service.close_session(session["terminal_session_id"]) is True
    assert service.get_session(session["terminal_session_id"]) is None
    assert connector.close_calls == 1
    assert persistence.events[-1][1] == "disconnected"
    assert persistence.session_updates[-1]["status"] == "disconnected"


def test_terminal_service_ignores_unknown_session_close():
    service = TerminalService(
        connector_factory=lambda _asset: FakeConnector(),
        persistence=FakePersistence(),
    )

    assert service.close_session(999) is False


def test_terminal_service_returns_error_when_connection_fails():
    persistence = FakePersistence()
    service = TerminalService(
        connector_factory=lambda _asset: FailingConnector(),
        persistence=persistence,
    )

    session = service.open_session(asset={"id": 3, "asset_type": "linux"})

    assert session["terminal_session_id"] is None
    assert session["channel"] is None
    assert session["error"] == "credential missing"
    assert persistence.events[-1][1] == "error"
    assert persistence.session_updates[-1]["status"] == "error"



def test_terminal_service_persists_sessions_and_events_to_database():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    service = TerminalService(
        connector_factory=lambda _asset: FakeConnector(),
        persistence=DbPersistence(engine),
    )

    session = service.open_session(asset={"id": 3, "asset_type": "linux"})
    service.attach_context(
        terminal_session_id=session["terminal_session_id"],
        selection_label="selected route block",
        selected_text="default via 10.0.0.1",
    )
    service.close_session(session["terminal_session_id"])

    with Session(engine) as db_session:
        terminal_session = db_session.exec(select(TerminalSession)).one()
        terminal_events = list(db_session.exec(select(TerminalEvent)).all())

    terminal_events.sort(key=lambda event: event.id or 0)
    assert terminal_session.asset_id == 3
    assert terminal_session.status == "disconnected"
    assert terminal_session.ended_at is not None
    assert [event.event_type for event in terminal_events] == ["connected", "context_attached", "disconnected"]
    assert "selected route block" in terminal_events[1].event_data



def test_terminal_panel_attaches_selected_text_through_terminal_service():
    app = QApplication.instance() or QApplication([])
    persistence = FakePersistence()
    attachments = []
    service = TerminalService(
        connector_factory=lambda _asset: FakeConnector(),
        persistence=persistence,
    )
    panel = TerminalPanel()
    panel.bind_terminal_service(service)
    panel.bind_context_attached_listener(lambda attachment: attachments.append(attachment))
    panel.set_asset_context({"id": 3, "name": "core-router", "host": "10.0.0.10", "port": 22})

    cursor = panel.terminal_view.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    panel.terminal_view.setTextCursor(cursor)
    attachment = panel.attach_selected_context("selected terminal output")

    assert app is not None
    assert attachment is not None
    assert attachment.selection_label == "selected terminal output"
    assert attachment.selected_text == "channel-1"
    assert attachments[-1].selected_text == "channel-1"
    assert persistence.events[-1][1] == "context_attached"
