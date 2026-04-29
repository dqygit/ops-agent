from pydantic import SecretStr

from app.shared.enums import AssetType, ModelProvider, TaskStatus
from app.shared.schemas import ModelConfig, PlanStep, TerminalContextAttachment


class ApprovalEvent(dict):
    def __eq__(self, other):
        if isinstance(other, dict):
            return all(self.get(key) == value for key, value in other.items())
        return super().__eq__(other)


class FakePersistence:
    def __init__(self):
        self.created_tasks = []
        self.created_steps = []
        self.task_updates = []
        self.step_updates = []
        self.approvals = []
        self.approval_details = []
        self.terminal_events = []
        self.model_usages = []
        self.command_executions = []

    def create_task(self, *, session_id: int, run_id: str, asset_id: int, user_input: str, terminal_context, plan_steps):
        self.created_tasks.append(
            {
                "session_id": session_id,
                "run_id": run_id,
                "asset_id": asset_id,
                "user_input": user_input,
                "terminal_context": terminal_context,
                "plan_steps": plan_steps,
            }
        )
        return 101

    def create_steps(self, *, task_id: int, plan_steps):
        self.created_steps.append({"task_id": task_id, "plan_steps": plan_steps})
        return [201 + index for index, _ in enumerate(plan_steps)]

    def update_task_status(self, *, task_id: int, status: str, final_summary: str | None = None):
        self.task_updates.append({"task_id": task_id, "status": status, "final_summary": final_summary})

    def update_step(self, *, step_id: int, status: str, output=None, error_message=None, exit_code=None, started_at=None, finished_at=None):
        self.step_updates.append(
            {
                "step_id": step_id,
                "status": status,
                "output": output,
                "error_message": error_message,
                "exit_code": exit_code,
                "started_at": started_at,
                "finished_at": finished_at,
            }
        )

    def record_approval(self, *, task_id: int, approved: bool, **kwargs):
        self.approvals.append(ApprovalEvent({"task_id": task_id, "approved": approved, **kwargs}))
        self.approval_details.append({"task_id": task_id, "approved": approved, **kwargs})

    def create_command_execution(self, **payload):
        command_execution_id = 301 + len(self.command_executions)
        self.command_executions.append({"id": command_execution_id, **payload})
        return command_execution_id

    def update_command_execution(self, *, command_execution_id: int, **updates):
        self.command_executions.append({"id": command_execution_id, **updates})

    def record_terminal_event(self, *, terminal_session_id: int, event_type: str, metadata=""):
        self.terminal_events.append(
            {
                "terminal_session_id": terminal_session_id,
                "event_type": event_type,
                "metadata": metadata,
            }
        )

    def record_model_usage(
        self,
        *,
        task_id: int,
        provider: str,
        model_name: str,
        base_url_snapshot: str,
        temperature_snapshot: float,
        max_tokens_snapshot: int,
    ):
        self.model_usages.append(
            {
                "task_id": task_id,
                "provider": provider,
                "model_name": model_name,
                "base_url_snapshot": base_url_snapshot,
                "temperature_snapshot": temperature_snapshot,
                "max_tokens_snapshot": max_tokens_snapshot,
            }
        )


class FakePlanner:
    def __call__(self, asset_type, user_input, terminal_context=None, recent_messages=None):
        assert asset_type is AssetType.HUAWEI
        assert user_input == "检查接口状态"
        assert terminal_context is not None
        assert terminal_context.selection_label == "selected interface"
        assert recent_messages == [{"role": "user", "content": "上一轮"}]
        return [
            PlanStep(
                title="Check interface status",
                command="display interface brief",
                reason="selected interface",
                risk_level="low",
            )
        ]


class FakeExecutor:
    def __call__(self, step, *, state=None, emit=None):
        assert state is not None
        assert state["asset_id"] == 1
        if emit is not None:
            emit("GigabitEthernet0/0/1 up")
        return {
            "step_index": 0,
            "title": step.title,
            "command": step.command,
            "exit_code": 0,
            "stdout": "GigabitEthernet0/0/1 up",
            "stderr": "",
        }


class FakeSummarizer:
    def __call__(self, user_input, execution_results, recent_messages=None):
        assert user_input == "检查接口状态"
        assert recent_messages == [{"role": "user", "content": "上一轮"}]
        stdout = execution_results[0]["stdout"]
        stderr = execution_results[0]["stderr"]
        assert stdout == "GigabitEthernet0/0/1 up" or stderr == "permission denied"
        return "接口状态正常"


MODEL_CONFIG = ModelConfig(
    provider=ModelProvider.ANTHROPIC,
    model_name="claude-sonnet-4-6",
    base_url="https://api.anthropic.com",
    api_key=SecretStr("test-key"),
    timeout_seconds=30,
    temperature=0.2,
    max_tokens=1024,
)


class FakeStreamingSummarizer:
    def __call__(self, user_input, execution_results, recent_messages=None):
        assert user_input == "检查接口状态"
        assert execution_results[0]["stdout"] == "GigabitEthernet0/0/1 up"
        assert recent_messages == [{"role": "user", "content": "上一轮"}]
        return iter(["接口", "状态", "正常"])


class FakeFailingExecutor:
    def __call__(self, step, *, state=None, emit=None):
        assert state is not None
        assert state["asset_id"] == 1
        if emit is not None:
            emit("permission denied")
        return {
            "step_index": 0,
            "title": step.title,
            "command": step.command,
            "exit_code": 1,
            "stdout": "",
            "stderr": "permission denied",
        }


def test_agent_runtime_pauses_for_approval_before_execution():
    from app.core.agent.runtime import AgentRuntime

    persistence = FakePersistence()
    runtime = AgentRuntime(
        planner=FakePlanner(),
        step_executor=FakeExecutor(),
        summarizer=FakeSummarizer(),
        persistence=persistence,
        model_config=MODEL_CONFIG,
    )

    result = runtime.start_run(
        conversation_id="conv-1",
        run_id="run-1",
        user_message="检查接口状态",
        asset_type=AssetType.HUAWEI,
        asset_id=1,
        session_id=11,
        model_name="claude-sonnet-4-6",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=1,
            selection_label="selected interface",
            selected_text="GigabitEthernet0/0/1 up",
        ),
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    assert result["task_id"] == 101
    assert result["step_ids"] == [201]
    assert persistence.created_tasks[0]["session_id"] == 11
    assert persistence.created_steps[0]["task_id"] == 101
    assert result["plan_steps"][0].command == "display interface brief"
    assert result["ui_events"][0]["type"] == "assistant_status"
    assert result["ui_events"][1]["type"] == "plan_ready"
    assert result["ui_events"][2]["type"] == "approval_requested"
    assert result["ui_events"][2]["type"] == "approval_requested"


def test_agent_runtime_resumes_after_approval_and_produces_summary():
    from app.core.agent.runtime import AgentRuntime

    persistence = FakePersistence()
    runtime = AgentRuntime(
        planner=FakePlanner(),
        step_executor=FakeExecutor(),
        summarizer=FakeSummarizer(),
        persistence=persistence,
        model_config=MODEL_CONFIG,
    )

    runtime.start_run(
        conversation_id="conv-1",
        run_id="run-2",
        user_message="检查接口状态",
        asset_type=AssetType.HUAWEI,
        asset_id=1,
        session_id=11,
        model_name="claude-sonnet-4-6",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=1,
            selection_label="selected interface",
            selected_text="GigabitEthernet0/0/1 up",
        ),
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    result = runtime.resume_run(run_id="run-2", approved=True)

    assert result["approved"] is True
    assert persistence.approvals == [{"task_id": 101, "approved": True}]
    assert persistence.approval_details[0]["asset_id"] == 1
    assert persistence.approval_details[0]["step_ids"] == [201]
    assert persistence.approval_details[0]["steps"][0].command == "display interface brief"
    assert persistence.task_updates[0]["status"] == TaskStatus.APPROVED.value
    assert persistence.task_updates[1]["status"] == TaskStatus.RUNNING.value
    assert persistence.task_updates[-1] == {
        "task_id": 101,
        "status": TaskStatus.COMPLETED.value,
        "final_summary": "接口状态正常",
    }
    assert persistence.step_updates[0]["status"] == TaskStatus.RUNNING.value
    assert persistence.step_updates[-1]["status"] == TaskStatus.COMPLETED.value
    assert persistence.step_updates[-1]["output"] == "GigabitEthernet0/0/1 up"
    assert persistence.model_usages == [
        {
            "task_id": 101,
            "provider": "anthropic",
            "model_name": "claude-sonnet-4-6",
            "base_url_snapshot": "https://api.anthropic.com",
            "temperature_snapshot": 0.2,
            "max_tokens_snapshot": 1024,
        }
    ]
    assert result["execution_results"][0]["command"] == "display interface brief"
    assert result["assistant_message"] == "接口状态正常"
    assert [event["type"] for event in result["ui_events"]] == [
        "assistant_status",
        "step_started",
        "terminal_output",
        "step_finished",
        "assistant_final",
    ]


def test_agent_runtime_stops_when_plan_is_rejected():
    from app.core.agent.runtime import AgentRuntime

    persistence = FakePersistence()
    runtime = AgentRuntime(
        planner=FakePlanner(),
        step_executor=FakeExecutor(),
        summarizer=FakeSummarizer(),
        persistence=persistence,
        model_config=MODEL_CONFIG,
    )

    runtime.start_run(
        conversation_id="conv-1",
        run_id="run-3",
        user_message="检查接口状态",
        asset_type=AssetType.HUAWEI,
        asset_id=1,
        session_id=11,
        model_name="claude-sonnet-4-6",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=1,
            selection_label="selected interface",
            selected_text="GigabitEthernet0/0/1 up",
        ),
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    result = runtime.resume_run(run_id="run-3", approved=False)

    assert result["approved"] is False
    assert persistence.approvals == [{"task_id": 101, "approved": False}]
    assert persistence.approval_details[0]["asset_id"] == 1
    assert persistence.approval_details[0]["step_ids"] == [201]
    assert persistence.approval_details[0]["steps"][0].command == "display interface brief"
    assert persistence.task_updates == [{"task_id": 101, "status": TaskStatus.REJECTED.value, "final_summary": None}]
    assert persistence.model_usages == []
    assert result["execution_results"] == []
    assert result["assistant_message"] == "任务已取消"
    assert result["ui_events"][-1]["type"] == "assistant_final"


def test_agent_runtime_streams_summary_chunks_before_final_message():
    from app.core.agent.runtime import AgentRuntime

    persistence = FakePersistence()
    runtime = AgentRuntime(
        planner=FakePlanner(),
        step_executor=FakeExecutor(),
        summarizer=FakeStreamingSummarizer(),
        persistence=persistence,
        model_config=MODEL_CONFIG,
    )

    runtime.start_run(
        conversation_id="conv-1",
        run_id="run-4",
        user_message="检查接口状态",
        asset_type=AssetType.HUAWEI,
        asset_id=1,
        session_id=11,
        model_name="claude-sonnet-4-6",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=1,
            selection_label="selected interface",
            selected_text="GigabitEthernet0/0/1 up",
        ),
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    result = runtime.resume_run(run_id="run-4", approved=True)

    assert result["assistant_message"] == "接口状态正常"
    assert [event["type"] for event in result["ui_events"]] == [
        "assistant_status",
        "step_started",
        "terminal_output",
        "step_finished",
        "assistant_status",
        "assistant_chunk",
        "assistant_chunk",
        "assistant_chunk",
        "assistant_final",
    ]
    assert result["ui_events"][-4]["payload"]["chunk"] == "接口"
    assert result["ui_events"][-3]["payload"]["chunk"] == "状态"
    assert result["ui_events"][-2]["payload"]["chunk"] == "正常"
    assert result["ui_events"][-1]["payload"]["message"] == "接口状态正常"
    assert persistence.created_tasks == [
        {
            "session_id": 11,
            "run_id": "run-4",
            "asset_id": 1,
            "user_input": "检查接口状态",
            "terminal_context": TerminalContextAttachment(
                terminal_session_id=1,
                selection_label="selected interface",
                selected_text="GigabitEthernet0/0/1 up",
            ),
            "plan_steps": result["plan_steps"],
        }
    ]
    assert persistence.created_steps == [{"task_id": 101, "plan_steps": result["plan_steps"]}]
    assert persistence.approvals == [{"task_id": 101, "approved": True}]
    assert persistence.approval_details[0]["asset_id"] == 1
    assert persistence.approval_details[0]["step_ids"] == [201]
    assert persistence.approval_details[0]["steps"][0].command == "display interface brief"
    assert persistence.model_usages == [
        {
            "task_id": 101,
            "provider": "anthropic",
            "model_name": "claude-sonnet-4-6",
            "base_url_snapshot": "https://api.anthropic.com",
            "temperature_snapshot": 0.2,
            "max_tokens_snapshot": 1024,
        }
    ]
    assert persistence.task_updates == [
        {"task_id": 101, "status": TaskStatus.APPROVED.value, "final_summary": None},
        {"task_id": 101, "status": TaskStatus.RUNNING.value, "final_summary": None},
        {"task_id": 101, "status": TaskStatus.COMPLETED.value, "final_summary": "接口状态正常"},
    ]
    assert persistence.step_updates[0]["step_id"] == 201
    assert persistence.step_updates[0]["status"] == TaskStatus.RUNNING.value
    assert persistence.step_updates[0]["started_at"] is not None
    assert persistence.step_updates[1]["step_id"] == 201
    assert persistence.step_updates[1]["status"] == TaskStatus.COMPLETED.value
    assert persistence.step_updates[1]["output"] == "GigabitEthernet0/0/1 up"
    assert persistence.step_updates[1]["error_message"] == ""
    assert persistence.step_updates[1]["finished_at"] is not None


def test_agent_runtime_marks_task_failed_when_execution_fails():
    from app.core.agent.runtime import AgentRuntime

    persistence = FakePersistence()
    runtime = AgentRuntime(
        planner=FakePlanner(),
        step_executor=FakeFailingExecutor(),
        summarizer=FakeSummarizer(),
        persistence=persistence,
        model_config=MODEL_CONFIG,
    )

    runtime.start_run(
        conversation_id="conv-1",
        run_id="run-5",
        user_message="检查接口状态",
        asset_type=AssetType.HUAWEI,
        asset_id=1,
        session_id=11,
        model_name="claude-sonnet-4-6",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=1,
            selection_label="selected interface",
            selected_text="GigabitEthernet0/0/1 up",
        ),
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    result = runtime.resume_run(run_id="run-5", approved=True)

    assert result["assistant_message"] == "接口状态正常"
    assert persistence.task_updates[-1] == {
        "task_id": 101,
        "status": TaskStatus.FAILED.value,
        "final_summary": "接口状态正常",
    }
    assert persistence.model_usages == [
        {
            "task_id": 101,
            "provider": "anthropic",
            "model_name": "claude-sonnet-4-6",
            "base_url_snapshot": "https://api.anthropic.com",
            "temperature_snapshot": 0.2,
            "max_tokens_snapshot": 1024,
        }
    ]
    assert persistence.step_updates[-1]["status"] == TaskStatus.FAILED.value
    assert persistence.step_updates[-1]["output"] == ""
    assert persistence.step_updates[-1]["error_message"] == "permission denied"
