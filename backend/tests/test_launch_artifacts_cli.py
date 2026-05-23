from pathlib import Path
import json

from app.cli.launch_artifacts import main
from app.models.schemas import (
    AgentProviderVerificationReport,
    AudioQuality,
    ConsentRecord,
    QwenVerificationReport,
    TtsRuntimeStatus,
    VoiceProfile,
)


def test_launch_artifacts_cli_writes_inventory_with_next_commands(tmp_path: Path, monkeypatch, capsys):
    voices = [
        voice_profile("voice_alice", "Alice"),
        voice_profile("voice_bob", "Bob"),
    ]

    monkeypatch.setattr("app.cli.launch_artifacts.list_voice_profiles", lambda: voices)
    monkeypatch.setattr("app.cli.launch_artifacts.list_blends", lambda: [])
    monkeypatch.setattr("app.cli.launch_artifacts.list_generation_results", lambda: [])
    monkeypatch.setattr(
        "app.cli.launch_artifacts.get_agent_provider_verification_report",
        lambda: AgentProviderVerificationReport(
            status="missing",
            report_path="data/agent-provider-verification-report.json",
            error="Run the Agent Provider Test provider preflight before launch.",
        ),
    )
    monkeypatch.setattr(
        "app.cli.launch_artifacts.get_qwen_verification_report",
        lambda: QwenVerificationReport(
            status="missing",
            report_path="data/qwen-runtime-verification-report.json",
            error="Run python -m app.cli.verify_qwen_runtime with two consented voice profile ids.",
        ),
    )
    monkeypatch.setattr(
        "app.cli.launch_artifacts.QwenTtsAdapter.runtime_status",
        lambda: TtsRuntimeStatus(
            backend="qwen3_tts",
            available=True,
            model_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            message="qwen-tts package is importable.",
        ),
    )
    report_path = tmp_path / "launch-artifacts.json"

    exit_code = main(["--report", str(report_path), "--summary"])

    assert exit_code == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["voice_count"] == 2
    assert payload["usable_voice_ids"] == ["voice_alice", "voice_bob"]
    assert payload["agent_provider"]["status"] == "missing"
    assert payload["qwen_runtime"]["available"] is True
    assert payload["agent_provider_commands"]["chatgpt"].startswith(
        "python -m app.cli.verify_agent_provider --provider openai"
    )
    assert "--base-url https://api.openai.com/v1" in payload["agent_provider_commands"]["chatgpt"]
    assert "--provider anthropic" in payload["agent_provider_commands"]["claude"]
    assert "--provider xai" in payload["agent_provider_commands"]["grok"]
    assert "--provider google" in payload["agent_provider_commands"]["gemini"]
    assert "--provider ollama" in payload["agent_provider_commands"]["local_ollama"]
    assert (
        "python -m app.cli.verify_qwen_runtime --voice-profile-id voice_alice --voice-profile-id voice_bob"
        in payload["next_commands"]
    )
    output = capsys.readouterr().out
    assert "Launch artifacts: 2 voices, 0 blends, 0 generations" in output
    assert "voice_alice: Alice" in output
    assert "voice_bob: Bob" in output
    assert "python -m app.cli.create_blend --name" in output
    assert "Provider command options:" in output
    assert "ChatGPT: python -m app.cli.verify_agent_provider --provider openai" in output
    assert "Claude: python -m app.cli.verify_agent_provider --provider anthropic" in output
    assert "Grok: python -m app.cli.verify_agent_provider --provider xai" in output


def voice_profile(profile_id: str, display_name: str) -> VoiceProfile:
    return VoiceProfile(
        id=profile_id,
        display_name=display_name,
        reference_text=f"{display_name} reads a clean reference sentence for Qwen cloning.",
        consent=ConsentRecord(
            voice_profile_id=profile_id,
            speaker_display_name=display_name,
            consent_type="self_or_written_permission",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            confirmed_by="Junwei",
            synthetic_voice_allowed=True,
        ),
        source_audio_path=f"data/voices/{profile_id}/sample.wav",
        cleaned_audio_path=f"data/voices/{profile_id}/sample.wav",
        quality=AudioQuality(
            file_name="sample.wav",
            size_bytes=160044,
            format="wav",
            duration_seconds=8.0,
            sample_rate_hz=24000,
            channel_count=1,
            warnings=[],
        ),
    )
