from io import StringIO

from app.core.connectors.network import NetworkConnector
from app.core.connectors.local_pty import LocalPtyConnector
from app.core.connectors.serial import SerialConnector


class ServerConnector:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str | None = None,
        private_key: str | None = None,
        passphrase: str | None = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.passphrase = passphrase
        self.shell_kind = "posix"
        self.client = None
        self.channel = None

    def _load_private_key(self):
        import paramiko

        if not self.private_key:
            return None

        key_text = self.private_key.strip()
        key_stream = StringIO(key_text)
        key_loaders = [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]
        last_error = None
        for key_loader in key_loaders:
            key_stream.seek(0)
            try:
                return key_loader.from_private_key(key_stream, password=self.passphrase or None)
            except Exception as exc:  # noqa: PERF203
                last_error = exc
        raise ValueError("SSH private key format is invalid or passphrase is incorrect") from last_error

    def connect(self) -> None:
        import paramiko

        client = paramiko.SSHClient()
        # Ensure we don't strictly require system host keys for now in this agentic context
        # but try to load them if available
        try:
            client.load_system_host_keys()
        except Exception:
            pass
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
        }
        if self.private_key:
            connect_kwargs["pkey"] = self._load_private_key()
        elif self.password is not None:
            connect_kwargs["password"] = self.password
        else:
            raise ValueError("SSH authentication material is required")
        client.connect(**connect_kwargs)
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
        self.channel = self.client.invoke_shell(term="xterm-256color")
        return self.channel

    def read(self) -> str:
        if self.channel is None or not self.channel.recv_ready():
            return ""
        return self.channel.recv(4096).decode(errors="ignore")

    def write(self, data: str) -> None:
        if self.channel is not None:
            try:
                self.channel.send(data.encode('utf-8'))
            except Exception:
                pass

    def resize(self, cols: int, rows: int) -> None:
        if self.channel is not None:
            try:
                self.channel.resize_pty(width=cols, height=rows)
            except Exception:
                pass

    def close(self) -> None:
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.client is not None:
            self.client.close()
            self.client = None


def connector_factory(asset):
    from sqlmodel import Session

    from app.db.session import engine
    from app.services.asset_service import get_asset_credential_record
    from app.services.credential_service import CredentialService
    from app.services.secret_key import get_ops_agent_secret_key
    from app.services.ssh_key_service import get_ssh_key_record

    credential_service = CredentialService(secret_key=get_ops_agent_secret_key())
    asset_id = getattr(asset, "id", None)
    asset_type = getattr(asset, "asset_type", "")
    auth_type = getattr(asset, "auth_type", "")
    ssh_key_id = getattr(asset, "ssh_key_id", None)

    if asset_type == "local_terminal":
        return LocalPtyConnector()

    if asset_type == "serial":
        serial_tags = {
            key: value
            for tag in getattr(asset, "tags", [])
            if ":" in tag
            for key, value in [tag.split(":", 1)]
        }
        parity_mapping = {
            "none": "N",
            "odd": "O",
            "even": "E",
        }
        try:
            bytesize = int(serial_tags.get("data-bits", "8"))
            stopbits = float(serial_tags.get("stop-bits", "1"))
        except ValueError as exc:
            raise ValueError("Invalid serial tag configuration") from exc
        parity = parity_mapping.get(serial_tags.get("parity", "none"), "N")
        return SerialConnector(
            device=getattr(asset, "host"),
            baudrate=int(getattr(asset, "port") or 9600),
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
        )

    password = None
    private_key = None
    passphrase = None

    with Session(engine) as session:
        if auth_type == "password":
            credential = get_asset_credential_record(session, asset_id)
            if credential is None:
                raise ValueError("Password credential is required for password auth")
            password = credential_service.decrypt_secret(credential.encrypted_blob)
        elif auth_type in {"key", "password_and_key"}:
            if ssh_key_id is None:
                raise ValueError("SSH key is required for key auth")
            ssh_key = get_ssh_key_record(session, ssh_key_id)
            if ssh_key is None:
                raise ValueError("SSH key not found")
            private_key = credential_service.decrypt_secret(ssh_key.encrypted_private_key)
            if ssh_key.encrypted_passphrase:
                passphrase = credential_service.decrypt_secret(ssh_key.encrypted_passphrase)
        else:
            credential = get_asset_credential_record(session, asset_id)
            if credential is not None:
                password = credential_service.decrypt_secret(credential.encrypted_blob)

    if asset_type in {"network", "cisco", "huawei", "juniper", "h3c"}:
        device_type_mapping = {
            "network": "cisco_ios",
            "cisco": "cisco_ios",
            "huawei": "huawei",
            "h3c": "huawei",
            "juniper": "juniper",
        }
        device_type = device_type_mapping.get(asset_type)
        if device_type is None:
            raise ValueError(f"Unsupported network asset type: {asset_type}")

        device_params = {
            "device_type": device_type,
            "host": getattr(asset, "host"),
            "port": getattr(asset, "port"),
            "username": getattr(asset, "username"),
        }
        if private_key:
            device_params["use_keys"] = True
            device_params["key_file"] = None
            device_params["pkey"] = ServerConnector(
                host=getattr(asset, "host"),
                port=getattr(asset, "port"),
                username=getattr(asset, "username"),
                private_key=private_key,
                passphrase=passphrase,
            )._load_private_key()
            if passphrase:
                device_params["passphrase"] = passphrase
        elif password is not None:
            device_params["password"] = password
        else:
            raise ValueError("Network device authentication material is required")
        return NetworkConnector(device_params)

    return ServerConnector(
        host=getattr(asset, "host"),
        port=getattr(asset, "port"),
        username=getattr(asset, "username"),
        password=password,
        private_key=private_key,
        passphrase=passphrase,
    )
