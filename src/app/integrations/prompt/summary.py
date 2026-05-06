from dataclasses import dataclass
from typing import Any

SYSTEM_PROMPT = "你是一个网络运维助手。基于用户请求和命令输出，给出简洁、准确、可执行的命令。"


@dataclass(frozen=True)
class PromptConversation:
    system_prompt: str
    messages: list[dict[str, str]]


def build_summary_conversation(
    user_input: str,
    command_outputs: list[str],
    recent_messages: list[dict[str, Any]] | None = None,
) -> PromptConversation:
    joined_outputs = "\n".join(f"{index}. {output}" for index, output in enumerate(command_outputs, start=1))
    return PromptConversation(
        system_prompt=SYSTEM_PROMPT,
        messages=[
            *(recent_messages or []),
            {
                "role": "user",
                "content": f"用户请求: {user_input}\n\n命令输出:\n{joined_outputs}",
            },
        ],
    )
