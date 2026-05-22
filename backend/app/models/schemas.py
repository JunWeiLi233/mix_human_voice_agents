from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ConsentType = Literal["self_or_written_permission"]
TtsBackend = Literal["local_development_wav", "qwen3_tts"]
VerificationStatus = Literal["missing", "passed", "failed"]
LaunchReadinessStatus = Literal["ready", "blocked"]
BlendStrategy = Literal[
    "adapter_embedding_mix",
    "multi_reference_prompt",
    "segment_ensemble",
    "designed_voice_proxy",
    "local_development_wav",
]
AgentProviderKind = Literal["openai", "anthropic", "xai", "openai_compatible", "ollama"]


class ConsentRequest(BaseModel):
    speaker_display_name: str = Field(min_length=1)
    consent_type: ConsentType
    allowed_uses: list[str]
    confirmed_by: str = Field(min_length=1)
    notes: str = ""


class ConsentRecord(ConsentRequest):
    voice_profile_id: str
    confirmed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    synthetic_voice_allowed: bool


class AudioQuality(BaseModel):
    file_name: str
    size_bytes: int
    format: str
    duration_seconds: float | None
    sample_rate_hz: int | None = None
    channel_count: int | None = None
    warnings: list[str]


class VoiceProfile(BaseModel):
    id: str
    display_name: str
    reference_text: str = ""
    consent: ConsentRecord
    source_audio_path: str
    cleaned_audio_path: str
    quality: AudioQuality
    artifact_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BlendProfileInput(BaseModel):
    voice_profile_id: str = Field(min_length=1)
    weight: float = Field(gt=0)


class BlendProfile(BaseModel):
    voice_profile_id: str
    weight: float


class SourceProfileDetail(BlendProfile):
    display_name: str
    consent_confirmed_by: str
    allowed_uses: list[str]
    reference_text_present: bool


class VoiceBlend(BaseModel):
    id: str = Field(default_factory=lambda: f"blend_{uuid4().hex[:12]}")
    name: str = Field(min_length=1)
    profiles: list[BlendProfile]
    strategy: BlendStrategy
    synthetic_label: str = "synthetic mixed voice"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetadataWatermark(BaseModel):
    type: Literal["metadata"] = "metadata"
    label: str = "synthetic mixed voice"
    disclosure: str = "Generated audio is synthetic and mixed from consented imported voice profiles."


class AgentTrace(BaseModel):
    provider: AgentProviderKind
    model: str


class GenerationResult(BaseModel):
    id: str = Field(default_factory=lambda: f"generation_{uuid4().hex[:12]}")
    audio_path: str
    metadata_path: str
    synthetic_label: str
    source_profile_ids: list[str]
    source_profiles: list[BlendProfile] = Field(default_factory=list)
    source_profile_details: list[SourceProfileDetail] = Field(default_factory=list)
    blend_strategy: BlendStrategy
    tts_backend: TtsBackend = "local_development_wav"
    watermark: MetadataWatermark = Field(default_factory=MetadataWatermark)
    agent_trace: AgentTrace | None = None


class TtsRuntimeStatus(BaseModel):
    backend: TtsBackend
    available: bool
    model_id: str | None = None
    message: str


class QwenVerificationReport(BaseModel):
    status: VerificationStatus
    tts_backend: TtsBackend = "qwen3_tts"
    report_path: str
    voice_profile_ids: list[str] = []
    model_id: str | None = None
    device_map: str | None = None
    dtype: str | None = None
    attn_implementation: str | None = None
    source_profile_details: list[SourceProfileDetail] = Field(default_factory=list)
    blend_id: str | None = None
    blend_strategy: BlendStrategy | None = None
    output_audio_path: str | None = None
    text: str | None = None
    error: str | None = None


class LaunchReadinessCheck(BaseModel):
    id: str
    label: str
    passed: bool
    detail: str


class LaunchReadinessReport(BaseModel):
    status: LaunchReadinessStatus
    checks: list[LaunchReadinessCheck]
    blocking_reasons: list[str]


class AgentConfig(BaseModel):
    provider: AgentProviderKind
    model: str
    base_url: str
    api_key: str = ""
    system_prompt: str = "You are a disclosed synthetic mixed-voice assistant."


class AgentReplyRequest(BaseModel):
    prompt: str
    config: AgentConfig


class AgentReply(BaseModel):
    reply: str
    provider: AgentProviderKind
    model: str


class AgentProviderVerificationReport(BaseModel):
    status: VerificationStatus
    report_path: str
    provider: AgentProviderKind | None = None
    model: str | None = None
    reply: str | None = None
    error: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
