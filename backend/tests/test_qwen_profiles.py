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
