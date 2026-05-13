from typing import Any, cast

from netmiko import ConnectHandler


class NetworkConnector:
    def __init__(self, device_params: dict[str, Any]):
        self.device_params = {"conn_timeout": 15, **device_params}
        self.shell_kind = "network"
        self.connection: Any | None = None

    def connect(self) -> None:
        self.connection = ConnectHandler(**self.device_params)

    def run_command(self, command: str) -> str:
        if self.connection is None:
            self.connect()
        connection = self.connection
        assert connection is not None
        return cast(str, connection.send_command(command))

    def open_interactive(self) -> object:
        if self.connection is None:
            self.connect()
        connection = self.connection
        assert connection is not None
        return connection

    def read(self) -> str:
        if self.connection is None:
            return ""
        output = cast(str, self.connection.read_channel())
        return output

    def write(self, data: str) -> None:
        if self.connection is None:
            return
        self.connection.write_channel(data)

    def resize(self, cols: int, rows: int) -> None:
        return None

    def close(self) -> None:
        if self.connection is None:
            return
        self.connection.disconnect()
        self.connection = None
