from io import StringIO
from typing import Any, cast

from netmiko import ConnectHandler


class NetworkConnector:
    def __init__(self, device_params: dict[str, Any], ssh_params: dict[str, Any] | None = None):
        self.device_params = {"conn_timeout": 15, **device_params}
        self.ssh_params = ssh_params or self._build_ssh_params(device_params)
        self.shell_kind = "network"
        self.connection: Any | None = None
        self.ssh_client: Any | None = None
        self.channel: Any | None = None

    def connect(self) -> None:
        self.connection = ConnectHandler(**self.device_params)

    def run_command(self, command: str) -> str:
        if self.connection is None:
            self.connect()
        connection = self.connection
        assert connection is not None
        return cast(str, connection.send_command(command))

    def open_interactive(self) -> object:
        if self.channel is None:
            self._connect_ssh()
        assert self.channel is not None
        return self.channel

    def read(self) -> str:
        if self.channel is None or not self.channel.recv_ready():
            return ""
        return cast(bytes, self.channel.recv(4096)).decode(errors="ignore")

    def write(self, data: str) -> None:
        if self.channel is None:
            return
        self.channel.send(data.encode("utf-8", errors="ignore"))

    def resize(self, cols: int, rows: int) -> None:
        if self.channel is None:
            return
        try:
            self.channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def close(self) -> None:
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.ssh_client is not None:
            self.ssh_client.close()
            self.ssh_client = None
        if self.connection is not None:
            self.connection.disconnect()
            self.connection = None

    def _connect_ssh(self) -> None:
        import paramiko

        client = paramiko.SSHClient()
        try:
            client.load_system_host_keys()
        except Exception:
            pass
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            "hostname": self.ssh_params.get("host"),
            "port": self.ssh_params.get("port", 22),
            "username": self.ssh_params.get("username"),
            "allow_agent": False,
            "look_for_keys": False,
        }
        private_key = self.ssh_params.get("private_key")
        password = self.ssh_params.get("password")
        passphrase = self.ssh_params.get("passphrase")
        if private_key:
            connect_kwargs["pkey"] = self._load_private_key(str(private_key), str(passphrase) if passphrase else None)
            if passphrase:
                connect_kwargs["passphrase"] = passphrase
            if password is not None:
                connect_kwargs["password"] = password
        elif password is not None:
            connect_kwargs["password"] = password
        else:
            raise ValueError("Network device authentication material is required")
        client.connect(**connect_kwargs)
        self.ssh_client = client
        self.channel = client.invoke_shell(term="xterm-256color")

    def _load_private_key(self, private_key: str, passphrase: str | None) -> object:
        import paramiko

        key_stream = StringIO(private_key.strip())
        key_loaders = [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]
        last_error = None
        for key_loader in key_loaders:
            key_stream.seek(0)
            try:
                return key_loader.from_private_key(key_stream, password=passphrase or None)
            except Exception as exc:
                last_error = exc
        raise ValueError("SSH private key format is invalid or passphrase is incorrect") from last_error

    def _build_ssh_params(self, device_params: dict[str, Any]) -> dict[str, Any]:
        return {
            "host": device_params.get("host"),
            "port": device_params.get("port", 22),
            "username": device_params.get("username"),
            "password": device_params.get("password"),
        }
