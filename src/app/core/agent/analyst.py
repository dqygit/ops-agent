from app.integrations.llm.base import SupportsSummarize
from app.shared.schemas import ModelConfig


def analyze_outputs(
    llm_provider: SupportsSummarize,
    config: ModelConfig,
    user_input: str,
    outputs: list[str],
    recent_messages=None,
) -> str:
    return llm_provider.summarize(
        config=config,
        user_input=user_input,
        command_outputs=outputs,
        recent_messages=recent_messages,
    )
