from pathlib import Path
import json
from uuid import uuid4

from app.models.schemas import VoiceProfile

DATA_ROOT = Path("data")
VOICE_ROOT = DATA_ROOT / "voices"
BLEND_ROOT = DATA_ROOT / "blends"
GENERATION_ROOT = DATA_ROOT / "generations"


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
