class TerminalSessionManager:
    def __init__(self, connector):
        self._connector = connector
        self._channel = None
        self._is_open = False

    @property
    def channel(self):
        return self._channel

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open(self):
        if self._is_open:
            return self._channel
        self._channel = self._connector.open_interactive()
        self._is_open = True
        return self._channel

    def read(self):
        return self._connector.read()

    def write(self, data: str) -> None:
        self._connector.write(data)

    def resize(self, cols: int, rows: int) -> None:
        self._connector.resize(cols, rows)

    def close(self) -> None:
        if not self._is_open:
            return
        self._connector.close()
        self._channel = None
        self._is_open = False
