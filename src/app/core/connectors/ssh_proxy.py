from dataclasses import dataclass


@dataclass
class SSHProxyConfig:
    asset_id: int
    name: str
    host: str
    port: int
    username: str
    password: str | None = None
    private_key: str | None = None
    passphrase: str | None = None


class SSHProxyConfigurationError(ValueError):
    pass


class SSHProxyAssetNotFoundError(SSHProxyConfigurationError):
    pass


class SSHProxyUnsupportedTargetError(SSHProxyConfigurationError):
    pass


class SSHProxyAuthenticationMaterialError(SSHProxyConfigurationError):
    pass


class SSHProxyConnectionError(ConnectionError):
    pass


class SSHProxyChannelOpenError(ConnectionError):
    pass


class SSHTargetConnectionThroughProxyError(ConnectionError):
    pass


def describe_ssh_proxy_error(error: Exception) -> str:
    if isinstance(error, SSHProxyUnsupportedTargetError):
        return "SSH proxy is supported only for Linux and network device assets in this version."
    if isinstance(error, SSHProxyAssetNotFoundError):
        return "Proxy asset not found. Select another SSH jump asset or clear the proxy setting."
    if isinstance(error, SSHProxyAuthenticationMaterialError):
        return "Proxy asset authentication material is incomplete. Check the JumpServer credential or SSH key."
    if isinstance(
        error,
        (
            SSHProxyConnectionError,
            SSHProxyChannelOpenError,
            SSHTargetConnectionThroughProxyError,
            SSHProxyConfigurationError,
        ),
    ):
        return str(error)
    return str(error)
