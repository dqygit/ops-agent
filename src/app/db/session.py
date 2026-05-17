from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.shared.config import APP_DIR, DB_PATH


APP_DIR.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_model_usage_columns()


def _ensure_model_usage_columns() -> None:
    inspector = inspect(engine)
    if "model_usages" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("model_usages")}
    statements = {
        "runtime_id": "ALTER TABLE model_usages ADD COLUMN runtime_id VARCHAR NOT NULL DEFAULT ''",
        "conversation_id": "ALTER TABLE model_usages ADD COLUMN conversation_id VARCHAR NOT NULL DEFAULT ''",
        "input_tokens": "ALTER TABLE model_usages ADD COLUMN input_tokens INTEGER NOT NULL DEFAULT 0",
        "output_tokens": "ALTER TABLE model_usages ADD COLUMN output_tokens INTEGER NOT NULL DEFAULT 0",
        "cache_creation_input_tokens": "ALTER TABLE model_usages ADD COLUMN cache_creation_input_tokens INTEGER NOT NULL DEFAULT 0",
        "cache_read_input_tokens": "ALTER TABLE model_usages ADD COLUMN cache_read_input_tokens INTEGER NOT NULL DEFAULT 0",
        "total_tokens": "ALTER TABLE model_usages ADD COLUMN total_tokens INTEGER NOT NULL DEFAULT 0",
        "call_kind": "ALTER TABLE model_usages ADD COLUMN call_kind VARCHAR NOT NULL DEFAULT 'agent'",
    }
    with engine.begin() as connection:
        if "task_id" in existing:
            nullable = next((column.get("nullable", True) for column in inspector.get_columns("model_usages") if column["name"] == "task_id"), True)
            if nullable is False:
                connection.execute(text("ALTER TABLE model_usages RENAME TO model_usages_legacy"))
                SQLModel.metadata.create_all(engine)
                connection.execute(text("""
                    INSERT INTO model_usages (
                        task_id, model_config_id, provider, model_name, base_url_snapshot,
                        temperature_snapshot, max_tokens_snapshot, created_at
                    )
                    SELECT task_id, model_config_id, provider, model_name, base_url_snapshot,
                        temperature_snapshot, max_tokens_snapshot, created_at
                    FROM model_usages_legacy
                """))
                connection.execute(text("DROP TABLE model_usages_legacy"))
                return
        for column_name, statement in statements.items():
            if column_name not in existing:
                connection.execute(text(statement))


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
