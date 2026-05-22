from app.models.schemas import BlendProfile, BlendProfileInput, BlendStrategy, VoiceBlend


class BlendError(ValueError):
    pass


def create_blend(
    name: str,
    profiles: list[BlendProfileInput],
    strategy: BlendStrategy,
) -> VoiceBlend:
    if len(profiles) < 2:
        raise BlendError("A mixed voice blend requires at least two profiles.")

    total = sum(profile.weight for profile in profiles)
    if total <= 0:
        raise BlendError("Blend weights must sum to a positive number.")

    normalized = [
        BlendProfile(
            voice_profile_id=profile.voice_profile_id,
            weight=profile.weight / total,
        )
        for profile in profiles
    ]
    return VoiceBlend(name=name, profiles=normalized, strategy=strategy)

