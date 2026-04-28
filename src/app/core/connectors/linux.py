from app.core.connectors.base import Connector


class LinuxConnector(Connector):
    def __init__(self, client):
        self._client = client

    def run_command(self, command: str) -> str:
        return self._client.run(command)

    def open_interactive(self) -> object:
        return self._client.open_terminal()

    def close(self) -> None:
        self._client.close()
