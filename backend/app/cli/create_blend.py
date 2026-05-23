from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from app.core.blends import BlendError, create_blend
from app.core.storage import get_voice_profiles_by_ids, save_blend
from app.models.schemas import BlendProfileInput, BlendStrategy, VoiceProfile


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a saved mixed voice blend from imported voice profiles.")
    parser.add_argument("--name", required=True, help="Saved blend name.")
    parser.add_argument(
        "--profile",
        action="append",
        required=True,
        help="Voice profile and weight in the form voice_profile_id=weight. Repeat for each imported voice.",
    )
    parser.add_argument(
        "--strategy",
        default="multi_reference_prompt",
        choices=[
            "adapter_embedding_mix",
            "multi_reference_prompt",
            "segment_ensemble",
            "designed_voice_proxy",
            "local_development_wav",
        ],
        help="Blend strategy to persist.",
    )
    parser.add_argument("--metadata", help="Optional path to write the saved blend JSON or failure report.")
    args = parser.parse_args(argv)

    try:
        profiles = [_parse_profile_spec(profile_spec) for profile_spec in args.profile]
        profile_ids = [profile.voice_profile_id for profile in profiles]
        voice_profiles = get_voice_profiles_by_ids(profile_ids)
        _validate_distinct_speaker_names(voice_profiles)
        blend = create_blend(name=args.name.strip(), profiles=profiles, strategy=args.strategy)
        saved_blend = save_blend(blend)
    except (BlendError, FileNotFoundError, ValidationError, ValueError) as exc:
        _write_metadata(args.metadata, {"status": "failed", "error": str(exc)})
        return 1

    _write_metadata(args.metadata, saved_blend.model_dump(mode="json"))
    return 0


def _parse_profile_spec(profile_spec: str) -> BlendProfileInput:
    if "=" not in profile_spec:
        raise ValueError("Blend profiles must use voice_profile_id=weight format.")
    voice_profile_id, weight_text = profile_spec.split("=", 1)
    voice_profile_id = voice_profile_id.strip()
    if not voice_profile_id:
        raise ValueError("Blend profile id must not be blank.")
    try:
        weight = float(weight_text.strip())
    except ValueError as exc:
        raise ValueError(f"Blend profile {voice_profile_id} weight must be a number.") from exc
    return BlendProfileInput(voice_profile_id=voice_profile_id, weight=weight)


def _validate_distinct_speaker_names(voice_profiles: dict[str, VoiceProfile]) -> None:
    normalized_names = {
        profile.display_name.strip().casefold()
        for profile in voice_profiles.values()
        if profile.display_name.strip()
    }
    if len(normalized_names) < 2:
        raise BlendError("A mixed voice blend requires at least two distinct speaker display names.")


def _write_metadata(metadata_path: str | None, payload: dict[str, object]) -> None:
    if not metadata_path:
        return
    path = Path(metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
