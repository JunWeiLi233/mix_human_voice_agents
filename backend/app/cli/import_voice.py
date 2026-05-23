from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.core.audio import AudioQualityError, analyze_audio_sample
from app.core.consent import ConsentError, create_consent_record
from app.core.storage import new_voice_profile_id, safe_storage_file_name, save_voice_profile
from app.models.schemas import ConsentRequest, VoiceProfile


DEFAULT_ALLOWED_USES = "private_agent_voice,local_audio_export"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import a consented WAV voice sample into local profile storage.")
    parser.add_argument("--speaker-display-name", required=True, help="Speaker display name for this profile.")
    parser.add_argument("--confirmed-by", required=True, help="Name/user who confirmed self or written permission.")
    parser.add_argument("--notes", default="", help="Consent notes proving local private synthetic voice permission.")
    parser.add_argument("--reference-text", required=True, help="Transcript matching the imported reference audio.")
    parser.add_argument("--audio", required=True, help="Path to a clean 5-30 second WAV reference sample.")
    parser.add_argument(
        "--allowed-use",
        action="append",
        default=[],
        help="Allowed use. Defaults to private_agent_voice and local_audio_export when omitted.",
    )
    parser.add_argument(
        "--metadata",
        default=None,
        help="Optional path to write the imported voice profile JSON metadata.",
    )
    args = parser.parse_args(argv)

    metadata_path = Path(args.metadata) if args.metadata else None
    speaker_display_name = args.speaker_display_name.strip()
    confirmed_by = args.confirmed_by.strip()
    reference_text = args.reference_text.strip()
    audio_path = Path(args.audio)

    validation_error = _input_error(speaker_display_name, confirmed_by, reference_text, audio_path)
    if validation_error:
        _write_error(metadata_path, validation_error)
        return 2

    try:
        quality = analyze_audio_sample(audio_path)
        source_bytes = audio_path.read_bytes()
        voice_id = new_voice_profile_id()
        consent = create_consent_record(
            voice_id,
            ConsentRequest(
                speaker_display_name=speaker_display_name,
                consent_type="self_or_written_permission",
                allowed_uses=_allowed_uses(args.allowed_use),
                confirmed_by=confirmed_by,
                notes=args.notes.strip(),
            ),
        )
        profile = VoiceProfile(
            id=voice_id,
            display_name=speaker_display_name,
            reference_text=reference_text,
            consent=consent,
            source_audio_path="",
            cleaned_audio_path="",
            quality=quality,
        )
        saved_profile = save_voice_profile(profile, source_bytes, safe_storage_file_name(audio_path.name))
    except (AudioQualityError, ConsentError, OSError, FileNotFoundError) as exc:
        _write_error(metadata_path, str(exc))
        return 1

    if metadata_path:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(saved_profile.model_dump(mode="json"), indent=2), encoding="utf-8")
    return 0


def _input_error(speaker_display_name: str, confirmed_by: str, reference_text: str, audio_path: Path) -> str | None:
    if not speaker_display_name:
        return "A speaker display name is required for voice import."
    if not confirmed_by:
        return "A consent confirmer is required for voice import."
    if not reference_text:
        return "A reference transcript is required for voice import."
    if not audio_path.exists():
        return f"Reference audio does not exist: {audio_path}"
    return None


def _allowed_uses(allowed_use_args: list[str]) -> list[str]:
    raw_values = allowed_use_args or DEFAULT_ALLOWED_USES.split(",")
    return [item.strip() for value in raw_values for item in value.split(",") if item.strip()]


def _write_error(metadata_path: Path | None, error: str) -> None:
    if metadata_path is None:
        return
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "status": "failed",
                "error": error,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
