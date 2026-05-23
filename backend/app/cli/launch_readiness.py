from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Sequence

from app.core.launch import LAUNCH_ACTIONS, evaluate_launch_readiness as evaluate_core_launch_readiness
from app.models.schemas import LaunchReadinessReport


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
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a concise launch status and next-action summary.",
    )
    args = parser.parse_args(argv)

    report = evaluate_launch_readiness()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    if args.tasks:
        update_tasks_handoff(Path(args.tasks), report)
    if args.summary:
        print_launch_summary(report)
    return 0 if report.status == "ready" else 1


def evaluate_launch_readiness() -> LaunchReadinessReport:
    return evaluate_core_launch_readiness()


def update_tasks_handoff(tasks_path: Path, report: LaunchReadinessReport) -> None:
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    existing = tasks_path.read_text(encoding="utf-8") if tasks_path.exists() else "# TASKS\n"
    section = _tasks_handoff_section(report)
    heading_index = _find_heading_index(existing, TASKS_SECTION_HEADING)
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


def print_launch_summary(report: LaunchReadinessReport) -> None:
    print(f"Launch readiness: {report.status}")
    next_actions = {
        action.check_id: action.action
        for action in (report.next_actions or _fallback_next_actions(report))
    }
    for check in report.checks:
        marker = "x" if check.passed else " "
        print(f"[{marker}] {check.label}: {check.detail}")
        if not check.passed and check.id in next_actions:
            print(f"    Next: {next_actions[check.id]}")
    if report.blocking_reasons:
        print("Blocking reasons:")
        for reason in report.blocking_reasons:
            print(f"- {reason}")


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
    next_actions = report.next_actions or _fallback_next_actions(report)
    for action in next_actions:
        lines.append(f"- [ ] {action.check_id}: {action.action}")
        lines.append(f"  Evidence: {action.evidence}")
    if report.blocking_reasons:
        lines.extend(["", "Blocking reasons:"])
        lines.extend(f"- {reason}" for reason in report.blocking_reasons)
    return "\n".join(lines) + "\n"


def _fallback_next_actions(report: LaunchReadinessReport):
    return [
        SimpleNamespace(
            check_id=check.id,
            action=LAUNCH_ACTIONS.get(check.id, check.label),
            evidence=check.detail,
        )
        for check in report.checks
        if not check.passed
    ]


if __name__ == "__main__":
    raise SystemExit(main())
