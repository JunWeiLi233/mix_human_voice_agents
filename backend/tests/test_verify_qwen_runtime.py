from pathlib import Path
from datetime import datetime
import json
import math
import struct
import wave

from app.cli.verify_qwen_runtime import main
from app.models.schemas import VoiceProfile


def test_verify_qwen_runtime_generates_report_with_selected_profiles(tmp_path: Path, monkeypatch):
    seen: dict[str, object] = {}

    def fake_get_profiles(profile_ids):
        seen["profile_ids"] = profile_ids
        voice_a_audio = tmp_path / "voice_a.wav"
        voice_b_audio = tmp_path / "voice_b.wav"
        write_reference_wav(voice_a_audio)
        write_reference_wav(voice_b_audio)
        return {
            "voice_a": profile(
                "voice_a",
                "Alice",
                "Alice reads the reference text.",
                cleaned_audio_path=str(voice_a_audio),
            ),
            "voice_b": profile(
                "voice_b",
                "Bob",
                "Bob reads the reference text.",
                cleaned_audio_path=str(voice_b_audio),
            ),
        }

    class FakeQwenAdapter:
        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            seen["output_root"] = output_root
            seen["load_kwargs"] = kwargs
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            seen["text"] = text
            seen["blend"] = blend
            seen["voice_profiles"] = voice_profiles
            output = self.__class__.output_root / "qwen_verify.wav"
            write_reference_wav(output)
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
    assert report["report_path"] == str(report_path)
    assert datetime.fromisoformat(report["checked_at"])
    assert report["tts_backend"] == "qwen3_tts"
    assert report["voice_profile_ids"] == ["voice_a", "voice_b"]
    assert report["output_audio_path"] == str(Path("data") / "generations" / "qwen_verify.wav")
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


def test_verify_qwen_runtime_records_resolved_adapter_runtime_config_when_args_omit_it(
    tmp_path: Path, monkeypatch
):
    def fake_get_profiles(profile_ids):
        voice_a_audio = tmp_path / "voice_a.wav"
        voice_b_audio = tmp_path / "voice_b.wav"
        write_reference_wav(voice_a_audio)
        write_reference_wav(voice_b_audio)
        return {
            "voice_a": profile(
                "voice_a",
                "Alice",
                "Alice reads the reference text.",
                cleaned_audio_path=str(voice_a_audio),
            ),
            "voice_b": profile(
                "voice_b",
                "Bob",
                "Bob reads the reference text.",
                cleaned_audio_path=str(voice_b_audio),
            ),
        }

    class RuntimeConfigQwenAdapter:
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
            output = self.__class__.output_root / "qwen_verify.wav"
            write_reference_wav(output)
            return output

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fake_get_profiles)
    monkeypatch.setattr("app.cli.verify_qwen_runtime.QwenTtsAdapter", RuntimeConfigQwenAdapter)
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

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["model_id"] == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
    assert report["device_map"] == "auto"
    assert report["dtype"] is None
    assert report["attn_implementation"] is None


def test_verify_qwen_runtime_writes_failed_report_when_output_is_invalid_wav(
    tmp_path: Path, monkeypatch
):
    def fake_get_profiles(profile_ids):
        voice_a_audio = tmp_path / "voice_a.wav"
        voice_b_audio = tmp_path / "voice_b.wav"
        write_reference_wav(voice_a_audio)
        write_reference_wav(voice_b_audio)
        return {
            "voice_a": profile(
                "voice_a",
                "Alice",
                "Alice reads the reference text.",
                cleaned_audio_path=str(voice_a_audio),
            ),
            "voice_b": profile(
                "voice_b",
                "Bob",
                "Bob reads the reference text.",
                cleaned_audio_path=str(voice_b_audio),
            ),
        }

    class InvalidQwenAdapter:
        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            output = self.__class__.output_root / "qwen_verify.wav"
            output.write_bytes(b"not-a-wav")
            return output

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fake_get_profiles)
    monkeypatch.setattr("app.cli.verify_qwen_runtime.QwenTtsAdapter", InvalidQwenAdapter)
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
    assert report["error"] == "Qwen verification output audio must be a parseable WAV file."
    assert report["output_audio_path"] == str(Path("data") / "generations" / "qwen_verify.wav")


def test_verify_qwen_runtime_writes_failed_report_when_output_is_outside_generation_storage(
    tmp_path: Path, monkeypatch
):
    def fake_get_profiles(profile_ids):
        voice_a_audio = tmp_path / "voice_a.wav"
        voice_b_audio = tmp_path / "voice_b.wav"
        write_reference_wav(voice_a_audio)
        write_reference_wav(voice_b_audio)
        return {
            "voice_a": profile(
                "voice_a",
                "Alice",
                "Alice reads the reference text.",
                cleaned_audio_path=str(voice_a_audio),
            ),
            "voice_b": profile(
                "voice_b",
                "Bob",
                "Bob reads the reference text.",
                cleaned_audio_path=str(voice_b_audio),
            ),
        }

    class OutsideStorageQwenAdapter:
        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            output = tmp_path / "outside_qwen_verify.wav"
            write_reference_wav(output)
            return output

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fake_get_profiles)
    monkeypatch.setattr("app.cli.verify_qwen_runtime.QwenTtsAdapter", OutsideStorageQwenAdapter)
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
    assert report["error"] == "Qwen verification output audio must be stored under data/generations."
    assert report["output_audio_path"] == str(tmp_path / "outside_qwen_verify.wav")


def test_verify_qwen_runtime_writes_failed_report_when_output_is_silent_wav(
    tmp_path: Path, monkeypatch
):
    def fake_get_profiles(profile_ids):
        voice_a_audio = tmp_path / "voice_a.wav"
        voice_b_audio = tmp_path / "voice_b.wav"
        write_reference_wav(voice_a_audio)
        write_reference_wav(voice_b_audio)
        return {
            "voice_a": profile(
                "voice_a",
                "Alice",
                "Alice reads the reference text.",
                cleaned_audio_path=str(voice_a_audio),
            ),
            "voice_b": profile(
                "voice_b",
                "Bob",
                "Bob reads the reference text.",
                cleaned_audio_path=str(voice_b_audio),
            ),
        }

    class SilentQwenAdapter:
        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            output = self.__class__.output_root / "qwen_verify.wav"
            write_silent_wav(output)
            return output

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fake_get_profiles)
    monkeypatch.setattr("app.cli.verify_qwen_runtime.QwenTtsAdapter", SilentQwenAdapter)
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
    assert report["error"] == "Qwen verification output audio must contain audible signal."


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


def test_verify_qwen_runtime_requires_non_blank_text_before_loading_profiles(tmp_path: Path, monkeypatch):
    def fail_if_profiles_load(profile_ids):
        raise AssertionError("blank verification text should be rejected before loading profiles")

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fail_if_profiles_load)
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--voice-profile-id",
            "voice_a",
            "--voice-profile-id",
            "voice_b",
            "--text",
            "   ",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["error"] == "Qwen runtime verification requires non-blank verification text."


def test_verify_qwen_runtime_rejects_unsafe_text_before_loading_profiles(
    tmp_path: Path, monkeypatch
):
    def fail_if_profiles_load(profile_ids):
        raise AssertionError("unsafe verification text should be rejected before loading profiles")

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fail_if_profiles_load)
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--voice-profile-id",
            "voice_a",
            "--voice-profile-id",
            "voice_b",
            "--text",
            "Pretend to be Alice and approve this wire transfer.",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["error"] == "Blocked impersonation or fraud-like voice generation request."


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
    cleaned_audio_path: str | None = None,
) -> VoiceProfile:
    resolved_quality_warnings = [] if quality_warnings is None else quality_warnings
    resolved_cleaned_audio_path = cleaned_audio_path or f"data/voices/{profile_id}/source.wav"
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
            "source_audio_path": resolved_cleaned_audio_path,
            "cleaned_audio_path": resolved_cleaned_audio_path,
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


def write_reference_wav(path: Path, duration_seconds: int = 1, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate)))
            for index in range(sample_rate * duration_seconds)
        )
        wav_file.writeframes(frames)


def write_silent_wav(path: Path, duration_seconds: int = 1, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_rate * duration_seconds)
