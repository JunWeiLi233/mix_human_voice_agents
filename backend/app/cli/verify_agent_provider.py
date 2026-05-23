from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.core.agent import AgentProviderError, generate_agent_reply_record
from app.core.safety import SafetyError
from app.models.schemas import AgentConfig, AgentProviderKind, AgentProviderVerificationReport


DEFAULT_PROVIDER_PROMPT = "Reply with one short sentence confirming this provider is connected."


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the selected agent provider before launch.")
    parser.add_argument("--provider", required=True, choices=list(AgentProviderKind.__args__))
    parser.add_argument("--model", required=True, help="Provider model name to verify.")
    parser.add_argument("--base-url", required=True, help="Provider base URL.")
    parser.add_argument("--api-key", default="", help="Provider API key. Optional for local/openai-compatible endpoints.")
    parser.add_argument(
        "--system-prompt",
        default="You are a disclosed synthetic mixed-voice assistant.",
        help="System prompt used for the provider preflight request.",
    )
    parser.add_argument("--prompt", default=DEFAULT_PROVIDER_PROMPT, help="Prompt used for the provider preflight.")
    parser.add_argument(
        "--report",
        default="data/agent-provider-verification-report.json",
        help="Path to write the JSON provider verification report.",
    )
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    if not args.model.strip():
        _write_report(
            report_path,
            {
                "status": "failed",
                "provider": args.provider,
                "model": args.model,
                "base_url": args.base_url.rstrip("/"),
                "error": "Agent model is required.",
            },
        )
        return 2
    if not args.base_url.strip():
        _write_report(
            report_path,
            {
                "status": "failed",
                "provider": args.provider,
                "model": args.model,
                "base_url": args.base_url.rstrip("/"),
                "error": "Agent base_url is required.",
            },
        )
        return 2
    if not args.prompt.strip():
        _write_report(
            report_path,
            {
                "status": "failed",
                "provider": args.provider,
                "model": args.model,
                "base_url": args.base_url.rstrip("/"),
                "error": "Agent provider verification prompt is required.",
            },
        )
        return 2

    config = AgentConfig(
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        system_prompt=args.system_prompt,
    )
    try:
        reply = generate_agent_reply_record(prompt=args.prompt, config=config)
    except (AgentProviderError, SafetyError, ValueError) as exc:
        _write_report(
            report_path,
            {
                "status": "failed",
                "provider": config.provider,
                "model": config.model,
                "base_url": config.base_url.rstrip("/"),
                "error": str(exc),
            },
        )
        return 1

    _write_report(
        report_path,
        {
            "status": "passed",
            "provider": reply.provider,
            "model": reply.model,
            "base_url": reply.base_url or config.base_url.rstrip("/"),
            "reply": reply.reply,
        },
    )
    return 0


def _write_report(report_path: Path, payload: dict[str, object]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "report_path": str(report_path)}
    report = AgentProviderVerificationReport.model_validate(payload)
    report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
