from pathlib import Path
import wave

import pytest

from app.core.audio import AudioQualityError, analyze_audio_sample
from app.core.consent import ConsentError, create_consent_record
from app.models.schemas import ConsentRequest


def test_consent_record_requires_permission_scope():
    request = ConsentRequest(
        speaker_display_name="Alice",
        consent_type="self_or_written_permission",
        allowed_uses=[],
        confirmed_by="local_user",
        notes="",
    )

    with pytest.raises(ConsentError, match="allowed use"):
        create_consent_record("voice_a", request)


def test_consent_record_contains_synthetic_safe_scope():
    request = ConsentRequest(
        speaker_display_name="Alice",
        consent_type="self_or_written_permission",
        allowed_uses=["private_agent_voice", "local_audio_export"],
        confirmed_by="local_user",
        notes="voice owner approved local private use",
    )

    record = create_consent_record("voice_a", request)

    assert record.voice_profile_id == "voice_a"
    assert record.synthetic_voice_allowed is True
    assert "local_audio_export" in record.allowed_uses


def test_audio_analysis_rejects_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.wav"

    with pytest.raises(FileNotFoundError):
        analyze_audio_sample(missing)


def test_audio_analysis_rejects_invalid_wav(tmp_path: Path):
    invalid = tmp_path / "sample.wav"
    invalid.write_bytes(b"not a wav")

    with pytest.raises(AudioQualityError, match="WAV header"):
        analyze_audio_sample(invalid)


def test_audio_analysis_accepts_clean_reference_wav(tmp_path: Path):
    sample = tmp_path / "sample.wav"
    write_reference_wav(sample)

    quality = analyze_audio_sample(sample)

    assert quality.format == "wav"
    assert quality.duration_seconds == 5
    assert quality.warnings == []


def write_reference_wav(path: Path, duration_seconds: int = 5, sample_rate: int = 16000) -> None:
    frames = b"\x00\x00" * sample_rate * duration_seconds
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
