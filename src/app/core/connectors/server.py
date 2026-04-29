class ServerConnector:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None
        self.channel = None

    def connect(self) -> None:
        import paramiko

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
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

    def read(self) -> str:
        if self.channel is None or not self.channel.recv_ready():
            return ""
        return self.channel.recv(4096).decode(errors="ignore")

    def write(self, data: str) -> None:
        if self.channel is not None:
            self.channel.send(data)

    def resize(self, cols: int, rows: int) -> None:
        if self.channel is not None:
            self.channel.resize_pty(width=cols, height=rows)

    def close(self) -> None:
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.client is not None:
            self.client.close()
            self.client = None
