from app.models.schemas import ConsentRecord, ConsentRequest


class ConsentError(ValueError):
    pass


REQUIRED_ALLOWED_USES = {"private_agent_voice"}
PUBLIC_FIGURE_TERMS = (
    "celebrity",
    "public figure",
    "politician",
    "president",
    "famous",
)
MISSING_PERMISSION_PHRASES = (
    "no permission",
    "without permission",
    "do not have permission",
    "don't have permission",
    "did not consent",
    "no consent",
    "without consent",
    "non-consenting",
)


def create_consent_record(voice_profile_id: str, request: ConsentRequest) -> ConsentRecord:
    _screen_consent_claims(request)
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


def _screen_consent_claims(request: ConsentRequest) -> None:
    claim_text = f"{request.speaker_display_name} {request.notes}".lower()
    if any(term in claim_text for term in PUBLIC_FIGURE_TERMS):
        raise ConsentError("public figure or celebrity voice imports are not allowed in this prototype.")
    if any(phrase in claim_text for phrase in MISSING_PERMISSION_PHRASES):
        raise ConsentError("Voice import requires self or written permission from the speaker.")
