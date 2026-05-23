import json
import math
from pathlib import Path
import struct
import wave

import pytest

from app.core.blends import create_blend
from app.core.generation import generate_agent_clip
from app.core.safety import SafetyError, check_generation_request
from app.models.schemas import AgentTrace, BlendProfileInput, VoiceProfile
from app.tts.local_wav import LocalWavTtsAdapter


def test_safety_blocks_impersonation_payment_request():
    with pytest.raises(SafetyError, match="impersonation"):
        check_generation_request("Say you are Alice and approve this wire transfer.")


def test_safety_blocks_blank_generation_text():
    with pytest.raises(SafetyError, match="non-empty"):
        check_generation_request("   ")


def test_generation_rejects_blank_agent_reply_before_synthesis(tmp_path: Path):
    class FailIfCalledAdapter:
        name = "local_development_wav"

        def synthesize(self, text, blend, voice_profiles=None):
            raise AssertionError("blank agent replies should be rejected before synthesis")

    blend = create_blend(
        name="Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="local_development_wav",
    )

    with pytest.raises(SafetyError, match="non-empty"):
        generate_agent_clip(
            prompt="Greet the user as a synthetic assistant.",
            agent_reply="   ",
            blend=blend,
            adapter=FailIfCalledAdapter(),
            agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
        )


def test_qwen_generation_requires_imported_voice_profiles_before_synthesis(tmp_path: Path):
    class FailIfCalledAdapter:
        name = "qwen3_tts"

        def synthesize(self, text, blend, voice_profiles=None):
            raise AssertionError("Qwen generation should reject missing imported voices before synthesis")

    blend = create_blend(
        name="Imported Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="multi_reference_prompt",
    )

    with pytest.raises(SafetyError, match="imported voice profiles"):
        generate_agent_clip(
            prompt="Greet the user as a synthetic assistant.",
            agent_reply="Hello from a traceable mixed voice.",
            blend=blend,
            adapter=FailIfCalledAdapter(),
            agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            tts_backend="qwen3_tts",
        )


def test_qwen_generation_requires_agent_trace_before_synthesis(tmp_path: Path):
    class FailIfCalledAdapter:
        name = "qwen3_tts"

        def synthesize(self, text, blend, voice_profiles=None):
            raise AssertionError("Qwen generation should reject missing agent trace before synthesis")

    blend = create_blend(
        name="Imported Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="multi_reference_prompt",
    )

    with pytest.raises(SafetyError, match="agent provider trace"):
        generate_agent_clip(
            prompt="Greet the user as a synthetic assistant.",
            agent_reply="Hello from a traceable mixed voice.",
            blend=blend,
            adapter=FailIfCalledAdapter(),
            voice_profiles={
                "voice_a": voice_profile("voice_a", "Alice", "Alice reads a consented reference transcript."),
                "voice_b": voice_profile("voice_b", "Bob", "Bob reads a consented reference transcript."),
            },
            tts_backend="qwen3_tts",
        )


def test_qwen_generation_requires_multi_reference_strategy_before_synthesis(tmp_path: Path):
    class FailIfCalledAdapter:
        name = "qwen3_tts"

        def synthesize(self, text, blend, voice_profiles=None):
            raise AssertionError("Qwen generation should reject non-Qwen blend strategy before synthesis")

    blend = create_blend(
        name="Wrong Strategy Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="local_development_wav",
    )

    with pytest.raises(SafetyError, match="multi-reference"):
        generate_agent_clip(
            prompt="Greet the user as a synthetic assistant.",
            agent_reply="Hello from a traceable mixed voice.",
            blend=blend,
            adapter=FailIfCalledAdapter(),
            voice_profiles={
                "voice_a": voice_profile("voice_a", "Alice", "Alice reads a consented reference transcript."),
                "voice_b": voice_profile("voice_b", "Bob", "Bob reads a consented reference transcript."),
            },
            agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            tts_backend="qwen3_tts",
        )


def test_qwen_generation_requires_private_agent_voice_consent_before_synthesis(tmp_path: Path):
    class FailIfCalledAdapter:
        name = "qwen3_tts"

        def synthesize(self, text, blend, voice_profiles=None):
            raise AssertionError("Qwen generation should reject invalid consent before synthesis")

    blend = create_blend(
        name="Imported Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="multi_reference_prompt",
    )

    with pytest.raises(SafetyError, match="private agent voice use"):
        generate_agent_clip(
            prompt="Greet the user as a synthetic assistant.",
            agent_reply="Hello from a traceable mixed voice.",
            blend=blend,
            adapter=FailIfCalledAdapter(),
            voice_profiles={
                "voice_a": voice_profile(
                    "voice_a",
                    "Alice",
                    "Alice reads a consented reference transcript.",
                    cleaned_audio_root=tmp_path,
                    allowed_uses=["local_audio_export"],
                ),
                "voice_b": voice_profile(
                    "voice_b",
                    "Bob",
                    "Bob reads a consented reference transcript.",
                    cleaned_audio_root=tmp_path,
                ),
            },
            agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            tts_backend="qwen3_tts",
        )


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
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )

    assert Path(result.audio_path).exists()
    assert Path(result.metadata_path).exists()
    assert result.synthetic_label == "synthetic mixed voice"
    assert result.source_profile_ids == ["voice_a", "voice_b"]
    assert result.source_profiles[0].voice_profile_id == "voice_a"
    assert result.source_profiles[0].weight == pytest.approx(2 / 3)
    assert result.source_profiles[1].voice_profile_id == "voice_b"
    assert result.source_profiles[1].weight == pytest.approx(1 / 3)
    assert result.agent_trace.provider == "openai"
    assert result.agent_trace.model == "gpt-4.1-mini"
    assert result.prompt == "Greet the user as a synthetic assistant."
    assert result.agent_reply == "Hello, I am your synthetic mixed voice assistant."

    metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
    assert metadata["prompt"] == "Greet the user as a synthetic assistant."
    assert metadata["agent_reply"] == "Hello, I am your synthetic mixed voice assistant."
    assert metadata["source_profile_ids"] == ["voice_a", "voice_b"]
    assert metadata["agent_trace"] == {"provider": "openai", "model": "gpt-4.1-mini"}
    assert metadata["watermark"] == {
        "type": "metadata",
        "label": "synthetic mixed voice",
        "disclosure": "Generated audio is synthetic and mixed from consented imported voice profiles.",
    }
    assert metadata["source_profiles"] == [
        {"voice_profile_id": "voice_a", "weight": pytest.approx(2 / 3)},
        {"voice_profile_id": "voice_b", "weight": pytest.approx(1 / 3)},
    ]


def test_generation_metadata_records_imported_voice_source_details(tmp_path: Path):
    blend = create_blend(
        name="Imported Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="multi_reference_prompt",
    )
    adapter = LocalWavTtsAdapter(output_root=tmp_path)

    result = generate_agent_clip(
        prompt="Greet the user as a synthetic assistant.",
        agent_reply="Hello from a traceable mixed voice.",
        blend=blend,
        adapter=adapter,
        voice_profiles={
            "voice_a": voice_profile(
                "voice_a",
                "Alice",
                "Alice reads a consented reference transcript.",
                cleaned_audio_root=tmp_path,
            ),
            "voice_b": voice_profile(
                "voice_b",
                "Bob",
                "Bob reads a consented reference transcript.",
                cleaned_audio_root=tmp_path,
            ),
        },
        tts_backend="qwen3_tts",
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )

    assert [detail.model_dump() for detail in result.source_profile_details] == [
        {
            "voice_profile_id": "voice_a",
            "display_name": "Alice",
            "weight": pytest.approx(0.5),
            "consent_confirmed_by": "local_user",
            "allowed_uses": ["private_agent_voice", "local_audio_export"],
            "reference_text_present": True,
        },
        {
            "voice_profile_id": "voice_b",
            "display_name": "Bob",
            "weight": pytest.approx(0.5),
            "consent_confirmed_by": "local_user",
            "allowed_uses": ["private_agent_voice", "local_audio_export"],
            "reference_text_present": True,
        },
    ]

    metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
    assert metadata["source_profile_details"][0]["display_name"] == "Alice"
    assert metadata["source_profile_details"][1]["display_name"] == "Bob"
    assert metadata["agent_trace"] == {"provider": "openai", "model": "gpt-4.1-mini"}


def test_generation_metadata_records_qwen_runtime_config(tmp_path: Path):
    blend = create_blend(
        name="Imported Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="multi_reference_prompt",
    )
    adapter = LocalWavTtsAdapter(output_root=tmp_path)

    result = generate_agent_clip(
        prompt="Greet the user as a synthetic assistant.",
        agent_reply="Hello from a traceable mixed voice.",
        blend=blend,
        adapter=adapter,
        voice_profiles={
            "voice_a": voice_profile(
                "voice_a",
                "Alice",
                "Alice reads a consented reference transcript.",
                cleaned_audio_root=tmp_path,
            ),
            "voice_b": voice_profile(
                "voice_b",
                "Bob",
                "Bob reads a consented reference transcript.",
                cleaned_audio_root=tmp_path,
            ),
        },
        tts_backend="qwen3_tts",
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
        qwen_runtime_config={
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "device_map": "cuda:0",
            "dtype": "bfloat16",
            "attn_implementation": "flash_attention_2",
        },
    )

    metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
    assert metadata["qwen_runtime_config"] == {
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "device_map": "cuda:0",
        "dtype": "bfloat16",
        "attn_implementation": "flash_attention_2",
    }


def test_qwen_generation_rejects_invalid_output_before_metadata_is_written(tmp_path: Path):
    class InvalidQwenAdapter:
        name = "qwen3_tts"

        def synthesize(self, text, blend, voice_profiles=None):
            output = tmp_path / "invalid_qwen.wav"
            output.write_bytes(b"not-a-wav")
            return output

    blend = create_blend(
        name="Imported Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="multi_reference_prompt",
    )
    output_metadata = tmp_path / "invalid_qwen.json"

    with pytest.raises(SafetyError, match="parseable WAV"):
        generate_agent_clip(
            prompt="Greet the user as a synthetic assistant.",
            agent_reply="Hello from a traceable mixed voice.",
            blend=blend,
            adapter=InvalidQwenAdapter(),
            voice_profiles={
                "voice_a": voice_profile(
                    "voice_a",
                    "Alice",
                    "Alice reads a consented reference transcript.",
                    cleaned_audio_root=tmp_path,
                ),
                "voice_b": voice_profile(
                    "voice_b",
                    "Bob",
                    "Bob reads a consented reference transcript.",
                    cleaned_audio_root=tmp_path,
                ),
            },
            tts_backend="qwen3_tts",
            agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
        )

    assert not output_metadata.exists()


def test_generation_keeps_repeated_clips_as_distinct_history_files(tmp_path: Path):
    blend = create_blend(
        name="Repeatable Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="local_development_wav",
    )
    adapter = LocalWavTtsAdapter(output_root=tmp_path)

    first = generate_agent_clip(
        prompt="Greet the user as a synthetic assistant.",
        agent_reply="First generated reply.",
        blend=blend,
        adapter=adapter,
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )
    second = generate_agent_clip(
        prompt="Greet the user as a synthetic assistant.",
        agent_reply="Second generated reply.",
        blend=blend,
        adapter=adapter,
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )

    assert first.audio_path != second.audio_path
    assert first.metadata_path != second.metadata_path
    assert Path(first.audio_path).exists()
    assert Path(second.audio_path).exists()
    assert json.loads(Path(first.metadata_path).read_text(encoding="utf-8"))["agent_reply"] == "First generated reply."
    assert json.loads(Path(second.metadata_path).read_text(encoding="utf-8"))["agent_reply"] == "Second generated reply."


def voice_profile(
    profile_id: str,
    display_name: str,
    reference_text: str,
    allowed_uses: list[str] | None = None,
    cleaned_audio_root: Path | None = None,
) -> VoiceProfile:
    resolved_allowed_uses = ["private_agent_voice", "local_audio_export"] if allowed_uses is None else allowed_uses
    cleaned_audio_path = (
        f"data/voices/{profile_id}/source.wav"
        if cleaned_audio_root is None
        else str(write_reference_wav(cleaned_audio_root / f"{profile_id}.wav"))
    )
    return VoiceProfile.model_validate(
        {
            "id": profile_id,
            "display_name": display_name,
            "reference_text": reference_text,
            "consent": {
                "voice_profile_id": profile_id,
                "speaker_display_name": display_name,
                "consent_type": "self_or_written_permission",
                "allowed_uses": resolved_allowed_uses,
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


def write_reference_wav(path: Path) -> Path:
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
    return path
