from pathlib import Path


APP_DIR = Path.home() / ".ops-agent"
DB_PATH = APP_DIR / "ops_agent.db"
SETTINGS_PATH = APP_DIR / "settings.json"
TEST_DB_PATH = APP_DIR / "ops_agent.test.db"
WINDOWS_APP_NAME = "Ops Agent"
WSL_TEST_MODE = True
