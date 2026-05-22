from app.models.schemas import VoiceProfile


REQUIRED_VOICE_USE = "private_agent_voice"


def validate_qwen_voice_profiles(voice_profiles: dict[str, VoiceProfile]) -> None:
    for profile in voice_profiles.values():
        consent = profile.consent
        if not consent.synthetic_voice_allowed or REQUIRED_VOICE_USE not in consent.allowed_uses:
            raise ValueError(f"Voice profile {profile.id} is not allowed for private agent voice use.")
        if not profile.reference_text.strip():
            raise ValueError(f"Voice profile {profile.id} must include reference text for Qwen synthesis.")
        if profile.quality.warnings:
            raise ValueError(f"Voice profile {profile.id} must not have audio quality warnings for Qwen synthesis.")
