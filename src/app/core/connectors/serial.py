from __future__ import annotations

import serial


class SerialConnector:
    def __init__(
        self,
        *,
        device: str,
        baudrate: int,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: float = 1,
        timeout: float = 0.05,
    ):
        self.device = device
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.connection = None
        self.shell_kind = "serial"

    def open_interactive(self) -> str:
        if self.connection is None:
            self.connection = serial.Serial(
                port=self.device,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
            )
        return "serial terminal connected"

    def read(self) -> str:
        if self.connection is None:
            return ""
        available = self.connection.in_waiting
        if available <= 0:
            return ""
        return self.connection.read(available).decode(errors="ignore")

    def write(self, data: str) -> None:
        if self.connection is None:
            return
        self.connection.write(data.encode("utf-8", errors="ignore"))

    def resize(self, cols: int, rows: int) -> None:
        return None

    def close(self) -> None:
        if self.connection is None:
            return
        self.connection.close()
        self.connection = None
