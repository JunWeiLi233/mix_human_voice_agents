import json
from pathlib import Path

from app.core.blends import validate_blend
from app.core.audio import is_parseable_wav, wav_has_audible_signal
from app.core.qwen_profiles import validate_qwen_voice_profiles
from app.core.safety import SafetyError, check_generation_request
from app.models.schemas import (
    AgentTrace,
    BlendProfile,
    GenerationResult,
    MetadataWatermark,
    SourceProfileDetail,
    TtsBackend,
    VoiceBlend,
    VoiceProfile,
)
from app.tts.base import TtsAdapter

METADATA_WATERMARK_DISCLOSURE = "Generated audio is synthetic and mixed from consented imported voice profiles."


def generate_agent_clip(
    prompt: str,
    agent_reply: str,
    blend: VoiceBlend,
    adapter: TtsAdapter,
    voice_profiles: dict[str, VoiceProfile] | None = None,
    tts_backend: TtsBackend = "local_development_wav",
    agent_trace: AgentTrace | None = None,
    qwen_runtime_config: dict[str, str | None] | None = None,
) -> GenerationResult:
    validate_blend(blend)
    check_generation_request(prompt)
    check_generation_request(agent_reply)
    if tts_backend == "qwen3_tts":
        _validate_qwen_generation_inputs(blend, voice_profiles, agent_trace)

    audio_path = adapter.synthesize(agent_reply, blend, voice_profiles=voice_profiles)
    if tts_backend == "qwen3_tts":
        _validate_qwen_output_audio(Path(audio_path))
    metadata_path = Path(audio_path).with_suffix(".json")
    result = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        prompt=prompt,
        agent_reply=agent_reply,
        synthetic_label=blend.synthetic_label,
        source_profile_ids=[profile.voice_profile_id for profile in blend.profiles],
        source_profiles=blend.profiles,
        source_profile_details=build_source_profile_details(blend.profiles, voice_profiles),
        blend_strategy=blend.strategy,
        tts_backend=tts_backend,
        qwen_runtime_config=qwen_runtime_config,
        agent_trace=agent_trace,
        watermark=MetadataWatermark(
            label=blend.synthetic_label,
            disclosure=METADATA_WATERMARK_DISCLOSURE,
        ),
    )
    metadata_path.write_text(
        json.dumps(result.model_dump(mode="json", exclude_none=True), indent=2),
        encoding="utf-8",
    )
    return result


def _validate_qwen_generation_inputs(
    blend: VoiceBlend,
    voice_profiles: dict[str, VoiceProfile] | None,
    agent_trace: AgentTrace | None,
) -> None:
    if agent_trace is None:
        raise SafetyError("Qwen generation requires an agent provider trace.")
    if blend.strategy != "multi_reference_prompt":
        raise SafetyError("Qwen generation requires the multi-reference mixed voice strategy.")
    source_ids = [profile.voice_profile_id for profile in blend.profiles]
    if not voice_profiles:
        raise SafetyError("Qwen generation requires imported voice profiles for each blend source.")
    missing_ids = [voice_id for voice_id in source_ids if voice_id not in voice_profiles]
    if missing_ids:
        raise SafetyError(
            "Qwen generation requires imported voice profiles for each blend source: "
            + ", ".join(missing_ids)
        )
    try:
        validate_qwen_voice_profiles({voice_id: voice_profiles[voice_id] for voice_id in source_ids})
    except ValueError as exc:
        raise SafetyError(str(exc)) from exc


def _validate_qwen_output_audio(audio_path: Path) -> None:
    if not audio_path.exists():
        raise SafetyError("Qwen generation output audio is missing.")
    if audio_path.stat().st_size == 0:
        raise SafetyError("Qwen generation output audio must be non-empty.")
    if not is_parseable_wav(audio_path):
        raise SafetyError("Qwen generation output audio must be a parseable WAV file.")
    if not wav_has_audible_signal(audio_path):
        raise SafetyError("Qwen generation output audio must contain audible signal.")


def build_source_profile_details(
    blend_profiles: list[BlendProfile],
    voice_profiles: dict[str, VoiceProfile] | None,
) -> list[SourceProfileDetail]:
    if not voice_profiles:
        return []

    details: list[SourceProfileDetail] = []
    for blend_profile in blend_profiles:
        voice_profile = voice_profiles.get(blend_profile.voice_profile_id)
        if voice_profile is None:
            continue
        details.append(
            SourceProfileDetail(
                voice_profile_id=blend_profile.voice_profile_id,
                display_name=voice_profile.display_name,
                weight=blend_profile.weight,
                consent_confirmed_by=voice_profile.consent.confirmed_by,
                allowed_uses=voice_profile.consent.allowed_uses,
                reference_text_present=bool(voice_profile.reference_text.strip()),
            )
        )
    return details
