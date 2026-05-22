from pathlib import Path
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.agent import AgentProviderError, generate_agent_reply_record
from app.core.audio import AudioQualityError, analyze_audio_sample
from app.core.blends import BlendError, create_blend, validate_blend
from app.core.consent import ConsentError, create_consent_record
from app.core.generation import generate_agent_clip
from app.core.generation import build_source_profile_details
from app.core.launch import (
    AGENT_PROVIDER_VERIFICATION_REPORT_PATH,
    QWEN_VERIFICATION_REPORT_PATH,
    evaluate_launch_readiness,
    get_agent_provider_verification_report,
    get_qwen_verification_report,
)
from app.core.safety import SafetyError
from app.core.storage import (
    GENERATION_ROOT,
    delete_voice_profile,
    ensure_storage,
    get_generation_audio_path,
    get_generation_metadata_path,
    get_voice_audio_path,
    get_voice_profiles_by_ids,
    list_blends,
    list_generation_results,
    list_voice_profiles,
    new_voice_profile_id,
    save_blend,
    save_voice_profile,
)
from app.models.schemas import (
    AgentProviderVerificationReport,
    AgentReply,
    AgentReplyRequest,
    AgentTrace,
    BlendProfileInput,
    BlendStrategy,
    ConsentRequest,
    GenerationResult,
    LaunchReadinessReport,
    QwenVerificationReport,
    TtsRuntimeStatus,
    TtsBackend,
    VoiceProfile,
    VoiceBlend,
)
from app.tts.local_wav import LocalWavTtsAdapter
from app.tts.qwen import QwenTtsAdapter, QwenTtsNotConfigured

router = APIRouter(prefix="/api")


class CreateBlendRequest(BaseModel):
    name: str
    profiles: list[BlendProfileInput]
    strategy: BlendStrategy = "local_development_wav"


class GenerateRequest(BaseModel):
    prompt: str
    agent_reply: str
    blend: VoiceBlend
    tts_backend: TtsBackend = "local_development_wav"
    agent_trace: AgentTrace | None = None
    model_id: str | None = None
    device_map: str | None = None
    dtype: str | None = None
    attn_implementation: str | None = None


class RunQwenVerificationRequest(BaseModel):
    voice_profile_ids: list[str]
    text: str = "This is a disclosed synthetic mixed voice runtime verification."
    model_id: str | None = None
    device_map: str | None = None
    dtype: str | None = None
    attn_implementation: str | None = None


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
    return get_qwen_verification_report()


@router.get("/agent/provider-verification", response_model=AgentProviderVerificationReport)
def agent_provider_verification_route() -> AgentProviderVerificationReport:
    return get_agent_provider_verification_report()


@router.post("/agent/provider-verification", response_model=AgentProviderVerificationReport)
def run_agent_provider_verification_route(request: AgentReplyRequest) -> AgentProviderVerificationReport:
    try:
        reply = generate_agent_reply_record(prompt=request.prompt, config=request.config)
    except (AgentProviderError, SafetyError) as exc:
        return _write_agent_provider_verification_report(
            {
                "status": "failed",
                "provider": request.config.provider,
                "model": request.config.model,
                "error": str(exc),
            }
        )

    verified_reply = AgentReply.model_validate(reply)
    return _write_agent_provider_verification_report(
        {
            "status": "passed",
            "provider": verified_reply.provider,
            "model": verified_reply.model,
            "reply": verified_reply.reply,
        }
    )


@router.get("/launch/readiness", response_model=LaunchReadinessReport)
def launch_readiness_route() -> LaunchReadinessReport:
    return evaluate_launch_readiness()


@router.post("/tts/qwen/verification", response_model=QwenVerificationReport)
def run_qwen_verification_route(request: RunQwenVerificationRequest) -> QwenVerificationReport:
    profile_ids = request.voice_profile_ids
    if len(profile_ids) < 2:
        raise HTTPException(status_code=400, detail="Qwen runtime verification requires at least two voice profile ids.")
    if len(set(profile_ids)) < 2:
        raise HTTPException(
            status_code=400,
            detail="Qwen runtime verification requires at least two distinct voice profile ids.",
        )

    try:
        voice_profiles = get_voice_profiles_by_ids(profile_ids)
        blend = create_blend(
            name="Qwen runtime verification blend",
            profiles=[BlendProfileInput(voice_profile_id=profile_id, weight=1) for profile_id in profile_ids],
            strategy="multi_reference_prompt",
        )
        adapter = QwenTtsAdapter.from_pretrained(
            model_id=request.model_id,
            device_map=request.device_map,
            dtype=request.dtype,
            attn_implementation=request.attn_implementation,
            output_root=Path(GENERATION_ROOT),
        )
        output_path = adapter.synthesize(request.text, blend, voice_profiles=voice_profiles)
    except (FileNotFoundError, QwenTtsNotConfigured, ValueError) as exc:
        return _write_qwen_verification_report(
            {
                "status": "failed",
                "error": str(exc),
                "voice_profile_ids": profile_ids,
                "model_id": request.model_id,
                "device_map": request.device_map,
                "dtype": request.dtype,
                "attn_implementation": request.attn_implementation,
                "tts_backend": "qwen3_tts",
                "text": request.text,
            }
        )

    return _write_qwen_verification_report(
        {
            "status": "passed",
            "voice_profile_ids": profile_ids,
            "model_id": request.model_id,
            "device_map": request.device_map,
            "dtype": request.dtype,
            "attn_implementation": request.attn_implementation,
            "source_profile_details": [
                detail.model_dump(mode="json")
                for detail in build_source_profile_details(blend.profiles, voice_profiles)
            ],
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


def _write_agent_provider_verification_report(payload: dict[str, object]) -> AgentProviderVerificationReport:
    report_path = AGENT_PROVIDER_VERIFICATION_REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload["report_path"] = str(report_path)
    report = AgentProviderVerificationReport.model_validate(payload)
    report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    return report


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
    try:
        validate_blend(request.blend)
    except BlendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    source_ids = [profile.voice_profile_id for profile in request.blend.profiles]
    voice_profiles = _load_voice_profiles_for_generation(source_ids, strict=request.tts_backend == "qwen3_tts")
    qwen_runtime_config = _qwen_runtime_config_from_request(request)
    if request.tts_backend == "qwen3_tts":
        adapter = QwenTtsAdapter.from_pretrained(
            model_id=request.model_id,
            device_map=request.device_map,
            dtype=request.dtype,
            attn_implementation=request.attn_implementation,
            output_root=Path(GENERATION_ROOT),
        )
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
            agent_trace=request.agent_trace,
            qwen_runtime_config=qwen_runtime_config,
        )
    except (BlendError, QwenTtsNotConfigured, SafetyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _load_voice_profiles_for_generation(profile_ids: list[str], strict: bool) -> dict[str, VoiceProfile] | None:
    try:
        return get_voice_profiles_by_ids(profile_ids)
    except FileNotFoundError as exc:
        if strict:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return None


def _qwen_runtime_config_from_request(request: GenerateRequest) -> dict[str, str | None] | None:
    if request.tts_backend != "qwen3_tts":
        return None
    return {
        "model_id": request.model_id,
        "device_map": request.device_map,
        "dtype": request.dtype,
        "attn_implementation": request.attn_implementation,
    }


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


@router.get("/generations/{generation_id}/metadata")
def generation_metadata_route(generation_id: str) -> FileResponse:
    try:
        metadata_path = get_generation_metadata_path(generation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(metadata_path, media_type="application/json", filename=f"{generation_id}.json")


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
    cleaned_reference_text = reference_text.strip()
    if not cleaned_reference_text:
        raise HTTPException(status_code=400, detail="A reference transcript is required for voice import.")

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
        reference_text=cleaned_reference_text,
        consent=consent,
        source_audio_path="",
        cleaned_audio_path="",
        quality=quality,
    )
    return save_voice_profile(profile, source_bytes, file.filename or "sample.wav")


@router.get("/voices", response_model=list[VoiceProfile])
def list_voices_route() -> list[VoiceProfile]:
    return list_voice_profiles()


@router.get("/voices/{voice_profile_id}/audio")
def voice_audio_route(voice_profile_id: str) -> FileResponse:
    try:
        audio_path = get_voice_audio_path(voice_profile_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(audio_path, media_type="audio/wav", filename=f"{voice_profile_id}.wav")


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
