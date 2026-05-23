from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from app.cli.create_blend import main as create_blend_main
from app.cli.generate_voice import main as generate_voice_main
from app.cli.import_voice import main as import_voice_main
from app.cli.launch_readiness import main as launch_readiness_main
from app.cli.verify_agent_provider import main as verify_agent_provider_main
from app.cli.verify_qwen_runtime import main as verify_qwen_runtime_main
from app.core.audio import is_parseable_wav, wav_has_audible_signal
from app.models.schemas import AgentProviderKind


DEFAULT_OUTPUT_DIR = Path("data") / "launch-sequence"
SUPPORTED_AGENT_PROVIDERS = list(AgentProviderKind.__args__)
LAUNCH_BLEND_STRATEGY = "multi_reference_prompt"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the full terminal launch sequence from a JSON manifest.")
    parser.add_argument("--manifest", required=True, help="Path to the launch sequence JSON manifest.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for intermediate reports.")
    parser.add_argument("--report", default=str(DEFAULT_OUTPUT_DIR / "sequence-report.json"))
    parser.add_argument("--tasks", default="../TASKS.md", help="TASKS.md path to refresh at the end.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the manifest and write a dry-run report without importing voices or calling providers.",
    )
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    try:
        manifest = _load_manifest(Path(args.manifest))
        _validate_manifest(manifest)
        if args.dry_run:
            _write_report(
                report_path,
                {
                    "status": "passed",
                    "mode": "dry_run",
                    "voice_count": len(manifest["voices"]),
                    "speaker_display_names": [
                        str(voice["speaker_display_name"]).strip() for voice in manifest["voices"]
                    ],
                },
            )
            return 0
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        imported_voice_ids = _run_voice_imports(manifest["voices"], output_dir)
        blend_id = _run_blend_creation(manifest, imported_voice_ids, output_dir)
        _run_agent_provider_verification(manifest["agent_provider"])
        _run_qwen_verification(manifest, imported_voice_ids)
        _run_generation(manifest, blend_id, output_dir)
        readiness_exit_code = launch_readiness_main(
            [
                "--report",
                str(Path("data") / "launch-readiness-report.json"),
                "--tasks",
                str(args.tasks),
            ]
        )
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        _write_report(report_path, {"status": "failed", "error": str(exc)})
        return 2

    if readiness_exit_code != 0:
        _write_report(
            report_path,
            {
                "status": "failed",
                "error": "Launch readiness remained blocked after the sequence.",
            },
        )
        return 1

    _write_report(
        report_path,
        {
            "status": "passed",
            "voice_profile_ids": imported_voice_ids,
            "blend_id": blend_id,
            "launch_readiness_report": str(Path("data") / "launch-readiness-report.json"),
        },
    )
    return 0


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _validate_manifest(manifest: dict[str, Any]) -> None:
    voices = manifest.get("voices", [])
    if len(voices) < 2:
        raise ValueError("Launch sequence manifest requires at least two voices.")
    normalized_speakers: set[str] = set()
    for index, voice in enumerate(voices, start=1):
        if not isinstance(voice, dict):
            raise ValueError(f"voices[{index}] must be an object.")
        _require(voice, "speaker_display_name", f"voices[{index}]")
        _require(voice, "confirmed_by", f"voices[{index}]")
        _require(voice, "reference_text", f"voices[{index}]")
        _require(voice, "audio", f"voices[{index}]")
        _validate_voice_weight(voice, index)
        normalized_speakers.add(str(voice["speaker_display_name"]).strip().casefold())
        audio_path = Path(str(voice["audio"]))
        if not audio_path.exists():
            raise ValueError(f"voices[{index}].audio does not exist: {audio_path}")
        if not audio_path.is_file():
            raise ValueError(f"voices[{index}].audio must be a file: {audio_path}")
        if not is_parseable_wav(audio_path):
            raise ValueError(f"voices[{index}].audio must be a parseable WAV file: {audio_path}")
        if not wav_has_audible_signal(audio_path):
            raise ValueError(f"voices[{index}].audio must contain audible signal: {audio_path}")
    if len(normalized_speakers) < 2:
        raise ValueError("Launch sequence manifest requires at least two distinct speaker display names.")
    blend = _optional_object(manifest.get("blend"), "blend")
    if "name" in blend and not str(blend["name"]).strip():
        raise ValueError("blend.name must not be blank when provided.")
    if str(blend.get("strategy", LAUNCH_BLEND_STRATEGY)) != LAUNCH_BLEND_STRATEGY:
        raise ValueError("blend.strategy must be multi_reference_prompt for Qwen launch generation.")
    provider = _optional_object(manifest.get("agent_provider"), "agent_provider")
    _require(provider, "provider", "agent_provider")
    _require(provider, "model", "agent_provider")
    _require(provider, "base_url", "agent_provider")
    if str(provider["provider"]) not in SUPPORTED_AGENT_PROVIDERS:
        raise ValueError(
            "agent_provider.provider must be one of: "
            f"{', '.join(SUPPORTED_AGENT_PROVIDERS)}."
        )
    if "prompt" in provider and not str(provider["prompt"]).strip():
        raise ValueError("agent_provider.prompt must not be blank when provided.")
    generation = _optional_object(manifest.get("generation"), "generation")
    _require(generation, "prompt", "generation")
    qwen = _optional_object(manifest.get("qwen"), "qwen")
    if "text" in qwen and not str(qwen["text"]).strip():
        raise ValueError("qwen.text must not be blank when provided.")
    _validate_optional_qwen_runtime_options(qwen)


def _require(payload: dict[str, Any], key: str, label: str) -> None:
    if not str(payload.get(key, "")).strip():
        raise ValueError(f"{label}.{key} is required.")


def _optional_object(payload: Any, label: str) -> dict[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be an object.")
    return payload


def _validate_voice_weight(voice: dict[str, Any], index: int) -> None:
    if "weight" not in voice:
        return
    try:
        weight = float(voice["weight"])
    except (TypeError, ValueError):
        raise ValueError(f"voices[{index}].weight must be a positive number.") from None
    if weight <= 0:
        raise ValueError(f"voices[{index}].weight must be a positive number.")


def _validate_optional_qwen_runtime_options(qwen: dict[str, Any]) -> None:
    for key in ("model_id", "device_map", "dtype", "attn_implementation"):
        if key in qwen and not str(qwen[key]).strip():
            raise ValueError(f"qwen.{key} must not be blank when provided.")


def _run_voice_imports(voices: list[dict[str, Any]], output_dir: Path) -> list[str]:
    imported_voice_ids: list[str] = []
    for index, voice in enumerate(voices, start=1):
        metadata_path = output_dir / f"voice-{index}.json"
        exit_code = import_voice_main(
            [
                "--speaker-display-name",
                str(voice["speaker_display_name"]),
                "--confirmed-by",
                str(voice["confirmed_by"]),
                "--notes",
                str(voice.get("notes", "")),
                "--reference-text",
                str(voice["reference_text"]),
                "--audio",
                str(voice["audio"]),
                "--metadata",
                str(metadata_path),
            ]
        )
        if exit_code != 0:
            raise ValueError(f"Voice import failed for {voice['speaker_display_name']}.")
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        imported_voice_ids.append(str(payload["id"]))
    return imported_voice_ids


def _run_blend_creation(manifest: dict[str, Any], voice_ids: list[str], output_dir: Path) -> str:
    blend = manifest.get("blend") or {}
    metadata_path = output_dir / "blend.json"
    args = [
        "--name",
        str(blend.get("name", "Launch blend")),
        "--strategy",
        str(blend.get("strategy", LAUNCH_BLEND_STRATEGY)),
        "--metadata",
        str(metadata_path),
    ]
    for voice_id, voice in zip(voice_ids, manifest["voices"]):
        args.extend(["--profile", f"{voice_id}={voice.get('weight', 1)}"])
    exit_code = create_blend_main(args)
    if exit_code != 0:
        raise ValueError("Blend creation failed.")
    return str(json.loads(metadata_path.read_text(encoding="utf-8"))["id"])


def _run_agent_provider_verification(provider: dict[str, Any]) -> None:
    args = [
        "--provider",
        str(provider["provider"]),
        "--model",
        str(provider["model"]),
        "--base-url",
        str(provider["base_url"]),
        "--api-key",
        str(provider.get("api_key", "")),
        "--system-prompt",
        str(provider.get("system_prompt", "You are a disclosed synthetic mixed-voice assistant.")),
        "--report",
        str(Path("data") / "agent-provider-verification-report.json"),
    ]
    if provider.get("prompt"):
        args.extend(["--prompt", str(provider["prompt"])])
    if verify_agent_provider_main(args) != 0:
        raise ValueError("Agent provider verification failed.")


def _run_qwen_verification(manifest: dict[str, Any], voice_ids: list[str]) -> None:
    qwen = manifest.get("qwen") or {}
    args = [
        "--text",
        str(qwen.get("text", "This is a disclosed synthetic mixed voice runtime verification.")),
        "--report",
        str(Path("data") / "qwen-runtime-verification-report.json"),
    ]
    for voice_id in voice_ids:
        args.extend(["--voice-profile-id", voice_id])
    _append_optional_qwen_args(args, qwen)
    if verify_qwen_runtime_main(args) != 0:
        raise ValueError("Qwen runtime verification failed.")


def _run_generation(manifest: dict[str, Any], blend_id: str, output_dir: Path) -> None:
    provider = manifest["agent_provider"]
    qwen = manifest.get("qwen") or {}
    generation = manifest["generation"]
    args = [
        "--blend-id",
        blend_id,
        "--prompt",
        str(generation["prompt"]),
        "--provider",
        str(provider["provider"]),
        "--model",
        str(provider["model"]),
        "--base-url",
        str(provider["base_url"]),
        "--api-key",
        str(provider.get("api_key", "")),
        "--system-prompt",
        str(provider.get("system_prompt", "You are a disclosed synthetic mixed-voice assistant.")),
        "--metadata",
        str(output_dir / "generation.json"),
    ]
    _append_optional_qwen_generation_args(args, qwen)
    if generate_voice_main(args) != 0:
        raise ValueError("Qwen mixed voice generation failed.")


def _append_optional_qwen_args(args: list[str], qwen: dict[str, Any]) -> None:
    mapping = {
        "model_id": "--model-id",
        "device_map": "--device-map",
        "dtype": "--dtype",
        "attn_implementation": "--attn-implementation",
    }
    for key, option in mapping.items():
        if qwen.get(key) is not None:
            args.extend([option, str(qwen[key])])


def _append_optional_qwen_generation_args(args: list[str], qwen: dict[str, Any]) -> None:
    mapping = {
        "model_id": "--qwen-model-id",
        "device_map": "--qwen-device-map",
        "dtype": "--qwen-dtype",
        "attn_implementation": "--qwen-attn-implementation",
    }
    for key, option in mapping.items():
        if qwen.get(key) is not None:
            args.extend([option, str(qwen[key])])


def _write_report(report_path: Path, payload: dict[str, object]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
