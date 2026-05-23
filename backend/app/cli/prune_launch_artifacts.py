from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.cli.launch_artifacts import _blend_status, _voice_status
from app.core.storage import BLEND_ROOT, ensure_storage, list_blends, list_voice_profiles


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prune stale launch artifacts that cannot satisfy mixed-voice launch readiness."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete stale blends. Without this flag the command only reports what would be deleted.",
    )
    parser.add_argument(
        "--report",
        default="data/prune-launch-artifacts-report.json",
        help="Path to write the JSON prune report.",
    )
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    report = collect_prune_plan(
        apply=args.apply,
        reviewed_apply_command=(
            None
            if args.apply
            else f"python -m app.cli.prune_launch_artifacts --apply --report {report_path}"
        ),
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _print_summary(report, report_path)
    return 0


def collect_prune_plan(*, apply: bool, reviewed_apply_command: str | None = None) -> dict[str, object]:
    ensure_storage()
    voices = list_voice_profiles()
    blends = list_blends()
    usable_voice_ids = [
        voice.id for voice in voices if _voice_status(voice)["launch_usable"]
    ]
    blend_statuses = [_blend_status(blend, usable_voice_ids, voices) for blend in blends]
    stale_blend_ids = [
        blend.id for blend, status in zip(blends, blend_statuses, strict=True) if not status["launch_eligible"]
    ]
    kept_blend_ids = [blend.id for blend in blends if blend.id not in set(stale_blend_ids)]
    deleted_blend_ids = _delete_blends(stale_blend_ids) if apply else []
    report: dict[str, object] = {
        "mode": "apply" if apply else "dry_run",
        "stale_blend_ids": stale_blend_ids,
        "stale_blends": [
            {
                "id": blend.id,
                "name": blend.name,
                "voice_profile_ids": [profile.voice_profile_id for profile in blend.profiles],
                "stale_reasons": status["stale_reasons"],
            }
            for blend, status in zip(blends, blend_statuses, strict=True)
            if not status["launch_eligible"]
        ],
        "deleted_blend_ids": deleted_blend_ids,
        "kept_blend_ids": kept_blend_ids,
    }
    if reviewed_apply_command is not None:
        report["reviewed_apply_command"] = reviewed_apply_command
    return report


def _delete_blends(blend_ids: list[str]) -> list[str]:
    deleted: list[str] = []
    blend_root = BLEND_ROOT.resolve()
    for blend_id in blend_ids:
        blend_path = (BLEND_ROOT / f"{blend_id}.json").resolve()
        if blend_root not in (blend_path, *blend_path.parents):
            continue
        if not blend_path.exists():
            continue
        blend_path.unlink()
        deleted.append(blend_id)
    return deleted


def _print_summary(report: dict[str, object], report_path: Path) -> None:
    stale_blend_ids = report["stale_blend_ids"]
    if report["mode"] == "apply":
        print(f"Deleted {len(report['deleted_blend_ids'])} stale blends.")
    else:
        print(f"Dry run: {len(stale_blend_ids)} stale blends would be deleted.")
        if report.get("reviewed_apply_command"):
            print(f"Review {report_path}, then run: {report['reviewed_apply_command']}")
    for blend_id in stale_blend_ids:
        print(f"- {blend_id}")


if __name__ == "__main__":
    raise SystemExit(main())
