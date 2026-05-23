from pathlib import Path
import json

from app.cli.launch_artifacts import main
from app.models.schemas import (
    AgentProviderVerificationReport,
    AgentTrace,
    AudioQuality,
    ConsentRecord,
    GenerationResult,
    QwenVerificationReport,
    SourceProfileDetail,
    TtsRuntimeStatus,
    VoiceBlend,
    BlendProfile,
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


def test_launch_artifacts_cli_separates_launch_eligible_and_stale_blends(tmp_path: Path, monkeypatch, capsys):
    voices = [
        voice_profile("voice_alice", "Alice"),
        voice_profile("voice_bob", "Bob"),
    ]
    blends = [
        VoiceBlend(
            id="blend_launch_ready",
            name="Alice + Bob",
            strategy="multi_reference_prompt",
            profiles=[
                BlendProfile(voice_profile_id="voice_alice", weight=0.5),
                BlendProfile(voice_profile_id="voice_bob", weight=0.5),
            ],
        ),
        VoiceBlend(
            id="blend_stale",
            name="Old Alice + Missing",
            strategy="multi_reference_prompt",
            profiles=[
                BlendProfile(voice_profile_id="voice_alice", weight=0.5),
                BlendProfile(voice_profile_id="voice_missing", weight=0.5),
            ],
        ),
    ]
    monkeypatch.setattr("app.cli.launch_artifacts.list_voice_profiles", lambda: voices)
    monkeypatch.setattr("app.cli.launch_artifacts.list_blends", lambda: blends)
    monkeypatch.setattr("app.cli.launch_artifacts.list_generation_results", lambda: [])
    monkeypatch.setattr(
        "app.cli.launch_artifacts.get_agent_provider_verification_report",
        lambda: AgentProviderVerificationReport(
            status="passed",
            report_path="data/agent-provider-verification-report.json",
            provider="openai_compatible",
            model="local-model",
            base_url="http://127.0.0.1:1234/v1",
            reply="Provider connected.",
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
    assert payload["blend_count"] == 2
    assert payload["launch_eligible_blend_count"] == 1
    assert payload["stale_blend_count"] == 1
    assert payload["launch_eligible_blend_ids"] == ["blend_launch_ready"]
    assert payload["stale_blend_ids"] == ["blend_stale"]
    assert payload["blends"][0]["launch_eligible"] is True
    assert payload["blends"][1]["launch_eligible"] is False
    assert payload["blends"][1]["missing_voice_profile_ids"] == ["voice_missing"]
    assert 'python -m app.cli.create_blend --name "Launch mixed voice"' not in payload["next_commands"]
    output = capsys.readouterr().out
    assert "Launch-eligible blends: 1; stale/nonmatching blends: 1" in output


def test_launch_artifacts_cli_explains_unusable_imported_voices(tmp_path: Path, monkeypatch, capsys):
    voices = [
        voice_profile("voice_alice", "Alice"),
        voice_profile(
            "voice_no_consent",
            "No Consent",
            allowed_uses=["local_audio_export"],
        ),
        voice_profile("voice_no_text", "No Text", reference_text=""),
        voice_profile(
            "voice_clipped",
            "Clipped",
            warnings=["Reference audio appears clipped; record a cleaner sample."],
        ),
    ]
    monkeypatch.setattr("app.cli.launch_artifacts.list_voice_profiles", lambda: voices)
    monkeypatch.setattr("app.cli.launch_artifacts.list_blends", lambda: [])
    monkeypatch.setattr("app.cli.launch_artifacts.list_generation_results", lambda: [])
    monkeypatch.setattr(
        "app.cli.launch_artifacts.get_agent_provider_verification_report",
        lambda: AgentProviderVerificationReport(status="missing", report_path="data/agent-provider-verification-report.json"),
    )
    monkeypatch.setattr(
        "app.cli.launch_artifacts.get_qwen_verification_report",
        lambda: QwenVerificationReport(status="missing", report_path="data/qwen-runtime-verification-report.json"),
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
    assert payload["usable_voice_count"] == 1
    assert payload["unusable_voice_count"] == 3
    voices_by_id = {voice["id"]: voice for voice in payload["voices"]}
    assert voices_by_id["voice_alice"]["launch_usable"] is True
    assert voices_by_id["voice_alice"]["unusable_reasons"] == []
    assert voices_by_id["voice_no_consent"]["launch_usable"] is False
    assert voices_by_id["voice_no_consent"]["unusable_reasons"] == [
        "Voice consent does not allow private agent voice synthesis."
    ]
    assert voices_by_id["voice_no_text"]["unusable_reasons"] == ["Reference transcript is missing."]
    assert voices_by_id["voice_clipped"]["unusable_reasons"] == [
        "Audio quality warnings must be resolved before launch."
    ]
    output = capsys.readouterr().out
    assert "Usable voices: 1; unusable voices: 3" in output
    assert "voice_no_consent: No Consent (unusable: Voice consent does not allow private agent voice synthesis.)" in output


def test_launch_artifacts_cli_explains_stale_qwen_generations(tmp_path: Path, monkeypatch, capsys):
    voices = [
        voice_profile("voice_alice", "Alice"),
        voice_profile("voice_bob", "Bob"),
    ]
    launch_blend = VoiceBlend(
        id="blend_launch_ready",
        name="Alice + Bob",
        strategy="multi_reference_prompt",
        profiles=[
            BlendProfile(voice_profile_id="voice_alice", weight=0.5),
            BlendProfile(voice_profile_id="voice_bob", weight=0.5),
        ],
    )
    generations = [
        generation_result(
            "generation_ready",
            "qwen3_tts",
            blend_id="blend_launch_ready",
            blend_name="Alice + Bob",
            source_profiles=launch_blend.profiles,
            source_details=[
                source_detail("voice_alice", "Alice"),
                source_detail("voice_bob", "Bob"),
            ],
            agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini", base_url="https://api.openai.com/v1"),
        ),
        generation_result(
            "generation_local",
            "local_development_wav",
            blend_id="blend_launch_ready",
            blend_name="Alice + Bob",
            source_profiles=launch_blend.profiles,
        ),
        generation_result(
            "generation_stale",
            "qwen3_tts",
            blend_id="blend_missing",
            blend_name="Missing blend",
            source_profiles=[BlendProfile(voice_profile_id="voice_alice", weight=1.0)],
            source_details=[source_detail("voice_alice", "Alice")],
        ),
    ]
    monkeypatch.setattr("app.cli.launch_artifacts.list_voice_profiles", lambda: voices)
    monkeypatch.setattr("app.cli.launch_artifacts.list_blends", lambda: [launch_blend])
    monkeypatch.setattr("app.cli.launch_artifacts.list_generation_results", lambda: generations)
    monkeypatch.setattr(
        "app.cli.launch_artifacts.get_agent_provider_verification_report",
        lambda: AgentProviderVerificationReport(
            status="passed",
            report_path="data/agent-provider-verification-report.json",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            reply="Provider connected.",
        ),
    )
    monkeypatch.setattr(
        "app.cli.launch_artifacts.get_qwen_verification_report",
        lambda: QwenVerificationReport(
            status="passed",
            report_path="data/qwen-runtime-verification-report.json",
            voice_profile_ids=["voice_alice", "voice_bob"],
            output_audio_path=str(Path("data") / "generations" / "qwen_verify.wav"),
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
    assert payload["qwen_generation_count"] == 2
    assert payload["launch_eligible_generation_count"] == 1
    assert payload["stale_generation_count"] == 2
    assert payload["launch_eligible_generation_ids"] == ["generation_ready"]
    assert payload["stale_generation_ids"] == ["generation_local", "generation_stale"]
    generations_by_id = {generation["id"]: generation for generation in payload["generations"]}
    assert generations_by_id["generation_ready"]["launch_eligible"] is True
    assert generations_by_id["generation_ready"]["stale_reasons"] == []
    assert generations_by_id["generation_local"]["stale_reasons"] == [
        "Generation was not created with Qwen3-TTS."
    ]
    assert generations_by_id["generation_stale"]["stale_reasons"] == [
        "Qwen generation must include at least two imported source profile details.",
        "Qwen generation must include an agent provider trace.",
        "Qwen generation must reference a current saved blend.",
    ]
    output = capsys.readouterr().out
    assert "Qwen launch-eligible generations: 1; stale/nonmatching generations: 2" in output
    assert (
        "generation_stale: qwen3_tts (stale: Qwen generation must include at least two imported source profile "
        "details.; Qwen generation must include an agent provider trace.; Qwen generation must reference a current "
        "saved blend.)"
        in output
    )


def test_launch_artifacts_cli_updates_tasks_handoff_with_artifact_inventory(tmp_path: Path, monkeypatch):
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
        ),
    )
    monkeypatch.setattr(
        "app.cli.launch_artifacts.get_qwen_verification_report",
        lambda: QwenVerificationReport(
            status="missing",
            report_path="data/qwen-runtime-verification-report.json",
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
    tasks_path = tmp_path / "TASKS.md"
    tasks_path.write_text(
        "# TASKS\n\nExisting handoff notes.\n\n## Launch Artifact Inventory\n\nold inventory\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--report",
            str(tmp_path / "launch-artifacts.json"),
            "--tasks",
            str(tasks_path),
        ]
    )

    assert exit_code == 0
    content = tasks_path.read_text(encoding="utf-8")
    assert "old inventory" not in content
    assert "## Launch Artifact Inventory" in content
    assert "- Voices: `2` total; `2` usable; `0` unusable" in content
    assert "- Blends: `0` total; `0` launch-eligible; `0` stale/nonmatching" in content
    assert "- Generations: `0` total; `0` Qwen; `0` launch-eligible; `0` stale/nonmatching" in content
    assert "- Usable voice IDs: `voice_alice`, `voice_bob`" in content
    assert "- Provider preflight status: `missing`" in content
    assert "- Qwen verification status: `missing`" in content
    assert "- Qwen runtime: `available` (`Qwen/Qwen3-TTS-12Hz-0.6B-Base`)" in content
    assert "Next artifact commands:" in content
    assert "- [ ] `python -m app.cli.create_blend --name \"Launch mixed voice\"" in content
    assert "- [ ] `python -m app.cli.verify_agent_provider --provider openai_compatible" in content


def voice_profile(
    profile_id: str,
    display_name: str,
    reference_text: str | None = None,
    allowed_uses: list[str] | None = None,
    warnings: list[str] | None = None,
) -> VoiceProfile:
    return VoiceProfile(
        id=profile_id,
        display_name=display_name,
        reference_text=(
            reference_text
            if reference_text is not None
            else f"{display_name} reads a clean reference sentence for Qwen cloning."
        ),
        consent=ConsentRecord(
            voice_profile_id=profile_id,
            speaker_display_name=display_name,
            consent_type="self_or_written_permission",
            allowed_uses=allowed_uses or ["private_agent_voice", "local_audio_export"],
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
            warnings=warnings or [],
        ),
    )


def generation_result(
    generation_id: str,
    backend: str,
    *,
    blend_id: str,
    blend_name: str,
    source_profiles: list[BlendProfile],
    source_details: list[SourceProfileDetail] | None = None,
    agent_trace: AgentTrace | None = None,
) -> GenerationResult:
    return GenerationResult(
        id=generation_id,
        audio_path=str(Path("data") / "generations" / f"{generation_id}.wav"),
        metadata_path=str(Path("data") / "generations" / f"{generation_id}.json"),
        blend_id=blend_id,
        blend_name=blend_name,
        prompt="Greet the user as a disclosed synthetic assistant.",
        agent_reply="Hello, I am a disclosed synthetic mixed voice assistant.",
        synthetic_label="synthetic mixed voice",
        source_profile_ids=[profile.voice_profile_id for profile in source_profiles],
        source_profiles=source_profiles,
        source_profile_details=source_details or [],
        blend_strategy="multi_reference_prompt",
        tts_backend=backend,
        agent_trace=agent_trace,
    )


def source_detail(profile_id: str, display_name: str) -> SourceProfileDetail:
    return SourceProfileDetail(
        voice_profile_id=profile_id,
        weight=0.5,
        display_name=display_name,
        consent_confirmed_by="Junwei",
        allowed_uses=["private_agent_voice", "local_audio_export"],
        reference_text_present=True,
    )
