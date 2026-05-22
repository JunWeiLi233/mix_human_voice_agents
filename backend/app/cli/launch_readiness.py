from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.api.routes import launch_readiness_route
from app.models.schemas import LaunchReadinessReport


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a local launch-readiness audit report.")
    parser.add_argument(
        "--report",
        default="data/launch-readiness-report.json",
        help="Path to write the JSON launch-readiness report.",
    )
    args = parser.parse_args(argv)

    report = evaluate_launch_readiness()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    return 0 if report.status == "ready" else 1


def evaluate_launch_readiness() -> LaunchReadinessReport:
    return launch_readiness_route()


if __name__ == "__main__":
    raise SystemExit(main())
