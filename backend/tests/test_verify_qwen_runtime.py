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
        def from_pretrained(cls, output_root=None):
            seen["output_root"] = output_root
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
        ]
    )

    assert exit_code == 0
    assert seen["profile_ids"] == ["voice_a", "voice_b"]
    assert seen["text"] == "This is a Qwen runtime verification."
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


def profile(profile_id: str, display_name: str, reference_text: str) -> VoiceProfile:
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
                "warnings": [],
            },
        }
    )
