from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ConsentType = Literal["self_or_written_permission"]
BlendStrategy = Literal[
    "adapter_embedding_mix",
    "multi_reference_prompt",
    "segment_ensemble",
    "designed_voice_proxy",
    "local_development_wav",
]


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
    warnings: list[str]


class VoiceProfile(BaseModel):
    id: str
    display_name: str
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


class VoiceBlend(BaseModel):
    id: str = Field(default_factory=lambda: f"blend_{uuid4().hex[:12]}")
    name: str = Field(min_length=1)
    profiles: list[BlendProfile]
    strategy: BlendStrategy
    synthetic_label: str = "synthetic mixed voice"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GenerationResult(BaseModel):
    id: str = Field(default_factory=lambda: f"generation_{uuid4().hex[:12]}")
    audio_path: str
    metadata_path: str
    synthetic_label: str
    source_profile_ids: list[str]
    blend_strategy: BlendStrategy


AgentProviderKind = Literal["openai_compatible", "ollama"]


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

