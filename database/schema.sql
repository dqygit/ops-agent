PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS asset_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    ssh_key_id INTEGER,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('linux', 'local_terminal', 'huawei', 'network', 'cisco', 'juniper', 'h3c')),
    vendor TEXT NOT NULL DEFAULT '',
    host TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 22 CHECK (port > 0 AND port <= 65535),
    username TEXT NOT NULL,
    auth_type TEXT NOT NULL DEFAULT '' CHECK (auth_type IN ('', 'password', 'key', 'password_and_key')),
    tags TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES asset_groups(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ssh_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    public_key TEXT NOT NULL DEFAULT '',
    private_key_encryption_version TEXT NOT NULL,
    encrypted_private_key TEXT NOT NULL,
    passphrase_encryption_version TEXT,
    encrypted_passphrase TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL UNIQUE,
    encryption_version TEXT NOT NULL,
    encrypted_blob TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS model_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('anthropic', 'openai_compatible', 'qwen', 'bigmodel', 'kimi', 'minimax', 'deepseek', 'azure_openai', 'amazon_bedrock', 'openrouter', 'cloudflare', 'github_models', 'siliconflow', 'openai_responses', 'google_gemini')),
    base_url TEXT NOT NULL,
    api_key_encryption_version TEXT NOT NULL,
    encrypted_api_key TEXT NOT NULL,
    model_name TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    timeout_seconds INTEGER NOT NULL DEFAULT 30 CHECK (timeout_seconds > 0),
    temperature REAL NOT NULL DEFAULT 0.2,
    max_tokens INTEGER NOT NULL DEFAULT 1024 CHECK (max_tokens > 0),
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_model_configs_single_default
ON model_configs(is_default)
WHERE is_default = 1;

CREATE TABLE IF NOT EXISTS assistant_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    parent_task_id INTEGER,
    run_id TEXT NOT NULL UNIQUE,
    asset_id INTEGER NOT NULL,
    terminal_id TEXT,
    user_input TEXT NOT NULL,
    attached_terminal_context TEXT NOT NULL DEFAULT '',
    task_type TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
    status TEXT NOT NULL CHECK (status IN ('draft', 'pending_approval', 'approved', 'rejected', 'running', 'completed', 'failed', 'stopped')),
    final_summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES assistant_messages(conversation_id)
);

CREATE TABLE IF NOT EXISTS task_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    title TEXT NOT NULL,
    command TEXT NOT NULL,
    working_directory TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL,
    expected_output TEXT NOT NULL DEFAULT '',
    risk_level TEXT NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'pending_approval', 'approved', 'rejected', 'running', 'completed', 'failed', 'skipped')),
    output TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    exit_code INTEGER,
    started_at TEXT,
    finished_at TEXT,
    FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE,
    UNIQUE (task_id, step_order)
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    step_id INTEGER,
    asset_id INTEGER NOT NULL,
    terminal_id TEXT,
    command TEXT NOT NULL,
    working_directory TEXT NOT NULL DEFAULT '',
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
    llm_explanation TEXT NOT NULL DEFAULT '',
    expected_output TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'auto_approved')),
    operator TEXT NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES task_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS command_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    step_id INTEGER NOT NULL,
    approval_id INTEGER,
    asset_id INTEGER NOT NULL,
    terminal_id TEXT NOT NULL,
    command TEXT NOT NULL,
    working_directory TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    output TEXT NOT NULL DEFAULT '',
    error_output TEXT NOT NULL DEFAULT '',
    exit_code INTEGER,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES task_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (approval_id) REFERENCES approvals(id) ON DELETE SET NULL,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS auto_approval_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT '',
    asset_tags TEXT NOT NULL DEFAULT '',
    command_name TEXT NOT NULL DEFAULT '',
    command_pattern TEXT NOT NULL DEFAULT '',
    max_risk_level TEXT NOT NULL DEFAULT 'low' CHECK (max_risk_level IN ('low', 'medium', 'high')),
    readonly_only INTEGER NOT NULL DEFAULT 1 CHECK (readonly_only IN (0, 1)),
    max_duration_seconds INTEGER NOT NULL DEFAULT 30 CHECK (max_duration_seconds > 0),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auto_approval_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    approval_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    step_id INTEGER,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES auto_approval_rules(id) ON DELETE CASCADE,
    FOREIGN KEY (approval_id) REFERENCES approvals(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES task_steps(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS model_usages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    model_config_id INTEGER,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    base_url_snapshot TEXT NOT NULL,
    temperature_snapshot REAL NOT NULL,
    max_tokens_snapshot INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (model_config_id) REFERENCES model_configs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    asset_id INTEGER,
    conversation_id TEXT,
    task_id INTEGER,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE SET NULL,
    FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS ix_assets_group_id ON assets(group_id);
CREATE INDEX IF NOT EXISTS ix_assistant_messages_conversation_id ON assistant_messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_agent_tasks_conversation_id ON agent_tasks(conversation_id);
CREATE INDEX IF NOT EXISTS ix_agent_tasks_parent_task_id ON agent_tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS ix_task_steps_task_id ON task_steps(task_id);
CREATE INDEX IF NOT EXISTS ix_approvals_task_id ON approvals(task_id);
CREATE INDEX IF NOT EXISTS ix_approvals_step_id ON approvals(step_id);
CREATE INDEX IF NOT EXISTS ix_command_executions_step_id ON command_executions(step_id);
CREATE INDEX IF NOT EXISTS ix_auto_approval_rules_conversation_id ON auto_approval_rules(conversation_id);
CREATE INDEX IF NOT EXISTS ix_model_usages_task_id ON model_usages(task_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_asset_id ON audit_logs(asset_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
