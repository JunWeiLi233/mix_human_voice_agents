from pathlib import Path

import pytest

from app.core.audio import analyze_audio_sample
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

