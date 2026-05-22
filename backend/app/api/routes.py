from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.agent import AgentProviderError, generate_agent_reply_record
from app.core.audio import analyze_audio_sample
from app.core.blends import BlendError, create_blend
from app.core.consent import ConsentError, create_consent_record
from app.core.generation import generate_agent_clip
from app.core.safety import SafetyError
from app.core.storage import GENERATION_ROOT, ensure_storage, list_voice_profiles, new_voice_profile_id, save_voice_profile
from app.models.schemas import (
    AgentReply,
    AgentReplyRequest,
    BlendProfileInput,
    BlendStrategy,
    ConsentRequest,
    GenerationResult,
    VoiceProfile,
    VoiceBlend,
)
from app.tts.local_wav import LocalWavTtsAdapter

router = APIRouter(prefix="/api")


class CreateBlendRequest(BaseModel):
    name: str
    profiles: list[BlendProfileInput]
    strategy: BlendStrategy = "local_development_wav"


class GenerateRequest(BaseModel):
    prompt: str
    agent_reply: str
    blend: VoiceBlend


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/blends", response_model=VoiceBlend)
def create_blend_route(request: CreateBlendRequest) -> VoiceBlend:
    try:
        return create_blend(
            name=request.name,
            profiles=request.profiles,
            strategy=request.strategy,
        )
    except BlendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate", response_model=GenerationResult)
def generate_route(request: GenerateRequest) -> GenerationResult:
    ensure_storage()
    adapter = LocalWavTtsAdapter(output_root=Path(GENERATION_ROOT))
    try:
        return generate_agent_clip(
            prompt=request.prompt,
            agent_reply=request.agent_reply,
            blend=request.blend,
            adapter=adapter,
        )
    except SafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/agent/reply", response_model=AgentReply)
def agent_reply_route(request: AgentReplyRequest) -> AgentReply:
    try:
        return generate_agent_reply_record(prompt=request.prompt, config=request.config)
    except (AgentProviderError, SafetyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/voices", response_model=VoiceProfile)
async def import_voice_route(
    speaker_display_name: str = Form(...),
    consent_type: str = Form(...),
    allowed_uses: str = Form(...),
    confirmed_by: str = Form(...),
    notes: str = Form(""),
    file: UploadFile = File(...),
) -> VoiceProfile:
    voice_id = new_voice_profile_id()
    consent_request = ConsentRequest(
        speaker_display_name=speaker_display_name,
        consent_type=consent_type,
        allowed_uses=[item.strip() for item in allowed_uses.split(",") if item.strip()],
        confirmed_by=confirmed_by,
        notes=notes,
    )
    try:
        consent = create_consent_record(voice_id, consent_request)
    except ConsentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    source_bytes = await file.read()
    ensure_storage()
    temp_dir = Path("data") / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / (file.filename or "sample.wav")
    temp_path.write_bytes(source_bytes)
    quality = analyze_audio_sample(temp_path)

    profile = VoiceProfile(
        id=voice_id,
        display_name=speaker_display_name,
        consent=consent,
        source_audio_path="",
        cleaned_audio_path="",
        quality=quality,
    )
    return save_voice_profile(profile, source_bytes, file.filename or "sample.wav")


@router.get("/voices", response_model=list[VoiceProfile])
def list_voices_route() -> list[VoiceProfile]:
    return list_voice_profiles()
