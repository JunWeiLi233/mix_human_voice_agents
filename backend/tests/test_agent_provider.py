import pytest

from app.core.agent import AgentProviderError, build_agent_payload, generate_agent_reply
from app.models.schemas import AgentConfig, AgentProviderKind


class FakeHttpClient:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.requests.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(self.payload)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def config(provider: AgentProviderKind) -> AgentConfig:
    base_urls = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com",
        "xai": "https://api.x.ai/v1",
        "openai_compatible": "https://api.example.test/v1",
        "ollama": "http://127.0.0.1:11434",
    }
    return AgentConfig(
        provider=provider,
        model="demo-model",
        base_url=base_urls[provider],
        api_key="" if provider == "ollama" else "sk-test",
        system_prompt="You are a disclosed synthetic mixed-voice assistant.",
    )


def test_build_agent_payload_includes_synthetic_voice_instruction():
    payload = build_agent_payload(
        config("openai_compatible"),
        "Say hello.",
    )

    assert payload["model"] == "demo-model"
    assert "disclosed synthetic mixed-voice assistant" in payload["messages"][0]["content"]
    assert payload["messages"][1]["content"] == "Say hello."


def test_openai_compatible_provider_uses_user_api_settings():
    client = FakeHttpClient({"choices": [{"message": {"content": "Hello from API."}}]})

    reply = generate_agent_reply(
        prompt="Say hello.",
        config=config("openai_compatible"),
        http_client=client,
    )

    assert reply == "Hello from API."
    assert client.requests[0]["url"] == "https://api.example.test/v1/chat/completions"
    assert client.requests[0]["headers"]["Authorization"] == "Bearer sk-test"


def test_openai_provider_uses_chatgpt_api_settings():
    client = FakeHttpClient({"choices": [{"message": {"content": "Hello from ChatGPT."}}]})

    reply = generate_agent_reply(
        prompt="Say hello.",
        config=config("openai"),
        http_client=client,
    )

    assert reply == "Hello from ChatGPT."
    assert client.requests[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert client.requests[0]["headers"]["Authorization"] == "Bearer sk-test"


def test_xai_provider_uses_grok_openai_compatible_api_settings():
    client = FakeHttpClient({"choices": [{"message": {"content": "Hello from Grok."}}]})

    reply = generate_agent_reply(
        prompt="Say hello.",
        config=config("xai"),
        http_client=client,
    )

    assert reply == "Hello from Grok."
    assert client.requests[0]["url"] == "https://api.x.ai/v1/chat/completions"
    assert client.requests[0]["headers"]["Authorization"] == "Bearer sk-test"


def test_anthropic_provider_uses_claude_messages_api_settings():
    client = FakeHttpClient({"content": [{"type": "text", "text": "Hello from Claude."}]})

    reply = generate_agent_reply(
        prompt="Say hello.",
        config=config("anthropic"),
        http_client=client,
    )

    assert reply == "Hello from Claude."
    assert client.requests[0]["url"] == "https://api.anthropic.com/v1/messages"
    assert client.requests[0]["headers"]["x-api-key"] == "sk-test"
    assert client.requests[0]["headers"]["anthropic-version"] == "2023-06-01"
    assert client.requests[0]["json"]["system"] == "You are a disclosed synthetic mixed-voice assistant."
    assert client.requests[0]["json"]["messages"] == [{"role": "user", "content": "Say hello."}]
    assert client.requests[0]["json"]["max_tokens"] == 1024


def test_ollama_provider_uses_local_endpoint_without_api_key():
    client = FakeHttpClient({"message": {"content": "Hello from local LLM."}})

    reply = generate_agent_reply(
        prompt="Say hello.",
        config=config("ollama"),
        http_client=client,
    )

    assert reply == "Hello from local LLM."
    assert client.requests[0]["url"] == "http://127.0.0.1:11434/api/chat"
    assert "Authorization" not in client.requests[0]["headers"]


def test_provider_rejects_missing_model():
    bad = config("ollama").model_copy(update={"model": ""})

    with pytest.raises(AgentProviderError, match="model"):
        generate_agent_reply("Say hello.", bad, http_client=FakeHttpClient({}))
