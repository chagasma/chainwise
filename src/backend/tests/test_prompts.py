from chainwise.agent.prompts import _PAYLOAD_CONTRACT
from chainwise.api.schemas import LLMPromptPayload


def test_payload_contract_mentions_all_llm_prompt_payload_fields() -> None:
    for field_name in LLMPromptPayload.model_fields:
        assert f'"{field_name}"' in _PAYLOAD_CONTRACT, (
            f"_PAYLOAD_CONTRACT doesn't mention '{field_name}' — "
            "keep it in sync with LLMPromptPayload."
        )
