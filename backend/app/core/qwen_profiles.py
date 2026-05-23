from pathlib import Path

from app.core.audio import is_parseable_wav, wav_has_audible_signal
from app.models.schemas import VoiceProfile


REQUIRED_VOICE_USE = "private_agent_voice"


def validate_qwen_voice_profiles(voice_profiles: dict[str, VoiceProfile]) -> None:
    normalized_speaker_names = {
        profile.display_name.strip().casefold()
        for profile in voice_profiles.values()
        if profile.display_name.strip()
    }
    if len(normalized_speaker_names) < 2:
        raise ValueError("Qwen synthesis requires at least two distinct speakers.")

    for profile in voice_profiles.values():
        consent = profile.consent
        if not consent.synthetic_voice_allowed or REQUIRED_VOICE_USE not in consent.allowed_uses:
            raise ValueError(f"Voice profile {profile.id} is not allowed for private agent voice use.")
        if not profile.reference_text.strip():
            raise ValueError(f"Voice profile {profile.id} must include reference text for Qwen synthesis.")
        if profile.quality.warnings:
            raise ValueError(f"Voice profile {profile.id} must not have audio quality warnings for Qwen synthesis.")
        if not profile.cleaned_audio_path or not Path(profile.cleaned_audio_path).exists():
            raise ValueError(f"Voice profile {profile.id} must have an existing cleaned audio file for Qwen synthesis.")
        if not is_parseable_wav(Path(profile.cleaned_audio_path)):
            raise ValueError(f"Voice profile {profile.id} must have a parseable cleaned WAV file for Qwen synthesis.")
        if not wav_has_audible_signal(Path(profile.cleaned_audio_path)):
            raise ValueError(f"Voice profile {profile.id} must have audible cleaned audio for Qwen synthesis.")
