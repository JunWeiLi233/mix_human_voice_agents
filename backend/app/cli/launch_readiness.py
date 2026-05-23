from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.core.launch import evaluate_launch_readiness as evaluate_core_launch_readiness
from app.models.schemas import LaunchReadinessReport


TASK_ACTIONS = {
    "research_review": "Refresh docs/research-review.md with a current Last checked date.",
    "imported_voices": "Import two consented WAV voice samples with matching transcripts.",
    "saved_blend": "Create and save a multi-reference blend from imported voices.",
    "generated_audio": "Generate a Qwen mixed voice clip with imported source details.",
    "agent_provider": "Run Test provider and keep the passed provider verification report.",
    "qwen_runtime": "Install and load qwen-tts with the selected Qwen model.",
    "qwen_verification": "Run Qwen verification with two imported voices and keep the passed report.",
}

TASKS_SECTION_HEADING = "## Launch Readiness Remaining Tasks"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a local launch-readiness audit report.")
    parser.add_argument(
        "--report",
        default="data/launch-readiness-report.json",
        help="Path to write the JSON launch-readiness report.",
    )
    parser.add_argument(
        "--tasks",
        help="Optional TASKS.md path to update with remaining launch-readiness work.",
    )
    args = parser.parse_args(argv)

    report = evaluate_launch_readiness()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    if args.tasks:
        update_tasks_handoff(Path(args.tasks), report)
    return 0 if report.status == "ready" else 1


def evaluate_launch_readiness() -> LaunchReadinessReport:
    return evaluate_core_launch_readiness()


def update_tasks_handoff(tasks_path: Path, report: LaunchReadinessReport) -> None:
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    existing = tasks_path.read_text(encoding="utf-8") if tasks_path.exists() else "# TASKS\n"
    section = _tasks_handoff_section(report)
    heading_index = existing.find(TASKS_SECTION_HEADING)
    if heading_index == -1:
        separator = "" if existing.endswith("\n\n") else "\n\n"
        tasks_path.write_text(f"{existing}{separator}{section}", encoding="utf-8")
        return

    next_heading_index = existing.find("\n## ", heading_index + 1)
    if next_heading_index == -1:
        updated = f"{existing[:heading_index].rstrip()}\n\n{section}"
    else:
        updated = f"{existing[:heading_index].rstrip()}\n\n{section}\n{existing[next_heading_index + 1:].lstrip()}"
    tasks_path.write_text(updated, encoding="utf-8")


def _tasks_handoff_section(report: LaunchReadinessReport) -> str:
    lines = [
        TASKS_SECTION_HEADING,
        "",
        f"- Status: `{report.status}`",
    ]
    if report.checked_at:
        lines.append(f"- Checked at: `{report.checked_at.isoformat()}`")
    if report.status == "ready":
        lines.extend(["", "- [x] Launch readiness report has no remaining blockers."])
        return "\n".join(lines) + "\n"

    lines.extend(["", "The following tasks are generated from failed launch-readiness checks:"])
    for check in report.checks:
        if check.passed:
            continue
        action = TASK_ACTIONS.get(check.id, check.label)
        lines.append(f"- [ ] {check.id}: {action}")
        lines.append(f"  Evidence: {check.detail}")
    if report.blocking_reasons:
        lines.extend(["", "Blocking reasons:"])
        lines.extend(f"- {reason}" for reason in report.blocking_reasons)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
