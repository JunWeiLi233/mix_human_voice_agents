from app.models.schemas import BlendProfile, BlendProfileInput, BlendStrategy, VoiceBlend


class BlendError(ValueError):
    pass


def create_blend(
    name: str,
    profiles: list[BlendProfileInput],
    strategy: BlendStrategy,
) -> VoiceBlend:
    _validate_distinct_profile_ids([profile.voice_profile_id for profile in profiles])

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


def validate_blend(blend: VoiceBlend) -> None:
    _validate_distinct_profile_ids([profile.voice_profile_id for profile in blend.profiles])


def _validate_distinct_profile_ids(profile_ids: list[str]) -> None:
    if len(profile_ids) < 2:
        raise BlendError("A mixed voice blend requires at least two profiles.")

    if len(set(profile_ids)) < 2:
        raise BlendError("A mixed voice blend requires at least two distinct profiles.")
