from pathlib import Path
import json

from app.cli.verify_qwen_runtime import main
from app.models.schemas import VoiceProfile


def test_verify_qwen_runtime_generates_report_with_selected_profiles(tmp_path: Path, monkeypatch):
    seen: dict[str, object] = {}

    def fake_get_profiles(profile_ids):
        seen["profile_ids"] = profile_ids
        return {
            "voice_a": profile("voice_a", "Alice", "Alice reads the reference text."),
            "voice_b": profile("voice_b", "Bob", "Bob reads the reference text."),
        }

    class FakeQwenAdapter:
        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            seen["output_root"] = output_root
            seen["load_kwargs"] = kwargs
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            seen["text"] = text
            seen["blend"] = blend
            seen["voice_profiles"] = voice_profiles
            output = tmp_path / "qwen_verify.wav"
            output.write_bytes(b"RIFFfake")
            return output

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fake_get_profiles)
    monkeypatch.setattr("app.cli.verify_qwen_runtime.QwenTtsAdapter", FakeQwenAdapter)

    report_path = tmp_path / "report.json"
    exit_code = main(
        [
            "--voice-profile-id",
            "voice_a",
            "--voice-profile-id",
            "voice_b",
            "--text",
            "This is a Qwen runtime verification.",
            "--report",
            str(report_path),
            "--model-id",
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "--device-map",
            "cuda:0",
            "--dtype",
            "bfloat16",
            "--attn-implementation",
            "flash_attention_2",
        ]
    )

    assert exit_code == 0
    assert seen["profile_ids"] == ["voice_a", "voice_b"]
    assert seen["text"] == "This is a Qwen runtime verification."
    assert seen["load_kwargs"] == {
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "device_map": "cuda:0",
        "dtype": "bfloat16",
        "attn_implementation": "flash_attention_2",
    }
    assert seen["blend"].strategy == "multi_reference_prompt"
    assert sorted(seen["voice_profiles"]) == ["voice_a", "voice_b"]
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["tts_backend"] == "qwen3_tts"
    assert report["voice_profile_ids"] == ["voice_a", "voice_b"]
    assert report["source_profile_details"] == [
        {
            "voice_profile_id": "voice_a",
            "display_name": "Alice",
            "weight": 0.5,
            "consent_confirmed_by": "local_user",
            "allowed_uses": ["private_agent_voice", "local_audio_export"],
            "reference_text_present": True,
        },
        {
            "voice_profile_id": "voice_b",
            "display_name": "Bob",
            "weight": 0.5,
            "consent_confirmed_by": "local_user",
            "allowed_uses": ["private_agent_voice", "local_audio_export"],
            "reference_text_present": True,
        },
    ]


def test_verify_qwen_runtime_requires_two_profiles(tmp_path: Path):
    exit_code = main(
        [
            "--voice-profile-id",
            "voice_a",
            "--report",
            str(tmp_path / "report.json"),
        ]
    )

    assert exit_code == 2


def test_verify_qwen_runtime_requires_two_distinct_profiles(tmp_path: Path, monkeypatch):
    def fail_if_profiles_load(profile_ids):
        raise AssertionError("duplicate profile ids should be rejected before loading profiles")

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fail_if_profiles_load)
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--voice-profile-id",
            "voice_a",
            "--voice-profile-id",
            "voice_a",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["error"] == "Qwen runtime verification requires at least two distinct voice profile ids."


def test_verify_qwen_runtime_rejects_quality_warnings_before_loading_runtime(
    tmp_path: Path, monkeypatch
):
    def fake_get_profiles(profile_ids):
        return {
            "voice_a": profile(
                "voice_a",
                "Alice",
                "Alice reads the reference text.",
                quality_warnings=["Reference audio appears clipped; record a cleaner sample."],
            ),
            "voice_b": profile("voice_b", "Bob", "Bob reads the reference text."),
        }

    class FailIfQwenLoads:
        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            raise AssertionError("quality warnings should be rejected before loading Qwen")

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fake_get_profiles)
    monkeypatch.setattr("app.cli.verify_qwen_runtime.QwenTtsAdapter", FailIfQwenLoads)
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--voice-profile-id",
            "voice_a",
            "--voice-profile-id",
            "voice_b",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["error"] == "Voice profile voice_a must not have audio quality warnings for Qwen synthesis."


def profile(
    profile_id: str,
    display_name: str,
    reference_text: str,
    quality_warnings: list[str] | None = None,
) -> VoiceProfile:
    resolved_quality_warnings = [] if quality_warnings is None else quality_warnings
    return VoiceProfile.model_validate(
        {
            "id": profile_id,
            "display_name": display_name,
            "reference_text": reference_text,
            "consent": {
                "voice_profile_id": profile_id,
                "speaker_display_name": display_name,
                "consent_type": "self_or_written_permission",
                "allowed_uses": ["private_agent_voice", "local_audio_export"],
                "confirmed_by": "local_user",
                "notes": "Written permission captured.",
                "synthetic_voice_allowed": True,
            },
            "source_audio_path": f"data/voices/{profile_id}/source.wav",
            "cleaned_audio_path": f"data/voices/{profile_id}/source.wav",
            "quality": {
                "file_name": "source.wav",
                "size_bytes": 10,
                "format": "wav",
                "duration_seconds": 5,
                "sample_rate_hz": 16000,
                "channel_count": 1,
                "warnings": resolved_quality_warnings,
            },
        }
    )
