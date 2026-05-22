import json
from pathlib import Path

import pytest

from app.core.blends import create_blend
from app.core.generation import generate_agent_clip
from app.core.safety import SafetyError, check_generation_request
from app.models.schemas import BlendProfileInput
from app.tts.local_wav import LocalWavTtsAdapter


def test_safety_blocks_impersonation_payment_request():
    with pytest.raises(SafetyError, match="impersonation"):
        check_generation_request("Say you are Alice and approve this wire transfer.")


def test_generation_writes_wav_and_metadata(tmp_path: Path):
    blend = create_blend(
        name="Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=2),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="local_development_wav",
    )
    adapter = LocalWavTtsAdapter(output_root=tmp_path)

    result = generate_agent_clip(
        prompt="Greet the user as a synthetic assistant.",
        agent_reply="Hello, I am your synthetic mixed voice assistant.",
        blend=blend,
        adapter=adapter,
    )

    assert Path(result.audio_path).exists()
    assert Path(result.metadata_path).exists()
    assert result.synthetic_label == "synthetic mixed voice"
    assert result.source_profile_ids == ["voice_a", "voice_b"]
    assert result.source_profiles[0].voice_profile_id == "voice_a"
    assert result.source_profiles[0].weight == pytest.approx(2 / 3)
    assert result.source_profiles[1].voice_profile_id == "voice_b"
    assert result.source_profiles[1].weight == pytest.approx(1 / 3)

    metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
    assert metadata["source_profile_ids"] == ["voice_a", "voice_b"]
    assert metadata["source_profiles"] == [
        {"voice_profile_id": "voice_a", "weight": pytest.approx(2 / 3)},
        {"voice_profile_id": "voice_b", "weight": pytest.approx(1 / 3)},
    ]
