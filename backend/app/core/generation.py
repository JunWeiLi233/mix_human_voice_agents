import json
from pathlib import Path

from app.core.blends import validate_blend
from app.core.safety import check_generation_request
from app.models.schemas import GenerationResult, MetadataWatermark, TtsBackend, VoiceBlend, VoiceProfile
from app.tts.base import TtsAdapter

METADATA_WATERMARK_DISCLOSURE = "Generated audio is synthetic and mixed from consented imported voice profiles."


def generate_agent_clip(
    prompt: str,
    agent_reply: str,
    blend: VoiceBlend,
    adapter: TtsAdapter,
    voice_profiles: dict[str, VoiceProfile] | None = None,
    tts_backend: TtsBackend = "local_development_wav",
) -> GenerationResult:
    validate_blend(blend)
    check_generation_request(prompt)
    check_generation_request(agent_reply)

    audio_path = adapter.synthesize(agent_reply, blend, voice_profiles=voice_profiles)
    metadata_path = Path(audio_path).with_suffix(".json")
    result = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        synthetic_label=blend.synthetic_label,
        source_profile_ids=[profile.voice_profile_id for profile in blend.profiles],
        source_profiles=blend.profiles,
        blend_strategy=blend.strategy,
        tts_backend=tts_backend,
        watermark=MetadataWatermark(
            label=blend.synthetic_label,
            disclosure=METADATA_WATERMARK_DISCLOSURE,
        ),
    )
    metadata_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return result
