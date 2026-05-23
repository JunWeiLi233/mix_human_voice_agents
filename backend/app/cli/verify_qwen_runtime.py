from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.core.audio import is_parseable_wav, wav_has_audible_signal
from app.core.blends import create_blend
from app.core.generation import build_source_profile_details
from app.core.qwen_profiles import validate_qwen_voice_profiles
from app.core.qwen_runtime import resolved_qwen_runtime_config
from app.core.storage import GENERATION_ROOT, get_voice_profiles_by_ids
from app.models.schemas import BlendProfileInput
from app.tts.qwen import QwenTtsAdapter, QwenTtsNotConfigured


DEFAULT_VERIFY_TEXT = "This is a disclosed synthetic mixed voice runtime verification."


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Qwen3-TTS mixed voice synthesis with imported profiles.")
    parser.add_argument(
        "--voice-profile-id",
        action="append",
        default=[],
        help="Imported voice profile id to include in the verification blend. Provide at least two.",
    )
    parser.add_argument("--text", default=DEFAULT_VERIFY_TEXT, help="Text to synthesize during verification.")
    parser.add_argument(
        "--model-id",
        default=None,
        help="Qwen3-TTS model id or local model directory. Defaults to QWEN_TTS_MODEL_ID or the adapter default.",
    )
    parser.add_argument(
        "--device-map",
        default=None,
        help="Device map passed to Qwen3TTSModel.from_pretrained, such as auto, cuda:0, or cpu.",
    )
    parser.add_argument(
        "--dtype",
        default=None,
        help="Torch dtype passed to Qwen3TTSModel.from_pretrained, such as bfloat16 or float16.",
    )
    parser.add_argument(
        "--attn-implementation",
        default=None,
        help="Attention implementation passed to Qwen3TTSModel.from_pretrained, such as flash_attention_2.",
    )
    parser.add_argument(
        "--report",
        default="data/qwen-runtime-verification-report.json",
        help="Path to write the JSON verification report.",
    )
    args = parser.parse_args(argv)

    profile_ids = list(args.voice_profile_id)
    if len(profile_ids) < 2:
        _write_report(
            Path(args.report),
            {
                "status": "failed",
                "error": "Qwen runtime verification requires at least two voice profile ids.",
                "voice_profile_ids": profile_ids,
                "model_id": args.model_id,
                "device_map": args.device_map,
                "dtype": args.dtype,
                "attn_implementation": args.attn_implementation,
                "tts_backend": "qwen3_tts",
            },
        )
        return 2
    if len(set(profile_ids)) < 2:
        _write_report(
            Path(args.report),
            {
                "status": "failed",
                "error": "Qwen runtime verification requires at least two distinct voice profile ids.",
                "voice_profile_ids": profile_ids,
                "model_id": args.model_id,
                "device_map": args.device_map,
                "dtype": args.dtype,
                "attn_implementation": args.attn_implementation,
                "tts_backend": "qwen3_tts",
            },
        )
        return 2
    if not args.text.strip():
        _write_report(
            Path(args.report),
            {
                "status": "failed",
                "error": "Qwen runtime verification requires non-blank verification text.",
                "voice_profile_ids": profile_ids,
                "model_id": args.model_id,
                "device_map": args.device_map,
                "dtype": args.dtype,
                "attn_implementation": args.attn_implementation,
                "tts_backend": "qwen3_tts",
            },
        )
        return 2

    try:
        voice_profiles = get_voice_profiles_by_ids(profile_ids)
        validate_qwen_voice_profiles(voice_profiles)
        blend = create_blend(
            name="Qwen runtime verification blend",
            profiles=[BlendProfileInput(voice_profile_id=profile_id, weight=1) for profile_id in profile_ids],
            strategy="multi_reference_prompt",
        )
        adapter = QwenTtsAdapter.from_pretrained(
            model_id=args.model_id,
            device_map=args.device_map,
            dtype=args.dtype,
            attn_implementation=args.attn_implementation,
            output_root=Path(GENERATION_ROOT),
        )
        runtime_config = resolved_qwen_runtime_config(
            adapter,
            _qwen_runtime_config_from_args(args),
        )
        output_path = adapter.synthesize(args.text, blend, voice_profiles=voice_profiles)
        output_error = _qwen_generated_audio_error(Path(output_path), "Qwen verification output audio")
        if output_error:
            _write_report(
                Path(args.report),
                {
                    "status": "failed",
                    "error": output_error,
                    "voice_profile_ids": profile_ids,
                    **runtime_config,
                    "tts_backend": "qwen3_tts",
                    "output_audio_path": str(output_path),
                    "text": args.text,
                },
            )
            return 1
    except (FileNotFoundError, QwenTtsNotConfigured, ValueError) as exc:
        _write_report(
            Path(args.report),
            {
                "status": "failed",
                "error": str(exc),
                "voice_profile_ids": profile_ids,
                "model_id": args.model_id,
                "device_map": args.device_map,
                "dtype": args.dtype,
                "attn_implementation": args.attn_implementation,
                "tts_backend": "qwen3_tts",
            },
        )
        return 1

    _write_report(
        Path(args.report),
        {
            "status": "passed",
            "voice_profile_ids": profile_ids,
            **runtime_config,
            "source_profile_details": [
                detail.model_dump(mode="json")
                for detail in build_source_profile_details(blend.profiles, voice_profiles)
            ],
            "blend_id": blend.id,
            "blend_strategy": blend.strategy,
            "tts_backend": "qwen3_tts",
            "output_audio_path": str(output_path),
            "text": args.text,
        },
    )
    return 0


def _qwen_generated_audio_error(path: Path, label: str) -> str | None:
    if not path.exists():
        return f"{label} must exist."
    if path.stat().st_size <= 0:
        return f"{label} must be non-empty."
    if not is_parseable_wav(path):
        return f"{label} must be a parseable WAV file."
    if not wav_has_audible_signal(path):
        return f"{label} must contain audible signal."
    return None


def _qwen_runtime_config_from_args(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        "model_id": args.model_id,
        "device_map": args.device_map,
        "dtype": args.dtype,
        "attn_implementation": args.attn_implementation,
    }


def _write_report(report_path: Path, payload: dict[str, object]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "report_path": str(report_path)}
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
