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


def build_anthropic_payload(config: AgentConfig, prompt: str) -> dict[str, Any]:
    if not config.model.strip():
        raise AgentProviderError("Agent model is required.")
    if not config.base_url.strip():
        raise AgentProviderError("Agent base_url is required.")
    check_generation_request(prompt)

    return {
        "model": config.model,
        "system": config.system_prompt,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }


def build_google_payload(config: AgentConfig, prompt: str) -> dict[str, Any]:
    if not config.model.strip():
        raise AgentProviderError("Agent model is required.")
    if not config.base_url.strip():
        raise AgentProviderError("Agent base_url is required.")
    check_generation_request(prompt)

    return {
        "systemInstruction": {
            "parts": [
                {
                    "text": config.system_prompt,
                }
            ],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
    }


def generate_agent_reply(
    prompt: str,
    config: AgentConfig,
    http_client: HttpClient | None = None,
) -> str:
    client = http_client or httpx.Client()
    base_url = config.base_url.rstrip("/")

    if config.provider in {"openai", "xai", "openai_compatible"}:
        if not config.api_key.strip():
            raise AgentProviderError("API key is required for OpenAI-compatible providers.")
        response = client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            json=build_agent_payload(config, prompt),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
    elif config.provider == "anthropic":
        if not config.api_key.strip():
            raise AgentProviderError("API key is required for Anthropic providers.")
        response = client.post(
            f"{base_url}/v1/messages",
            headers={
                "x-api-key": config.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=build_anthropic_payload(config, prompt),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        reply = next(
            (
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            ),
            "",
        )
        if not reply:
            raise AgentProviderError("Anthropic response did not include text content.")
    elif config.provider == "google":
        if not config.api_key.strip():
            raise AgentProviderError("API key is required for Google Gemini providers.")
        response = client.post(
            f"{base_url}/{_google_model_path(config.model)}:generateContent",
            headers={
                "x-goog-api-key": config.api_key,
                "Content-Type": "application/json",
            },
            json=build_google_payload(config, prompt),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        reply = _extract_google_reply(data)
    elif config.provider == "ollama":
        response = client.post(
            f"{base_url}/api/chat",
            headers={"Content-Type": "application/json"},
            json={**build_agent_payload(config, prompt), "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["message"]["content"]
    else:
        raise AgentProviderError(f"Unsupported agent provider: {config.provider}")

    _validate_agent_reply_text(reply)
    check_generation_request(reply)
    return reply


def generate_agent_reply_record(prompt: str, config: AgentConfig) -> AgentReply:
    reply = generate_agent_reply(prompt=prompt, config=config)
    return AgentReply(reply=reply, provider=config.provider, model=config.model, base_url=config.base_url.rstrip("/"))


def _validate_agent_reply_text(reply: str) -> None:
    if not reply.strip():
        raise AgentProviderError("Agent provider response must include non-empty text.")


def _google_model_path(model: str) -> str:
    cleaned = model.strip()
    if cleaned.startswith("models/"):
        return cleaned
    return f"models/{cleaned}"


def _extract_google_reply(data: dict[str, Any]) -> str:
    candidates = data.get("candidates", [])
    if not candidates:
        raise AgentProviderError("Google Gemini response did not include candidates.")
    parts = candidates[0].get("content", {}).get("parts", [])
    reply = "".join(part.get("text", "") for part in parts)
    if not reply:
        raise AgentProviderError("Google Gemini response did not include text content.")
    return reply
