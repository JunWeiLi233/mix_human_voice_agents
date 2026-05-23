import json
import math
from pathlib import Path
import struct
import wave

from app.cli.generate_voice import main
from app.models.schemas import (
    AgentProviderVerificationReport,
    AgentReply,
    AudioQuality,
    BlendProfile,
    ConsentRecord,
    QwenVerificationReport,
    SourceProfileDetail,
    VoiceBlend,
    VoiceProfile,
)


def test_generate_voice_cli_creates_qwen_mixed_clip_from_saved_blend(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_profile("voice_a", "Alice")
    save_profile("voice_b", "Bob")
    blend = save_blend("voice_a", "voice_b")
    write_passed_agent_report()
    write_passed_qwen_report(["voice_a", "voice_b"])
    metadata_path = tmp_path / "generated-report.json"

    monkeypatch.setattr(
        "app.cli.generate_voice.generate_agent_reply_record",
        lambda prompt, config: AgentReply(
            reply="Hello from a launch-ready mixed voice.",
            provider=config.provider,
            model=config.model,
            base_url=config.base_url.rstrip("/"),
        ),
    )

    class FakeQwenAdapter:
        runtime_config = {
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "device_map": "auto",
            "dtype": None,
            "attn_implementation": None,
        }

        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            output = self.__class__.output_root / f"{blend.id}_qwen_generated.wav"
            write_reference_wav(output)
            return output

    monkeypatch.setattr("app.cli.generate_voice.QwenTtsAdapter", FakeQwenAdapter)

    exit_code = main(
        [
            "--blend-id",
            blend.id,
            "--prompt",
            "Greet the user as a disclosed synthetic assistant.",
            "--provider",
            "openai_compatible",
            "--model",
            "local-qwen-agent",
            "--base-url",
            "http://127.0.0.1:1234/v1",
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert report["tts_backend"] == "qwen3_tts"
    assert report["blend_strategy"] == "multi_reference_prompt"
    assert report["source_profile_ids"] == ["voice_a", "voice_b"]
    assert report["prompt"] == "Greet the user as a disclosed synthetic assistant."
    assert report["agent_reply"] == "Hello from a launch-ready mixed voice."
    assert report["agent_trace"] == {
        "provider": "openai_compatible",
        "model": "local-qwen-agent",
        "base_url": "http://127.0.0.1:1234/v1",
    }
    assert Path(report["audio_path"]).exists()
    assert Path(report["metadata_path"]).exists()
    assert report["metadata_path"] != str(metadata_path)
    saved_metadata = json.loads(Path(report["metadata_path"]).read_text(encoding="utf-8"))
    assert saved_metadata["source_profile_details"][0]["display_name"] == "Alice"
    assert saved_metadata["source_profile_details"][1]["display_name"] == "Bob"


def test_generate_voice_cli_requires_passed_agent_provider_preflight(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_profile("voice_a", "Alice")
    save_profile("voice_b", "Bob")
    blend = save_blend("voice_a", "voice_b")
    write_passed_qwen_report(["voice_a", "voice_b"])
    metadata_path = tmp_path / "failed-generation.json"

    exit_code = main(
        [
            "--blend-id",
            blend.id,
            "--prompt",
            "Greet the user as a disclosed synthetic assistant.",
            "--provider",
            "openai_compatible",
            "--model",
            "local-qwen-agent",
            "--base-url",
            "http://127.0.0.1:1234/v1",
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 1
    report = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "Agent provider preflight must pass before Qwen generation.",
    }
    assert list((tmp_path / "data" / "generations").glob("*.json")) == []


def test_generate_voice_cli_rejects_qwen_report_from_wrong_backend_before_generation(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    save_profile("voice_a", "Alice")
    save_profile("voice_b", "Bob")
    blend = save_blend("voice_a", "voice_b")
    write_passed_agent_report()
    output_path = write_reference_wav(Path("data") / "generations" / "qwen_verify.wav")
    report_path = Path("data") / "qwen-runtime-verification-report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "checked_at": "2026-05-23T00:00:00+00:00",
                "report_path": str(report_path),
                "voice_profile_ids": ["voice_a", "voice_b"],
                "tts_backend": "local_development_wav",
                "blend_strategy": "multi_reference_prompt",
                "source_profile_details": [
                    {
                        "voice_profile_id": "voice_a",
                        "display_name": "Alice",
                        "weight": 0.5,
                        "consent_confirmed_by": "Junwei",
                        "allowed_uses": ["private_agent_voice", "local_audio_export"],
                        "reference_text_present": True,
                    },
                    {
                        "voice_profile_id": "voice_b",
                        "display_name": "Bob",
                        "weight": 0.5,
                        "consent_confirmed_by": "Junwei",
                        "allowed_uses": ["private_agent_voice", "local_audio_export"],
                        "reference_text_present": True,
                    },
                ],
                "output_audio_path": str(output_path),
                "text": "This is a Qwen verification.",
            }
        ),
        encoding="utf-8",
    )
    metadata_path = tmp_path / "failed-generation.json"

    def fail_if_called(*args, **kwargs):
        raise AssertionError("invalid Qwen verification should stop before generation")

    monkeypatch.setattr("app.cli.generate_voice.generate_agent_reply_record", fail_if_called)
    monkeypatch.setattr("app.cli.generate_voice.QwenTtsAdapter.from_pretrained", fail_if_called)

    exit_code = main(
        [
            "--blend-id",
            blend.id,
            "--prompt",
            "Greet the user as a disclosed synthetic assistant.",
            "--provider",
            "openai_compatible",
            "--model",
            "local-qwen-agent",
            "--base-url",
            "http://127.0.0.1:1234/v1",
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 1
    report = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "Qwen verification report was not produced by the Qwen3-TTS backend.",
    }


def test_generate_voice_cli_rejects_mismatched_qwen_runtime_options_before_external_calls(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    save_profile("voice_a", "Alice")
    save_profile("voice_b", "Bob")
    blend = save_blend("voice_a", "voice_b")
    write_passed_agent_report()
    write_passed_qwen_report(["voice_a", "voice_b"])
    metadata_path = tmp_path / "failed-generation.json"

    def fail_if_called(*args, **kwargs):
        raise AssertionError("runtime mismatch should stop before external calls")

    monkeypatch.setattr("app.cli.generate_voice.generate_agent_reply_record", fail_if_called)
    monkeypatch.setattr("app.cli.generate_voice.QwenTtsAdapter.from_pretrained", fail_if_called)

    exit_code = main(
        [
            "--blend-id",
            blend.id,
            "--prompt",
            "Greet the user as a disclosed synthetic assistant.",
            "--provider",
            "openai_compatible",
            "--model",
            "local-qwen-agent",
            "--base-url",
            "http://127.0.0.1:1234/v1",
            "--qwen-model-id",
            "Qwen/Other-TTS-Model",
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 1
    report = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "Qwen generation runtime config must match the passed Qwen verification.",
    }


def test_generate_voice_cli_rejects_unusable_saved_blend_before_external_calls(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    save_profile("voice_a", "Alice")
    save_profile("voice_b", "Bob", warnings=["Reference audio appears clipped; record a cleaner sample."])
    blend = save_blend("voice_a", "voice_b")
    write_passed_agent_report()
    write_passed_qwen_report(["voice_a", "voice_b"])
    metadata_path = tmp_path / "failed-generation.json"
    agent_calls: list[str] = []

    def fake_agent_reply(prompt, config):
        agent_calls.append(prompt)
        return AgentReply(
            reply="This should not be generated.",
            provider=config.provider,
            model=config.model,
            base_url=config.base_url.rstrip("/"),
        )

    class FailIfQwenLoads:
        @classmethod
        def from_pretrained(cls, **kwargs):
            raise ValueError("Qwen should not load for an unusable saved blend.")

    monkeypatch.setattr("app.cli.generate_voice.generate_agent_reply_record", fake_agent_reply)
    monkeypatch.setattr("app.cli.generate_voice.QwenTtsAdapter", FailIfQwenLoads)

    exit_code = main(
        [
            "--blend-id",
            blend.id,
            "--prompt",
            "Greet the user as a disclosed synthetic assistant.",
            "--provider",
            "openai_compatible",
            "--model",
            "local-qwen-agent",
            "--base-url",
            "http://127.0.0.1:1234/v1",
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 1
    assert agent_calls == []
    report = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "Voice profile voice_b must not have audio quality warnings for Qwen synthesis.",
    }
    assert list((tmp_path / "data" / "generations").glob("*_qwen_generated.*")) == []


def save_profile(profile_id: str, display_name: str, warnings: list[str] | None = None) -> VoiceProfile:
    voice_dir = Path("data") / "voices" / profile_id
    voice_dir.mkdir(parents=True, exist_ok=True)
    audio_path = write_reference_wav(voice_dir / "source.wav")
    profile = VoiceProfile(
        id=profile_id,
        display_name=display_name,
        reference_text=f"{display_name} reads a clean reference sentence for Qwen cloning.",
        consent=ConsentRecord(
            voice_profile_id=profile_id,
            speaker_display_name=display_name,
            consent_type="self_or_written_permission",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            confirmed_by="Junwei",
            notes="Written permission captured.",
            synthetic_voice_allowed=True,
        ),
        source_audio_path=str(audio_path),
        cleaned_audio_path=str(audio_path),
        quality=AudioQuality(
            file_name="source.wav",
            size_bytes=audio_path.stat().st_size,
            format="wav",
            duration_seconds=5.0,
            sample_rate_hz=16000,
            channel_count=1,
            warnings=warnings or [],
        ),
    )
    (voice_dir / "profile.json").write_text(profile.model_dump_json(), encoding="utf-8")
    return profile


def save_blend(*profile_ids: str) -> VoiceBlend:
    blend_root = Path("data") / "blends"
    blend_root.mkdir(parents=True, exist_ok=True)
    blend = VoiceBlend(
        id="blend_launch",
        name="Launch blend",
        profiles=[BlendProfile(voice_profile_id=profile_id, weight=1 / len(profile_ids)) for profile_id in profile_ids],
        strategy="multi_reference_prompt",
    )
    (blend_root / f"{blend.id}.json").write_text(blend.model_dump_json(), encoding="utf-8")
    return blend


def write_passed_agent_report() -> None:
    report_path = Path("data") / "agent-provider-verification-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = AgentProviderVerificationReport(
        status="passed",
        provider="openai_compatible",
        model="local-qwen-agent",
        base_url="http://127.0.0.1:1234/v1",
        reply="Provider ready.",
        report_path=str(report_path),
    )
    report_path.write_text(report.model_dump_json(), encoding="utf-8")


def write_passed_qwen_report(profile_ids: list[str]) -> None:
    output_path = Path("data") / "generations" / "qwen_verify.wav"
    write_reference_wav(output_path)
    report_path = Path("data") / "qwen-runtime-verification-report.json"
    report = QwenVerificationReport(
        status="passed",
        report_path=str(report_path),
        voice_profile_ids=profile_ids,
        model_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        device_map="auto",
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        source_profile_details=[
            SourceProfileDetail(
                voice_profile_id="voice_a",
                display_name="Alice",
                weight=0.5,
                consent_confirmed_by="Junwei",
                allowed_uses=["private_agent_voice", "local_audio_export"],
                reference_text_present=True,
            ),
            SourceProfileDetail(
                voice_profile_id="voice_b",
                display_name="Bob",
                weight=0.5,
                consent_confirmed_by="Junwei",
                allowed_uses=["private_agent_voice", "local_audio_export"],
                reference_text_present=True,
            ),
        ],
        output_audio_path=str(output_path),
        text="This is a Qwen verification.",
    )
    report_path.write_text(report.model_dump_json(), encoding="utf-8")


def write_reference_wav(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    duration_seconds = 5
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate)))
            for index in range(sample_rate * duration_seconds)
        )
        wav_file.writeframes(frames)
    return path
