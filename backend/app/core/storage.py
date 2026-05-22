from pathlib import Path
import json
import shutil
from uuid import uuid4

from app.models.schemas import GenerationResult, VoiceBlend, VoiceProfile

DATA_ROOT = Path("data")
VOICE_ROOT = DATA_ROOT / "voices"
BLEND_ROOT = DATA_ROOT / "blends"
GENERATION_ROOT = DATA_ROOT / "generations"


class VoiceProfileDeleteResult:
    def __init__(self, deleted_blend_ids: list[str], deleted_generation_ids: list[str]) -> None:
        self.deleted_blend_ids = deleted_blend_ids
        self.deleted_generation_ids = deleted_generation_ids


def ensure_storage() -> None:
    for path in (VOICE_ROOT, BLEND_ROOT, GENERATION_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def new_voice_profile_id() -> str:
    return f"voice_{uuid4().hex[:12]}"


def save_voice_profile(profile: VoiceProfile, source_bytes: bytes, file_name: str) -> VoiceProfile:
    ensure_storage()
    voice_dir = VOICE_ROOT / profile.id
    voice_dir.mkdir(parents=True, exist_ok=True)
    source_path = voice_dir / file_name
    source_path.write_bytes(source_bytes)
    updated = profile.model_copy(
        update={
            "source_audio_path": str(source_path),
            "cleaned_audio_path": str(source_path),
        }
    )
    (voice_dir / "profile.json").write_text(
        json.dumps(updated.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return updated


def list_voice_profiles() -> list[VoiceProfile]:
    ensure_storage()
    profiles: list[VoiceProfile] = []
    for profile_path in sorted(VOICE_ROOT.glob("*/profile.json")):
        profiles.append(VoiceProfile.model_validate_json(profile_path.read_text(encoding="utf-8")))
    return profiles


def get_voice_profiles_by_ids(profile_ids: list[str]) -> dict[str, VoiceProfile]:
    profiles = {profile.id: profile for profile in list_voice_profiles()}
    missing = [profile_id for profile_id in profile_ids if profile_id not in profiles]
    if missing:
        raise FileNotFoundError(f"Missing voice profiles: {', '.join(missing)}")
    return {profile_id: profiles[profile_id] for profile_id in profile_ids}


def get_voice_audio_path(profile_id: str) -> Path:
    ensure_storage()
    voice_dir = (VOICE_ROOT / profile_id).resolve()
    profile_path = voice_dir / "profile.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Voice profile not found: {profile_id}")

    profile = VoiceProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))
    audio_path = Path(profile.source_audio_path).resolve()
    if voice_dir not in (audio_path, *audio_path.parents):
        raise FileNotFoundError(f"Voice audio is outside voice storage: {profile_id}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Voice audio is missing: {profile_id}")
    return audio_path


def delete_voice_profile(profile_id: str) -> VoiceProfileDeleteResult:
    ensure_storage()
    voice_dir = VOICE_ROOT / profile_id
    if not (voice_dir / "profile.json").exists():
        raise FileNotFoundError(f"Voice profile not found: {profile_id}")

    shutil.rmtree(voice_dir)

    deleted_blend_ids: list[str] = []
    for blend_path in sorted(BLEND_ROOT.glob("*.json")):
        blend = VoiceBlend.model_validate_json(blend_path.read_text(encoding="utf-8"))
        if any(profile.voice_profile_id == profile_id for profile in blend.profiles):
            deleted_blend_ids.append(blend.id)
            blend_path.unlink()

    deleted_generation_ids: list[str] = []
    generation_root = GENERATION_ROOT.resolve()
    for metadata_path in sorted(GENERATION_ROOT.glob("*.json")):
        result = GenerationResult.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        if profile_id not in result.source_profile_ids:
            continue

        audio_path = Path(result.audio_path).resolve()
        if generation_root in (audio_path, *audio_path.parents) and audio_path.exists():
            audio_path.unlink()
        metadata_path.unlink()
        deleted_generation_ids.append(result.id)

    return VoiceProfileDeleteResult(
        deleted_blend_ids=deleted_blend_ids,
        deleted_generation_ids=deleted_generation_ids,
    )


def save_blend(blend: VoiceBlend) -> VoiceBlend:
    ensure_storage()
    blend_path = BLEND_ROOT / f"{blend.id}.json"
    blend_path.write_text(
        json.dumps(blend.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return blend


def list_blends() -> list[VoiceBlend]:
    ensure_storage()
    blends: list[VoiceBlend] = []
    for blend_path in sorted(
        BLEND_ROOT.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        blends.append(VoiceBlend.model_validate_json(blend_path.read_text(encoding="utf-8")))
    return blends


def list_generation_results() -> list[GenerationResult]:
    ensure_storage()
    results: list[GenerationResult] = []
    for metadata_path in sorted(
        GENERATION_ROOT.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        results.append(GenerationResult.model_validate_json(metadata_path.read_text(encoding="utf-8")))
    return results


def get_generation_audio_path(generation_id: str) -> Path:
    ensure_storage()
    generation_root = GENERATION_ROOT.resolve()
    for metadata_path in sorted(GENERATION_ROOT.glob("*.json")):
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if payload.get("id") != generation_id:
            continue

        audio_path = Path(payload["audio_path"]).resolve()
        if generation_root not in (audio_path, *audio_path.parents):
            raise FileNotFoundError(f"Generated audio is outside generation storage: {generation_id}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Generated audio is missing: {generation_id}")
        return audio_path

    raise FileNotFoundError(f"Generated audio not found: {generation_id}")


def get_generation_metadata_path(generation_id: str) -> Path:
    ensure_storage()
    generation_root = GENERATION_ROOT.resolve()
    for metadata_path in sorted(GENERATION_ROOT.glob("*.json")):
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if payload.get("id") != generation_id:
            continue

        resolved_metadata_path = metadata_path.resolve()
        if generation_root not in (resolved_metadata_path, *resolved_metadata_path.parents):
            raise FileNotFoundError(f"Generated metadata is outside generation storage: {generation_id}")
        return resolved_metadata_path

    raise FileNotFoundError(f"Generated metadata not found: {generation_id}")
