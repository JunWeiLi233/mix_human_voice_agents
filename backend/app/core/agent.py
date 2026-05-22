from typing import Any, Protocol

import httpx

from app.core.safety import check_generation_request
from app.models.schemas import AgentConfig, AgentReply


class AgentProviderError(ValueError):
    pass


class HttpClient(Protocol):
    def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        raise NotImplementedError


def build_agent_payload(config: AgentConfig, prompt: str) -> dict[str, Any]:
    if not config.model.strip():
        raise AgentProviderError("Agent model is required.")
    if not config.base_url.strip():
        raise AgentProviderError("Agent base_url is required.")
    check_generation_request(prompt)

    return {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": config.system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }


def generate_agent_reply(
    prompt: str,
    config: AgentConfig,
    http_client: HttpClient | None = None,
) -> str:
    client = http_client or httpx.Client()
    payload = build_agent_payload(config, prompt)
    base_url = config.base_url.rstrip("/")

    if config.provider == "openai_compatible":
        if not config.api_key.strip():
            raise AgentProviderError("API key is required for OpenAI-compatible providers.")
        response = client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
    elif config.provider == "ollama":
        response = client.post(
            f"{base_url}/api/chat",
            headers={"Content-Type": "application/json"},
            json={**payload, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["message"]["content"]
    else:
        raise AgentProviderError(f"Unsupported agent provider: {config.provider}")

    check_generation_request(reply)
    return reply


def generate_agent_reply_record(prompt: str, config: AgentConfig) -> AgentReply:
    reply = generate_agent_reply(prompt=prompt, config=config)
    return AgentReply(reply=reply, provider=config.provider, model=config.model)

