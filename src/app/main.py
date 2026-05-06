
import os
from importlib import import_module
from app.api import app
from app.shared.config import APP_DIR

def main() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    host = os.environ.get("OPS_AGENT_HOST", "127.0.0.1")
    port = int(os.environ.get("OPS_AGENT_PORT", "8000"))
    import_module("uvicorn").run(app, host=host, port=port)

if __name__ == "__main__":
    main()
