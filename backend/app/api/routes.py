from pathlib import Path
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.agent import AgentProviderError, generate_agent_reply_record
from app.core.audio import AudioQualityError, analyze_audio_sample
from app.core.blends import BlendError, create_blend
from app.core.consent import ConsentError, create_consent_record
from app.core.generation import generate_agent_clip
from app.core.safety import SafetyError
from app.core.storage import (
    GENERATION_ROOT,
    delete_voice_profile,
    ensure_storage,
    get_generation_audio_path,
    get_voice_profiles_by_ids,
    list_blends,
    list_generation_results,
    list_voice_profiles,
    new_voice_profile_id,
    save_blend,
    save_voice_profile,
)
from app.models.schemas import (
    AgentReply,
    AgentReplyRequest,
    BlendProfileInput,
    BlendStrategy,
    ConsentRequest,
    GenerationResult,
    QwenVerificationReport,
    TtsRuntimeStatus,
    TtsBackend,
    VoiceProfile,
    VoiceBlend,
)
from app.tts.local_wav import LocalWavTtsAdapter
from app.tts.qwen import QwenTtsAdapter, QwenTtsNotConfigured

router = APIRouter(prefix="/api")
QWEN_VERIFICATION_REPORT_PATH = Path("data") / "qwen-runtime-verification-report.json"


class CreateBlendRequest(BaseModel):
    name: str
    profiles: list[BlendProfileInput]
    strategy: BlendStrategy = "local_development_wav"


class GenerateRequest(BaseModel):
    prompt: str
    agent_reply: str
    blend: VoiceBlend
    tts_backend: TtsBackend = "local_development_wav"


class RunQwenVerificationRequest(BaseModel):
    voice_profile_ids: list[str]
    text: str = "This is a disclosed synthetic mixed voice runtime verification."


class DeleteVoiceResponse(BaseModel):
    deleted_voice_profile_id: str
    deleted_blend_ids: list[str]
    deleted_generation_ids: list[str]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/tts/qwen/status", response_model=TtsRuntimeStatus)
def qwen_status_route() -> TtsRuntimeStatus:
    return QwenTtsAdapter.runtime_status()


@router.get("/tts/qwen/verification", response_model=QwenVerificationReport)
def qwen_verification_route() -> QwenVerificationReport:
    report_path = QWEN_VERIFICATION_REPORT_PATH
    if not report_path.exists():
        return QwenVerificationReport(
            status="missing",
            report_path=str(report_path),
            error="Run python -m app.cli.verify_qwen_runtime with two consented voice profile ids.",
        )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload.setdefault("report_path", str(report_path))
    return QwenVerificationReport.model_validate(payload)


@router.post("/tts/qwen/verification", response_model=QwenVerificationReport)
def run_qwen_verification_route(request: RunQwenVerificationRequest) -> QwenVerificationReport:
    profile_ids = request.voice_profile_ids
    if len(profile_ids) < 2:
        raise HTTPException(status_code=400, detail="Qwen runtime verification requires at least two voice profile ids.")

    try:
        voice_profiles = get_voice_profiles_by_ids(profile_ids)
        blend = create_blend(
            name="Qwen runtime verification blend",
            profiles=[BlendProfileInput(voice_profile_id=profile_id, weight=1) for profile_id in profile_ids],
            strategy="multi_reference_prompt",
        )
        adapter = QwenTtsAdapter.from_pretrained(output_root=Path(GENERATION_ROOT))
        output_path = adapter.synthesize(request.text, blend, voice_profiles=voice_profiles)
    except (FileNotFoundError, QwenTtsNotConfigured, ValueError) as exc:
        return _write_qwen_verification_report(
            {
                "status": "failed",
                "error": str(exc),
                "voice_profile_ids": profile_ids,
                "tts_backend": "qwen3_tts",
                "text": request.text,
            }
        )

    return _write_qwen_verification_report(
        {
            "status": "passed",
            "voice_profile_ids": profile_ids,
            "blend_id": blend.id,
            "blend_strategy": blend.strategy,
            "tts_backend": "qwen3_tts",
            "output_audio_path": str(output_path),
            "text": request.text,
        }
    )


def _write_qwen_verification_report(payload: dict[str, object]) -> QwenVerificationReport:
    report_path = QWEN_VERIFICATION_REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload["report_path"] = str(report_path)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return QwenVerificationReport.model_validate(payload)


@router.post("/blends", response_model=VoiceBlend)
def create_blend_route(request: CreateBlendRequest) -> VoiceBlend:
    try:
        blend = create_blend(
            name=request.name,
            profiles=request.profiles,
            strategy=request.strategy,
        )
        return save_blend(blend)
    except BlendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/blends", response_model=list[VoiceBlend])
def list_blends_route() -> list[VoiceBlend]:
    return list_blends()


@router.post("/generate", response_model=GenerationResult)
def generate_route(request: GenerateRequest) -> GenerationResult:
    ensure_storage()
    voice_profiles = None
    if request.tts_backend == "qwen3_tts":
        source_ids = [profile.voice_profile_id for profile in request.blend.profiles]
        try:
            voice_profiles = get_voice_profiles_by_ids(source_ids)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        adapter = QwenTtsAdapter.from_pretrained(output_root=Path(GENERATION_ROOT))
    else:
        adapter = LocalWavTtsAdapter(output_root=Path(GENERATION_ROOT))
    try:
        return generate_agent_clip(
            prompt=request.prompt,
            agent_reply=request.agent_reply,
            blend=request.blend,
            adapter=adapter,
            voice_profiles=voice_profiles,
            tts_backend=request.tts_backend,
        )
    except (QwenTtsNotConfigured, SafetyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/generations", response_model=list[GenerationResult])
def list_generations_route() -> list[GenerationResult]:
    return list_generation_results()


@router.get("/generations/{generation_id}/audio")
def generation_audio_route(generation_id: str) -> FileResponse:
    try:
        audio_path = get_generation_audio_path(generation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(audio_path, media_type="audio/wav", filename=f"{generation_id}.wav")


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
    reference_text: str = Form(""),
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
    try:
        quality = analyze_audio_sample(temp_path)
    except AudioQualityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    profile = VoiceProfile(
        id=voice_id,
        display_name=speaker_display_name,
        reference_text=reference_text,
        consent=consent,
        source_audio_path="",
        cleaned_audio_path="",
        quality=quality,
    )
    return save_voice_profile(profile, source_bytes, file.filename or "sample.wav")


@router.get("/voices", response_model=list[VoiceProfile])
def list_voices_route() -> list[VoiceProfile]:
    return list_voice_profiles()


@router.delete("/voices/{voice_profile_id}", response_model=DeleteVoiceResponse)
def delete_voice_route(voice_profile_id: str) -> DeleteVoiceResponse:
    try:
        result = delete_voice_profile(voice_profile_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DeleteVoiceResponse(
        deleted_voice_profile_id=voice_profile_id,
        deleted_blend_ids=result.deleted_blend_ids,
        deleted_generation_ids=result.deleted_generation_ids,
    )
