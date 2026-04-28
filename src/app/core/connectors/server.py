import paramiko


class ServerConnector:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client: paramiko.SSHClient | None = None
        self.channel = None

    def connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )
        self.client = client

    def run_command(self, command: str) -> str:
        if self.client is None:
            self.connect()
        assert self.client is not None
        _, stdout, _ = self.client.exec_command(command)
        return stdout.read().decode()

    def open_interactive(self) -> object:
        if self.client is None:
            self.connect()
        assert self.client is not None
        self.channel = self.client.invoke_shell()
        return self.channel

    def close(self) -> None:
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.client is not None:
            self.client.close()
            self.client = None
