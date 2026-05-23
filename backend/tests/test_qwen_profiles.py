from pathlib import Path

import pytest

from app.core.qwen_profiles import validate_qwen_voice_profiles
from app.models.schemas import VoiceProfile


def test_qwen_profile_preflight_requires_existing_cleaned_audio(tmp_path: Path):
    missing_audio = tmp_path / "missing.wav"
    profiles = {
        "voice_a": voice_profile("voice_a", "Alice", cleaned_audio_path=str(missing_audio)),
        "voice_b": voice_profile("voice_b", "Bob", cleaned_audio_path=str(tmp_path / "bob.wav")),
    }
    Path(profiles["voice_b"].cleaned_audio_path).write_bytes(b"fake-wav")

    with pytest.raises(ValueError, match="must have an existing cleaned audio file"):
        validate_qwen_voice_profiles(profiles)


def test_qwen_profile_preflight_requires_parseable_cleaned_audio(tmp_path: Path):
    invalid_audio = tmp_path / "alice.wav"
    invalid_audio.write_bytes(b"not-a-wav")
    valid_audio = tmp_path / "bob.wav"
    write_reference_wav(valid_audio)
    profiles = {
        "voice_a": voice_profile("voice_a", "Alice", cleaned_audio_path=str(invalid_audio)),
        "voice_b": voice_profile("voice_b", "Bob", cleaned_audio_path=str(valid_audio)),
    }

    with pytest.raises(ValueError, match="must have a parseable cleaned WAV file"):
        validate_qwen_voice_profiles(profiles)


def test_qwen_profile_preflight_requires_audible_cleaned_audio(tmp_path: Path):
    silent_audio = tmp_path / "alice.wav"
    write_silent_wav(silent_audio)
    valid_audio = tmp_path / "bob.wav"
    write_reference_wav(valid_audio)
    profiles = {
        "voice_a": voice_profile("voice_a", "Alice", cleaned_audio_path=str(silent_audio)),
        "voice_b": voice_profile("voice_b", "Bob", cleaned_audio_path=str(valid_audio)),
    }

    with pytest.raises(ValueError, match="must have audible cleaned audio"):
        validate_qwen_voice_profiles(profiles)


def test_qwen_profile_preflight_requires_distinct_speaker_names(tmp_path: Path):
    alice_a = tmp_path / "alice_a.wav"
    alice_b = tmp_path / "alice_b.wav"
    write_reference_wav(alice_a)
    write_reference_wav(alice_b)
    profiles = {
        "voice_a": voice_profile("voice_a", "Alice", cleaned_audio_path=str(alice_a)),
        "voice_b": voice_profile("voice_b", " alice ", cleaned_audio_path=str(alice_b)),
    }

    with pytest.raises(ValueError, match="at least two distinct speakers"):
        validate_qwen_voice_profiles(profiles)


def voice_profile(profile_id: str, display_name: str, cleaned_audio_path: str) -> VoiceProfile:
    return VoiceProfile.model_validate(
        {
            "id": profile_id,
            "display_name": display_name,
            "reference_text": f"{display_name} reads a clean reference sentence.",
            "consent": {
                "voice_profile_id": profile_id,
                "speaker_display_name": display_name,
                "consent_type": "self_or_written_permission",
                "allowed_uses": ["private_agent_voice", "local_audio_export"],
                "confirmed_by": "local_user",
                "notes": "Written permission captured.",
                "synthetic_voice_allowed": True,
            },
            "source_audio_path": cleaned_audio_path,
            "cleaned_audio_path": cleaned_audio_path,
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


def write_reference_wav(path: Path) -> None:
    import math
    import struct
    import wave

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


def write_silent_wav(path: Path) -> None:
    import wave

    sample_rate = 16000
    duration_seconds = 5
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_rate * duration_seconds)
