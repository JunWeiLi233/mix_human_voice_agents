from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.core.launch import get_agent_provider_verification_report, get_qwen_verification_report
from app.core.storage import list_blends, list_generation_results, list_voice_profiles
from app.models.schemas import GenerationResult, VoiceBlend, VoiceProfile
from app.tts.qwen import QwenTtsAdapter


REQUIRED_VOICE_USE = "private_agent_voice"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inventory launch artifacts and print the next concrete commands.")
    parser.add_argument(
        "--report",
        default="data/launch-artifacts-report.json",
        help="Path to write the JSON artifact inventory.",
    )
    parser.add_argument("--summary", action="store_true", help="Print a concise inventory and command summary.")
    args = parser.parse_args(argv)

    report = collect_launch_artifacts()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.summary:
        _print_summary(report)
    return 0


def collect_launch_artifacts() -> dict[str, object]:
    voices = list_voice_profiles()
    blends = list_blends()
    generations = list_generation_results()
    agent_provider = get_agent_provider_verification_report()
    qwen_verification = get_qwen_verification_report()
    qwen_runtime = QwenTtsAdapter.runtime_status()
    voice_statuses = [_voice_status(voice) for voice in voices]
    usable_voice_ids = [
        voice.id for voice, status in zip(voices, voice_statuses, strict=True) if status["launch_usable"]
    ]
    blend_statuses = [_blend_status(blend, usable_voice_ids) for blend in blends]
    launch_eligible_blend_ids = [
        blend.id for blend, status in zip(blends, blend_statuses, strict=True) if status["launch_eligible"]
    ]
    stale_blend_ids = [
        blend.id for blend, status in zip(blends, blend_statuses, strict=True) if not status["launch_eligible"]
    ]

    return {
        "voice_count": len(voices),
        "usable_voice_count": len(usable_voice_ids),
        "unusable_voice_count": len(voices) - len(usable_voice_ids),
        "blend_count": len(blends),
        "launch_eligible_blend_count": len(launch_eligible_blend_ids),
        "stale_blend_count": len(stale_blend_ids),
        "generation_count": len(generations),
        "voices": [_voice_payload(voice, status) for voice, status in zip(voices, voice_statuses, strict=True)],
        "usable_voice_ids": usable_voice_ids,
        "launch_eligible_blend_ids": launch_eligible_blend_ids,
        "stale_blend_ids": stale_blend_ids,
        "blends": [_blend_payload(blend, status) for blend, status in zip(blends, blend_statuses, strict=True)],
        "generations": [_generation_payload(generation) for generation in generations],
        "agent_provider": agent_provider.model_dump(mode="json"),
        "agent_provider_commands": _agent_provider_commands(),
        "qwen_verification": qwen_verification.model_dump(mode="json"),
        "qwen_runtime": qwen_runtime.model_dump(mode="json"),
        "next_commands": _next_commands(
            usable_voice_ids=usable_voice_ids,
            blends=blends,
            generations=generations,
            agent_provider_status=agent_provider.status,
            qwen_verification_status=qwen_verification.status,
            qwen_runtime_available=qwen_runtime.available,
        ),
    }


def _voice_payload(voice: VoiceProfile, status: dict[str, object]) -> dict[str, object]:
    return {
        "id": voice.id,
        "display_name": voice.display_name,
        "private_agent_voice": _voice_allows_private_agent_voice(voice),
        "reference_text_present": bool(voice.reference_text.strip()),
        "quality_warnings": voice.quality.warnings,
        "source_audio_path": voice.source_audio_path,
        "cleaned_audio_path": voice.cleaned_audio_path,
        **status,
    }


def _blend_payload(blend: VoiceBlend, status: dict[str, object]) -> dict[str, object]:
    return {
        "id": blend.id,
        "name": blend.name,
        "strategy": blend.strategy,
        "voice_profile_ids": [profile.voice_profile_id for profile in blend.profiles],
        "profiles": [profile.model_dump(mode="json") for profile in blend.profiles],
        **status,
    }


def _generation_payload(generation: GenerationResult) -> dict[str, object]:
    return {
        "id": generation.id,
        "tts_backend": generation.tts_backend,
        "blend_id": generation.blend_id,
        "blend_name": generation.blend_name,
        "audio_path": generation.audio_path,
        "metadata_path": generation.metadata_path,
        "source_profile_ids": generation.source_profile_ids,
    }


def _next_commands(
    *,
    usable_voice_ids: list[str],
    blends: list[VoiceBlend],
    generations: list[GenerationResult],
    agent_provider_status: str,
    qwen_verification_status: str,
    qwen_runtime_available: bool,
) -> list[str]:
    commands: list[str] = []
    if len(usable_voice_ids) < 2:
        commands.append(
            "python -m app.cli.run_launch_sequence --write-template data/launch-sequence/launch-manifest.template.json"
        )
        return commands

    selected_voice_ids = usable_voice_ids[:2]
    if not _has_blend_for_voices(blends, selected_voice_ids):
        profiles = " ".join(f"--profile {voice_id}=1" for voice_id in selected_voice_ids)
        commands.append(
            'python -m app.cli.create_blend --name "Launch mixed voice" '
            f"--strategy multi_reference_prompt {profiles}"
        )
    if agent_provider_status != "passed":
        commands.append(_agent_provider_commands()["openai_compatible_api"])
    if qwen_runtime_available and qwen_verification_status != "passed":
        profile_args = " ".join(f"--voice-profile-id {voice_id}" for voice_id in selected_voice_ids)
        commands.append(f"python -m app.cli.verify_qwen_runtime {profile_args}")
    if not any(generation.tts_backend == "qwen3_tts" for generation in generations):
        commands.append(
            "python -m app.cli.generate_voice "
            "--blend-id <saved-blend-id> --prompt <prompt> "
            "--provider openai_compatible --model <model> --base-url <base-url> --api-key <api-key>"
        )
    return commands


def _agent_provider_commands() -> dict[str, str]:
    return {
        "chatgpt": (
            "python -m app.cli.verify_agent_provider --provider openai "
            "--model gpt-4.1-mini --base-url https://api.openai.com/v1 --api-key <openai-api-key>"
        ),
        "claude": (
            "python -m app.cli.verify_agent_provider --provider anthropic "
            "--model claude-sonnet-4-5 --base-url https://api.anthropic.com --api-key <anthropic-api-key>"
        ),
        "grok": (
            "python -m app.cli.verify_agent_provider --provider xai "
            "--model grok-4 --base-url https://api.x.ai/v1 --api-key <xai-api-key>"
        ),
        "gemini": (
            "python -m app.cli.verify_agent_provider --provider google "
            "--model gemini-2.5-flash --base-url https://generativelanguage.googleapis.com/v1beta "
            "--api-key <google-api-key>"
        ),
        "openai_compatible_api": (
            "python -m app.cli.verify_agent_provider --provider openai_compatible "
            "--model <model> --base-url <base-url> --api-key <api-key>"
        ),
        "local_ollama": (
            "python -m app.cli.verify_agent_provider --provider ollama "
            "--model llama3.1 --base-url http://127.0.0.1:11434"
        ),
    }


def _has_blend_for_voices(blends: list[VoiceBlend], voice_ids: list[str]) -> bool:
    selected = set(voice_ids)
    for blend in blends:
        blend_ids = {profile.voice_profile_id for profile in blend.profiles}
        if selected.issubset(blend_ids) and blend.strategy == "multi_reference_prompt":
            return True
    return False


def _blend_status(blend: VoiceBlend, usable_voice_ids: list[str]) -> dict[str, object]:
    usable_ids = set(usable_voice_ids)
    blend_ids = [profile.voice_profile_id for profile in blend.profiles]
    missing_voice_profile_ids = sorted({voice_id for voice_id in blend_ids if voice_id not in usable_ids})
    launch_eligible = (
        blend.strategy == "multi_reference_prompt"
        and len(set(blend_ids)) >= 2
        and not missing_voice_profile_ids
    )
    return {
        "launch_eligible": launch_eligible,
        "missing_voice_profile_ids": missing_voice_profile_ids,
    }


def _voice_is_usable(voice: VoiceProfile) -> bool:
    return bool(_voice_status(voice)["launch_usable"])


def _voice_status(voice: VoiceProfile) -> dict[str, object]:
    reasons: list[str] = []
    if not _voice_allows_private_agent_voice(voice):
        reasons.append("Voice consent does not allow private agent voice synthesis.")
    if not voice.reference_text.strip():
        reasons.append("Reference transcript is missing.")
    if voice.quality.warnings:
        reasons.append("Audio quality warnings must be resolved before launch.")
    return {
        "launch_usable": not reasons,
        "unusable_reasons": reasons,
    }


def _voice_allows_private_agent_voice(voice: VoiceProfile) -> bool:
    return voice.consent.synthetic_voice_allowed and REQUIRED_VOICE_USE in voice.consent.allowed_uses


def _print_summary(report: dict[str, object]) -> None:
    print(
        "Launch artifacts: "
        f"{report['voice_count']} voices, {report['blend_count']} blends, {report['generation_count']} generations"
    )
    print(f"Usable voices: {report['usable_voice_count']}; unusable voices: {report['unusable_voice_count']}")
    print(
        "Launch-eligible blends: "
        f"{report['launch_eligible_blend_count']}; stale/nonmatching blends: {report['stale_blend_count']}"
    )
    for voice in report["voices"]:
        if voice["launch_usable"]:
            print(f"{voice['id']}: {voice['display_name']}")
        else:
            reasons = "; ".join(voice["unusable_reasons"])
            print(f"{voice['id']}: {voice['display_name']} (unusable: {reasons})")
    print("Provider command options:")
    provider_commands = report["agent_provider_commands"]
    for label, key in (
        ("ChatGPT", "chatgpt"),
        ("Claude", "claude"),
        ("Grok", "grok"),
        ("Gemini", "gemini"),
        ("API", "openai_compatible_api"),
        ("Local", "local_ollama"),
    ):
        print(f"{label}: {provider_commands[key]}")
    print("Next commands:")
    for command in report["next_commands"]:
        print(f"- {command}")


if __name__ == "__main__":
    raise SystemExit(main())
