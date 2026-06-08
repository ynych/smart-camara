"""PromptAgent 校验与 responses 文本提取（TDD）。"""

from agents.prompt_agent import extract_responses_text, validate_chat_endpoint_id


def test_validate_rejects_ark_app_id():
    assert validate_chat_endpoint_id("ark-foo") is not None


def test_validate_accepts_ep():
    assert validate_chat_endpoint_id("ep-20260320111147-t4tz8") is None


def test_extract_responses_text_from_output_blocks():
    body = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "你好"}],
            }
        ]
    }
    assert extract_responses_text(body) == "你好"


def test_extract_fallback_chat_completions():
    body = {"choices": [{"message": {"content": "legacy"}}]}
    assert extract_responses_text(body) == "legacy"
