from __future__ import annotations

import re


MIN_REFERENCE_TEXT_WORDS = 5
REFERENCE_TEXT_ERROR = (
    f"Reference transcript must include at least {MIN_REFERENCE_TEXT_WORDS} words for Qwen voice cloning."
)


def reference_text_error(reference_text: str) -> str | None:
    if not reference_text.strip():
        return "A reference transcript is required for voice import."
    if len(re.findall(r"\b[\w']+\b", reference_text)) < MIN_REFERENCE_TEXT_WORDS:
        return REFERENCE_TEXT_ERROR
    return None
