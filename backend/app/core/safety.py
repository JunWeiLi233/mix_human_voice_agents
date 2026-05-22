class SafetyError(ValueError):
    pass


BLOCKED_PHRASES = (
    "wire transfer",
    "approve this payment",
    "approve this wire",
    "i am alice",
    "i am bob",
    "pretend to be",
    "do not disclose",
    "without disclosure",
)


def check_generation_request(text: str) -> None:
    lowered = text.lower()
    if any(phrase in lowered for phrase in BLOCKED_PHRASES):
        raise SafetyError("Blocked impersonation or fraud-like voice generation request.")

