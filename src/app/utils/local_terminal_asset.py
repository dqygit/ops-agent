from types import SimpleNamespace

from app.shared.enums import AssetType


def build_local_terminal_asset():
    return SimpleNamespace(
        id=0,
        asset_type=AssetType.LOCAL_TERMINAL.value,
        name="local-terminal",
        host="localhost",
        port=0,
        username="",
        auth_type="",
        tags=[],
        vendor="",
        description="default local terminal asset",
        group_id=None,
        ssh_key_id=None,
    )
