from app.models.schemas import ConsentRecord, ConsentRequest


class ConsentError(ValueError):
    pass


REQUIRED_ALLOWED_USES = {"private_agent_voice"}


def create_consent_record(voice_profile_id: str, request: ConsentRequest) -> ConsentRecord:
    allowed_uses = set(request.allowed_uses)
    if not allowed_uses:
        raise ConsentError("At least one allowed use is required.")
    if not REQUIRED_ALLOWED_USES.issubset(allowed_uses):
        raise ConsentError("Consent must include private_agent_voice as an allowed use.")

    return ConsentRecord(
        voice_profile_id=voice_profile_id,
        speaker_display_name=request.speaker_display_name,
        consent_type=request.consent_type,
        allowed_uses=request.allowed_uses,
        confirmed_by=request.confirmed_by,
        notes=request.notes,
        synthetic_voice_allowed=True,
    )

