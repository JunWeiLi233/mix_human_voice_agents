from pathlib import Path
import sys
import types

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


def profile(profile_id: str, audio_path: Path, reference_text: str = "") -> VoiceProfile:
    return VoiceProfile.model_validate(
        {
            "id": profile_id,
            "display_name": profile_id,
            "reference_text": reference_text,
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
            "voice_a": profile("voice_a", audio_a, "Alice reference transcript."),
            "voice_b": profile("voice_b", audio_b, "Bob reference transcript."),
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


def test_qwen_adapter_uses_imported_reference_text_for_clone_prompt(tmp_path: Path):
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
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="multi_reference_prompt",
    )

    adapter.synthesize(
        text="Hello from a cloned blend.",
        blend=blend,
        voice_profiles={
            "voice_a": profile("voice_a", audio_a, "Alice says the first reference sentence."),
            "voice_b": profile("voice_b", audio_b, "Bob says the second reference sentence."),
        },
    )

    assert [call["ref_text"] for call in fake_model.prompt_calls] == [
        "Alice says the first reference sentence.",
        "Bob says the second reference sentence.",
    ]


def test_qwen_adapter_loads_model_from_environment_config(monkeypatch, tmp_path: Path):
    seen: dict[str, object] = {}

    class FakeQwen3TTSModel:
        @classmethod
        def from_pretrained(cls, model_id, **kwargs):
            seen["model_id"] = model_id
            seen["kwargs"] = kwargs
            return cls()

    fake_qwen_tts = types.SimpleNamespace(Qwen3TTSModel=FakeQwen3TTSModel)
    fake_torch = types.SimpleNamespace(bfloat16="fake-bfloat16")
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_qwen_tts)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setenv("QWEN_TTS_MODEL_ID", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    monkeypatch.setenv("QWEN_TTS_DEVICE_MAP", "cuda:0")
    monkeypatch.setenv("QWEN_TTS_DTYPE", "bfloat16")
    monkeypatch.setenv("QWEN_TTS_ATTN_IMPLEMENTATION", "flash_attention_2")

    adapter = QwenTtsAdapter.from_pretrained(output_root=tmp_path)

    assert adapter.model is not None
    assert seen == {
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "kwargs": {
            "device_map": "cuda:0",
            "dtype": "fake-bfloat16",
            "attn_implementation": "flash_attention_2",
        },
    }
