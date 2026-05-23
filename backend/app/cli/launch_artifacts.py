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
TASKS_ARTIFACT_SECTION_HEADING = "## Launch Artifact Inventory"
PRUNE_REPORT_PATH = Path("data") / "prune-launch-artifacts-report.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inventory launch artifacts and print the next concrete commands.")
    parser.add_argument(
        "--report",
        default="data/launch-artifacts-report.json",
        help="Path to write the JSON artifact inventory.",
    )
    parser.add_argument(
        "--tasks",
        help="Optional TASKS.md path to update with launch artifact inventory.",
    )
    parser.add_argument("--summary", action="store_true", help="Print a concise inventory and command summary.")
    args = parser.parse_args(argv)

    report = collect_launch_artifacts()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.tasks:
        update_tasks_handoff(Path(args.tasks), report)

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
    usable_distinct_voice_ids = _select_distinct_speaker_voice_ids(voices, usable_voice_ids)
    blend_statuses = [_blend_status(blend, usable_voice_ids, voices) for blend in blends]
    launch_eligible_blend_ids = [
        blend.id for blend, status in zip(blends, blend_statuses, strict=True) if status["launch_eligible"]
    ]
    stale_blend_ids = [
        blend.id for blend, status in zip(blends, blend_statuses, strict=True) if not status["launch_eligible"]
    ]
    generation_statuses = [_generation_status(generation, blends) for generation in generations]
    launch_eligible_generation_ids = [
        generation.id
        for generation, status in zip(generations, generation_statuses, strict=True)
        if status["launch_eligible"]
    ]
    stale_generation_ids = [
        generation.id
        for generation, status in zip(generations, generation_statuses, strict=True)
        if not status["launch_eligible"]
    ]
    reviewed_prune_apply_command = _reviewed_prune_apply_command(stale_blend_ids)

    return {
        "voice_count": len(voices),
        "usable_voice_count": len(usable_voice_ids),
        "unusable_voice_count": len(voices) - len(usable_voice_ids),
        "distinct_usable_speaker_count": len(usable_distinct_voice_ids),
        "blend_count": len(blends),
        "launch_eligible_blend_count": len(launch_eligible_blend_ids),
        "stale_blend_count": len(stale_blend_ids),
        "generation_count": len(generations),
        "qwen_generation_count": sum(1 for generation in generations if generation.tts_backend == "qwen3_tts"),
        "launch_eligible_generation_count": len(launch_eligible_generation_ids),
        "stale_generation_count": len(stale_generation_ids),
        "voices": [_voice_payload(voice, status) for voice, status in zip(voices, voice_statuses, strict=True)],
        "usable_voice_ids": usable_voice_ids,
        "usable_distinct_voice_ids": usable_distinct_voice_ids,
        "launch_eligible_blend_ids": launch_eligible_blend_ids,
        "stale_blend_ids": stale_blend_ids,
        "reviewed_prune_apply_command": reviewed_prune_apply_command,
        "stale_blend_reason_counts": _reason_counts(
            status["stale_reasons"] for status in blend_statuses if not status["launch_eligible"]
        ),
        "launch_eligible_generation_ids": launch_eligible_generation_ids,
        "stale_generation_ids": stale_generation_ids,
        "blends": [_blend_payload(blend, status) for blend, status in zip(blends, blend_statuses, strict=True)],
        "generations": [
            _generation_payload(generation, status)
            for generation, status in zip(generations, generation_statuses, strict=True)
        ],
        "agent_provider": agent_provider.model_dump(mode="json"),
        "agent_provider_commands": _agent_provider_commands(),
        "qwen_verification": qwen_verification.model_dump(mode="json"),
        "qwen_runtime": qwen_runtime.model_dump(mode="json"),
        "next_commands": _next_commands(
            usable_voice_ids=usable_voice_ids,
            usable_distinct_voice_ids=usable_distinct_voice_ids,
            blends=blends,
            stale_blend_ids=stale_blend_ids,
            generation_statuses=generation_statuses,
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


def _generation_payload(generation: GenerationResult, status: dict[str, object]) -> dict[str, object]:
    return {
        "id": generation.id,
        "tts_backend": generation.tts_backend,
        "blend_id": generation.blend_id,
        "blend_name": generation.blend_name,
        "audio_path": generation.audio_path,
        "metadata_path": generation.metadata_path,
        "source_profile_ids": generation.source_profile_ids,
        **status,
    }


def _reason_counts(reason_groups: Sequence[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for reasons in reason_groups:
        for reason in reasons:
            counts[str(reason)] = counts.get(str(reason), 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _reviewed_prune_apply_command(stale_blend_ids: list[str]) -> str | None:
    if not stale_blend_ids or not PRUNE_REPORT_PATH.exists():
        return None
    try:
        payload = json.loads(PRUNE_REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("mode") != "dry_run":
        return None
    if sorted(payload.get("stale_blend_ids", [])) != sorted(stale_blend_ids):
        return None
    command = payload.get("reviewed_apply_command")
    return command if isinstance(command, str) and command.strip() else None


def _next_commands(
    *,
    usable_voice_ids: list[str],
    usable_distinct_voice_ids: list[str],
    blends: list[VoiceBlend],
    stale_blend_ids: list[str],
    generation_statuses: list[dict[str, object]],
    agent_provider_status: str,
    qwen_verification_status: str,
    qwen_runtime_available: bool,
) -> list[str]:
    commands: list[str] = []
    if stale_blend_ids:
        commands.append("python -m app.cli.prune_launch_artifacts --report data/prune-launch-artifacts-report.json")
    if len(usable_voice_ids) < 2 or len(usable_distinct_voice_ids) < 2:
        commands.append(
            "python -m app.cli.run_launch_sequence --write-template data/launch-sequence/launch-manifest.template.json"
        )
        return commands

    selected_voice_ids = usable_distinct_voice_ids[:2]
    launch_blend_id = _blend_id_for_voices(blends, selected_voice_ids)
    if launch_blend_id is None:
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
    if not any(status["launch_eligible"] for status in generation_statuses):
        blend_id = launch_blend_id or "<saved-blend-id>"
        commands.append(
            "python -m app.cli.generate_voice "
            f"--blend-id {blend_id} --prompt <prompt> "
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
    return _blend_id_for_voices(blends, voice_ids) is not None


def _blend_id_for_voices(blends: list[VoiceBlend], voice_ids: list[str]) -> str | None:
    selected = set(voice_ids)
    for blend in blends:
        blend_ids = {profile.voice_profile_id for profile in blend.profiles}
        if selected.issubset(blend_ids) and blend.strategy == "multi_reference_prompt":
            return blend.id
    return None


def _blend_status(blend: VoiceBlend, usable_voice_ids: list[str], voices: list[VoiceProfile]) -> dict[str, object]:
    usable_ids = set(usable_voice_ids)
    voice_by_id = {voice.id: voice for voice in voices}
    blend_ids = [profile.voice_profile_id for profile in blend.profiles]
    missing_voice_profile_ids = sorted({voice_id for voice_id in blend_ids if voice_id not in usable_ids})
    distinct_speakers = {
        voice_by_id[voice_id].display_name.strip().casefold()
        for voice_id in set(blend_ids)
        if voice_id in voice_by_id and voice_by_id[voice_id].display_name.strip()
    }
    launch_eligible = (
        blend.strategy == "multi_reference_prompt"
        and len(set(blend_ids)) >= 2
        and len(distinct_speakers) >= 2
        and not missing_voice_profile_ids
    )
    stale_reasons: list[str] = []
    if blend.strategy != "multi_reference_prompt":
        stale_reasons.append("Blend must use the multi_reference_prompt strategy for Qwen launch.")
    if len(set(blend_ids)) < 2:
        stale_reasons.append("Blend must reference at least two imported voice profiles.")
    if len(distinct_speakers) < 2:
        stale_reasons.append("Blend must reference at least two distinct speaker display names.")
    if missing_voice_profile_ids:
        stale_reasons.append(
            "Blend references voices that are missing or not launch-usable: "
            f"{', '.join(missing_voice_profile_ids)}."
        )
    return {
        "launch_eligible": launch_eligible,
        "missing_voice_profile_ids": missing_voice_profile_ids,
        "stale_reasons": [] if launch_eligible else stale_reasons,
    }


def _select_distinct_speaker_voice_ids(voices: list[VoiceProfile], usable_voice_ids: list[str]) -> list[str]:
    usable_ids = set(usable_voice_ids)
    selected: list[str] = []
    seen_speakers: set[str] = set()
    for voice in voices:
        if voice.id not in usable_ids:
            continue
        speaker_key = voice.display_name.strip().casefold()
        if not speaker_key or speaker_key in seen_speakers:
            continue
        selected.append(voice.id)
        seen_speakers.add(speaker_key)
    return selected


def _generation_status(generation: GenerationResult, blends: list[VoiceBlend]) -> dict[str, object]:
    reasons: list[str] = []
    if generation.tts_backend != "qwen3_tts":
        return {
            "launch_eligible": False,
            "stale_reasons": ["Generation was not created with Qwen3-TTS."],
        }
    if generation.blend_strategy != "multi_reference_prompt":
        reasons.append("Qwen generation must use the multi_reference_prompt blend strategy.")
    if len(generation.source_profile_details) < 2:
        reasons.append("Qwen generation must include at least two imported source profile details.")
    elif sorted(detail.voice_profile_id for detail in generation.source_profile_details) != sorted(
        generation.source_profile_ids
    ):
        reasons.append("Qwen generation source details must match generated source profile ids.")
    if not all(detail.reference_text_present for detail in generation.source_profile_details):
        reasons.append("Qwen generation source details must include reference transcripts.")
    if not all(REQUIRED_VOICE_USE in detail.allowed_uses for detail in generation.source_profile_details):
        reasons.append("Qwen generation source details must allow private agent voice synthesis.")
    distinct_speakers = {
        detail.display_name.strip().casefold()
        for detail in generation.source_profile_details
        if detail.display_name.strip()
    }
    if len(generation.source_profile_details) >= 2 and len(distinct_speakers) < 2:
        reasons.append("Qwen generation must include at least two distinct source speakers.")
    if generation.agent_trace is None:
        reasons.append("Qwen generation must include an agent provider trace.")
    if not generation.prompt.strip() or not generation.agent_reply.strip():
        reasons.append("Qwen generation must include the agent prompt and spoken reply transcript.")
    if not _generation_references_current_blend(generation, blends):
        reasons.append("Qwen generation must reference a current saved blend.")
    audio_path = Path(generation.audio_path)
    if not audio_path.exists():
        reasons.append("Qwen generation audio is missing.")
    elif audio_path.stat().st_size == 0:
        reasons.append("Qwen generation audio must be non-empty.")
    return {
        "launch_eligible": not reasons,
        "stale_reasons": reasons,
    }


def _generation_references_current_blend(generation: GenerationResult, blends: list[VoiceBlend]) -> bool:
    if not generation.blend_id:
        return False
    matching_blend = next((blend for blend in blends if blend.id == generation.blend_id), None)
    if matching_blend is None:
        return False
    return (
        matching_blend.name == generation.blend_name
        and matching_blend.strategy == generation.blend_strategy
        and matching_blend.profiles == generation.source_profiles
    )


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


def update_tasks_handoff(tasks_path: Path, report: dict[str, object]) -> None:
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    existing = tasks_path.read_text(encoding="utf-8") if tasks_path.exists() else "# TASKS\n"
    section = _tasks_handoff_section(report)
    heading_index = _find_heading_index(existing, TASKS_ARTIFACT_SECTION_HEADING)
    if heading_index == -1:
        separator = "" if existing.endswith("\n\n") else "\n\n"
        tasks_path.write_text(f"{existing}{separator}{section}", encoding="utf-8")
        return

    next_heading_index = _find_next_section_heading_index(existing, heading_index + 1)
    if next_heading_index == -1:
        updated = f"{existing[:heading_index].rstrip()}\n\n{section}"
    else:
        updated = f"{existing[:heading_index].rstrip()}\n\n{section}\n{existing[next_heading_index:].lstrip()}"
    tasks_path.write_text(updated, encoding="utf-8")


def _find_heading_index(content: str, heading: str) -> int:
    offset = 0
    for line in content.splitlines(keepends=True):
        if line.strip() == heading:
            return offset
        offset += len(line)
    return -1


def _find_next_section_heading_index(content: str, start: int) -> int:
    offset = 0
    for line in content.splitlines(keepends=True):
        if offset >= start and line.startswith("## "):
            return offset
        offset += len(line)
    return -1


def _tasks_handoff_section(report: dict[str, object]) -> str:
    qwen_runtime = report["qwen_runtime"]
    runtime_label = "available" if qwen_runtime["available"] else "unavailable"
    runtime_model = qwen_runtime.get("model_id") or "unknown model"
    lines = [
        TASKS_ARTIFACT_SECTION_HEADING,
        "",
        "- Voices: "
        f"`{report['voice_count']}` total; `{report['usable_voice_count']}` usable; "
        f"`{report['unusable_voice_count']}` unusable; "
        f"`{report['distinct_usable_speaker_count']}` distinct usable speakers",
        "- Blends: "
        f"`{report['blend_count']}` total; `{report['launch_eligible_blend_count']}` launch-eligible; "
        f"`{report['stale_blend_count']}` stale/nonmatching",
        "- Generations: "
        f"`{report['generation_count']}` total; `{report['qwen_generation_count']}` Qwen; "
        f"`{report['launch_eligible_generation_count']}` launch-eligible; "
        f"`{report['stale_generation_count']}` stale/nonmatching",
        f"- Usable voice IDs: {_format_inline_ids(report['usable_voice_ids'])}",
        f"- Usable distinct-speaker voice IDs: {_format_inline_ids(report['usable_distinct_voice_ids'])}",
        f"- Launch-eligible blend IDs: {_format_inline_ids(report['launch_eligible_blend_ids'])}",
        f"- Launch-eligible generation IDs: {_format_inline_ids(report['launch_eligible_generation_ids'])}",
        f"- Provider preflight status: `{report['agent_provider']['status']}`",
        f"- Qwen verification status: `{report['qwen_verification']['status']}`",
        f"- Qwen runtime: `{runtime_label}` (`{runtime_model}`)",
    ]
    unusable_voices = [voice for voice in report["voices"] if not voice["launch_usable"]]
    if unusable_voices:
        lines.extend(["", "Unusable voices:"])
        for voice in unusable_voices:
            reasons = "; ".join(voice["unusable_reasons"])
            lines.append(f"- `{voice['id']}` {voice['display_name']}: {reasons}")
    stale_blend_reason_counts = report.get("stale_blend_reason_counts", {})
    if stale_blend_reason_counts:
        lines.extend(["", "Stale blend reason summary:"])
        for reason, count in stale_blend_reason_counts.items():
            lines.append(f"- `{count}` {reason}")
    if report.get("reviewed_prune_apply_command"):
        lines.extend(
            [
                "",
                "Reviewed prune apply command:",
                f"- [ ] `{report['reviewed_prune_apply_command']}`",
            ]
        )
    provider_commands = report.get("agent_provider_commands", {})
    if provider_commands:
        lines.extend(["", "Provider preflight command options:"])
        for label, key in (
            ("ChatGPT", "chatgpt"),
            ("Claude", "claude"),
            ("Grok", "grok"),
            ("Gemini", "gemini"),
            ("API", "openai_compatible_api"),
            ("Local", "local_ollama"),
        ):
            lines.append(f"- {label}: `{provider_commands[key]}`")
    stale_generations = [generation for generation in report["generations"] if not generation["launch_eligible"]]
    if stale_generations:
        lines.extend(["", "Stale/nonmatching generations:"])
        for generation in stale_generations:
            reasons = "; ".join(generation["stale_reasons"])
            lines.append(f"- `{generation['id']}` {generation['tts_backend']}: {reasons}")
    if report["next_commands"]:
        lines.extend(["", "Next artifact commands:"])
        lines.extend(f"- [ ] `{command}`" for command in report["next_commands"])
    return "\n".join(lines) + "\n"


def _format_inline_ids(ids: list[str]) -> str:
    if not ids:
        return "`none`"
    return ", ".join(f"`{item}`" for item in ids)


def _print_summary(report: dict[str, object]) -> None:
    print(
        "Launch artifacts: "
        f"{report['voice_count']} voices, {report['blend_count']} blends, {report['generation_count']} generations"
    )
    print(f"Usable voices: {report['usable_voice_count']}; unusable voices: {report['unusable_voice_count']}")
    print(f"Distinct usable speakers: {report['distinct_usable_speaker_count']}")
    print(
        "Launch-eligible blends: "
        f"{report['launch_eligible_blend_count']}; stale/nonmatching blends: {report['stale_blend_count']}"
    )
    print(
        "Qwen launch-eligible generations: "
        f"{report['launch_eligible_generation_count']}; "
        f"stale/nonmatching generations: {report['stale_generation_count']}"
    )
    for voice in report["voices"]:
        if voice["launch_usable"]:
            print(f"{voice['id']}: {voice['display_name']}")
        else:
            reasons = "; ".join(voice["unusable_reasons"])
            print(f"{voice['id']}: {voice['display_name']} (unusable: {reasons})")
    for generation in report["generations"]:
        if generation["launch_eligible"]:
            print(f"{generation['id']}: {generation['tts_backend']}")
        else:
            reasons = "; ".join(generation["stale_reasons"])
            print(f"{generation['id']}: {generation['tts_backend']} (stale: {reasons})")
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
