import os


def get_ops_agent_secret_key() -> str:
    secret_key = os.environ.get("OPS_AGENT_SECRET_KEY","wVLhNVnD@e08vx#D")
    if secret_key:
        return secret_key
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("OPS_AGENT_ENV") in {"dev", "test"}:
        return "dev-secret-key"
    raise RuntimeError("OPS_AGENT_SECRET_KEY must be set")
