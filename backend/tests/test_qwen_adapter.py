from pathlib import Path

import numpy as np

from app.core.blends import create_blend
from app.models.schemas import BlendProfileInput, VoiceProfile
from app.tts.qwen import QwenTtsAdapter


class FakeQwenModel:
    def __init__(self):
        self.prompt_calls = []
        self.generate_calls = []

    def create_voice_clone_prompt(self, ref_audio, ref_text, x_vector_only_mode=False):
        self.prompt_calls.append(
            {
                "ref_audio": ref_audio,
                "ref_text": ref_text,
                "x_vector_only_mode": x_vector_only_mode,
            }
        )
        return {"prompt": Path(ref_audio).stem, "text": ref_text}

    def generate_voice_clone(self, text, language, voice_clone_prompt):
        self.generate_calls.append(
            {
                "text": text,
                "language": language,
                "voice_clone_prompt": voice_clone_prompt,
            }
        )
        value = 0.25 if voice_clone_prompt["prompt"] == "a" else 0.75
        return [np.full(1600, value, dtype=np.float32)], 16000


def profile(profile_id: str, audio_path: Path) -> VoiceProfile:
    return VoiceProfile.model_validate(
        {
            "id": profile_id,
            "display_name": profile_id,
            "consent": {
                "voice_profile_id": profile_id,
                "speaker_display_name": profile_id,
                "consent_type": "self_or_written_permission",
                "allowed_uses": ["private_agent_voice"],
                "confirmed_by": "local_user",
                "notes": "",
                "synthetic_voice_allowed": True,
            },
            "source_audio_path": str(audio_path),
            "cleaned_audio_path": str(audio_path),
            "quality": {
                "file_name": audio_path.name,
                "size_bytes": 10,
                "format": "wav",
                "duration_seconds": 5,
                "warnings": [],
            },
        }
    )


def test_qwen_adapter_mixes_each_source_profile_by_weight(tmp_path: Path):
    audio_a = tmp_path / "a.wav"
    audio_b = tmp_path / "b.wav"
    audio_a.write_bytes(b"fake-audio-a")
    audio_b.write_bytes(b"fake-audio-b")
    fake_model = FakeQwenModel()
    adapter = QwenTtsAdapter(model=fake_model, output_root=tmp_path)
    blend = create_blend(
        name="Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=3),
        ],
        strategy="multi_reference_prompt",
    )

    output = adapter.synthesize(
        text="Hello from a cloned blend.",
        blend=blend,
        voice_profiles={
            "voice_a": profile("voice_a", audio_a),
            "voice_b": profile("voice_b", audio_b),
        },
    )

    assert output.exists()
    mixed, sample_rate = adapter.read_output(output)
    assert sample_rate == 16000
    assert len(fake_model.prompt_calls) == 2
    assert len(fake_model.generate_calls) == 2
    assert fake_model.generate_calls[0]["voice_clone_prompt"]["prompt"] == "a"
    assert fake_model.generate_calls[1]["voice_clone_prompt"]["prompt"] == "b"
    assert float(mixed[0]) == np.float32(0.625)
