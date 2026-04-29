import pytest

from app.core.connectors.server import ServerConnector
from app.services.terminal_service import TerminalService


class FakeConnector:
    def __init__(self):
        self.closed = False
        self.output = ""
        self.writes = []
        self.resizes = []

    def open_interactive(self):
        return "connected"

    def read(self):
        output = self.output
        self.output = ""
        return output

    def write(self, data):
        self.writes.append(data)
        self.output = f"echo: {data}"

    def resize(self, cols, rows):
        self.resizes.append((cols, rows))

    def close(self):
        self.closed = True


class FakePersistence:
    def __init__(self):
        self.next_id = 1
        self.sessions = []
        self.updates = []
        self.events = []

    def create_session(self, asset_id):
        terminal_session_id = self.next_id
        self.next_id += 1
        self.sessions.append({"id": terminal_session_id, "asset_id": asset_id})
        return terminal_session_id

    def update_session(self, terminal_session_id, **kwargs):
        self.updates.append({"terminal_session_id": terminal_session_id, **kwargs})

    def record_event(self, terminal_session_id, event_type, metadata=""):
        self.events.append(
            {
                "terminal_session_id": terminal_session_id,
                "event_type": event_type,
                "metadata": metadata,
            }
        )


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = list(messages)
        self.accepted = False
        self.closed = None
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000):
        self.closed = code

    async def receive_json(self):
        if not self.messages:
            return {"type": "close"}
        return self.messages.pop(0)

    async def send_json(self, message):
        self.sent.append(message)


def test_terminal_service_closes_connector_when_open_fails():
    class FailingConnector(FakeConnector):
        def open_interactive(self):
            raise RuntimeError("open failed")

    connector = FailingConnector()
    persistence = FakePersistence()
    service = TerminalService(connector_factory=lambda _asset: connector, persistence=persistence)

    result = service.open_session({"id": 10})

    assert result == {"terminal_session_id": None, "channel": None, "error": "open failed"}
    assert connector.closed is True
    assert persistence.updates == [{"terminal_session_id": 1, "status": "failed", "last_error": "open failed"}]
    assert persistence.events[-1] == {"terminal_session_id": 1, "event_type": "error", "metadata": "open failed"}


def test_terminal_service_creates_one_connector_per_session_and_closes_only_requested_session():
    connectors = []
    persistence = FakePersistence()

    def connector_factory(_asset):
        connector = FakeConnector()
        connectors.append(connector)
        return connector

    service = TerminalService(connector_factory=connector_factory, persistence=persistence)

    first = service.open_session({"id": 10})
    second = service.open_session({"id": 10})

    assert first == {"terminal_session_id": 1, "channel": "terminal connected", "error": ""}
    assert second == {"terminal_session_id": 2, "channel": "terminal connected", "error": ""}
    assert len(connectors) == 2

    assert service.close_session(1) is True
    assert connectors[0].closed is True
    assert connectors[1].closed is False
    assert service.get_session(2) is not None


@pytest.mark.anyio
async def test_terminal_service_stream_writes_resizes_outputs_and_closes_session():
    connector = FakeConnector()
    persistence = FakePersistence()
    service = TerminalService(connector_factory=lambda _asset: connector, persistence=persistence)
    result = service.open_session({"id": 20})
    websocket = FakeWebSocket(
        [
            {"type": "input", "data": "pwd\r"},
            {"type": "resize", "cols": 120, "rows": 40},
            {"type": "close"},
        ]
    )

    await service.stream_session(result["terminal_session_id"], websocket)

    assert websocket.accepted is True
    assert connector.writes == ["pwd\r"]
    assert connector.resizes == [(120, 40)]
    assert {"type": "output", "data": "echo: pwd\r"} in websocket.sent
    assert {"type": "closed"} in websocket.sent
    assert connector.closed is True
    assert service.get_session(result["terminal_session_id"]) is None
    assert any(event["event_type"] == "disconnected" for event in persistence.events)


@pytest.mark.anyio
async def test_terminal_service_stream_rejects_missing_session():
    service = TerminalService(connector_factory=lambda _asset: FakeConnector(), persistence=FakePersistence())
    websocket = FakeWebSocket([])

    await service.stream_session(999, websocket)

    assert websocket.accepted is False
    assert websocket.closed == 1008


def test_server_connector_interactive_channel_reads_writes_and_resizes():
    class FakeChannel:
        def __init__(self):
            self.sent = []
            self.resizes = []

        def recv_ready(self):
            return True

        def recv(self, size):
            return b"hello"

        def send(self, data):
            self.sent.append(data)

        def resize_pty(self, *, width, height):
            self.resizes.append((width, height))

    connector = ServerConnector(host="example.test", port=22, username="ops", password="redacted")
    connector.channel = FakeChannel()

    assert connector.read() == "hello"
    connector.write("pwd\r")
    connector.resize(120, 40)

    assert connector.channel.sent == ["pwd\r"]
    assert connector.channel.resizes == [(120, 40)]
