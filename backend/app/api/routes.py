from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.blends import BlendError, create_blend
from app.core.generation import generate_agent_clip
from app.core.safety import SafetyError
from app.core.storage import GENERATION_ROOT, ensure_storage
from app.models.schemas import BlendProfileInput, BlendStrategy, GenerationResult, VoiceBlend
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
