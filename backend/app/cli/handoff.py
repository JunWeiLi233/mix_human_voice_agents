from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.cli.launch_artifacts import main as launch_artifacts_main
from app.cli.launch_readiness import main as launch_readiness_main


USAGE_LIMIT_SECTION_HEADING = "## Usage Limit Handoff"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh TASKS.md before a Codex usage/session/context limit handoff."
    )
    parser.add_argument("--tasks", default="../TASKS.md", help="TASKS.md path to refresh.")
    parser.add_argument(
        "--artifacts-report",
        default="data/launch-artifacts-report.json",
        help="Path to write the launch artifact inventory JSON report.",
    )
    parser.add_argument(
        "--readiness-report",
        default="data/launch-readiness-report.json",
        help="Path to write the launch readiness JSON report.",
    )
    parser.add_argument("--no-summary", action="store_true", help="Do not print artifact/readiness summaries.")
    args = parser.parse_args(argv)

    tasks_path = Path(args.tasks)
    summary_args = [] if args.no_summary else ["--summary"]
    launch_artifacts_main(
        [
            "--report",
            args.artifacts_report,
            "--tasks",
            str(tasks_path),
            *summary_args,
        ]
    )
    launch_readiness_main(
        [
            "--report",
            args.readiness_report,
            "--tasks",
            str(tasks_path),
            *summary_args,
        ]
    )
    update_usage_limit_handoff(tasks_path)
    print(f"Usage-limit handoff written to {tasks_path}")
    return 0


def update_usage_limit_handoff(tasks_path: Path) -> None:
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    existing = tasks_path.read_text(encoding="utf-8") if tasks_path.exists() else "# TASKS\n"
    section = _usage_limit_section()
    heading_index = _find_heading_index(existing, USAGE_LIMIT_SECTION_HEADING)
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


def _usage_limit_section() -> str:
    return "\n".join(
        [
            USAGE_LIMIT_SECTION_HEADING,
            "",
            f"- Last refreshed: `{datetime.now(timezone.utc).isoformat()}`",
            "- Reason: Codex usage/session/context limit handoff.",
            "- Next agent should start from `## Next Tasks`, `## Launch Readiness Remaining Tasks`, and `## Launch Artifact Inventory`.",
            "- Preserve commit identity: `JunWeiLi233 <mcpejunwei@gmail.com>`.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
