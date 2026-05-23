from pathlib import Path
from datetime import datetime
import json

from app.cli.verify_agent_provider import main
from app.models.schemas import AgentReply


def test_verify_agent_provider_writes_passed_report(tmp_path: Path, monkeypatch):
    seen: dict[str, object] = {}

    def fake_generate_agent_reply_record(prompt, config):
        seen["prompt"] = prompt
        seen["config"] = config
        return AgentReply(
            reply="Provider ready for mixed voice launch.",
            provider=config.provider,
            model=config.model,
            base_url=config.base_url.rstrip("/"),
        )

    monkeypatch.setattr("app.cli.verify_agent_provider.generate_agent_reply_record", fake_generate_agent_reply_record)
    report_path = tmp_path / "agent-provider-verification-report.json"

    exit_code = main(
        [
            "--provider",
            "openai_compatible",
            "--model",
            "custom-voice-agent-model",
            "--base-url",
            "http://127.0.0.1:1234/v1/",
            "--api-key",
            "sk-test",
            "--prompt",
            "Reply with one short sentence confirming this provider is connected.",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert seen["prompt"] == "Reply with one short sentence confirming this provider is connected."
    assert seen["config"].provider == "openai_compatible"
    assert seen["config"].model == "custom-voice-agent-model"
    assert seen["config"].base_url == "http://127.0.0.1:1234/v1/"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["provider"] == "openai_compatible"
    assert report["model"] == "custom-voice-agent-model"
    assert report["base_url"] == "http://127.0.0.1:1234/v1"
    assert report["reply"] == "Provider ready for mixed voice launch."
    assert report["report_path"] == str(report_path)
    assert datetime.fromisoformat(report["checked_at"])


def test_verify_agent_provider_writes_failed_report_on_provider_error(tmp_path: Path, monkeypatch):
    def fake_generate_agent_reply_record(prompt, config):
        raise ValueError("connection refused")

    monkeypatch.setattr("app.cli.verify_agent_provider.generate_agent_reply_record", fake_generate_agent_reply_record)
    report_path = tmp_path / "agent-provider-verification-report.json"

    exit_code = main(
        [
            "--provider",
            "ollama",
            "--model",
            "llama3.1",
            "--base-url",
            "http://127.0.0.1:11434",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["provider"] == "ollama"
    assert report["model"] == "llama3.1"
    assert report["base_url"] == "http://127.0.0.1:11434"
    assert report["error"] == "connection refused"


def test_verify_agent_provider_rejects_missing_model_before_request(tmp_path: Path, monkeypatch):
    def fail_if_called(prompt, config):
        raise AssertionError("provider should not be called when model is blank")

    monkeypatch.setattr("app.cli.verify_agent_provider.generate_agent_reply_record", fail_if_called)
    report_path = tmp_path / "agent-provider-verification-report.json"

    exit_code = main(
        [
            "--provider",
            "ollama",
            "--model",
            " ",
            "--base-url",
            "http://127.0.0.1:11434",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["error"] == "Agent model is required."
