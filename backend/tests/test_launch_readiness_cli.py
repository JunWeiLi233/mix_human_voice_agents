from pathlib import Path
import json

from app.cli.launch_readiness import main
from app.models.schemas import LaunchReadinessCheck, LaunchReadinessReport


def test_launch_readiness_cli_writes_report(tmp_path: Path, monkeypatch):
    def fake_evaluate_launch_readiness():
        return LaunchReadinessReport(
            status="blocked",
            checks=[
                LaunchReadinessCheck(
                    id="qwen_verification",
                    label="Qwen verification",
                    passed=False,
                    detail="No passed Qwen runtime verification report.",
                )
            ],
            blocking_reasons=["Run Qwen runtime verification successfully before launch."],
        )

    monkeypatch.setattr("app.cli.launch_readiness.evaluate_launch_readiness", fake_evaluate_launch_readiness)
    report_path = tmp_path / "launch-readiness.json"

    exit_code = main(["--report", str(report_path)])

    assert exit_code == 1
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload == {
        "status": "blocked",
        "checks": [
            {
                "id": "qwen_verification",
                "label": "Qwen verification",
                "passed": False,
                "detail": "No passed Qwen runtime verification report.",
            }
        ],
        "blocking_reasons": ["Run Qwen runtime verification successfully before launch."],
    }


def test_launch_readiness_cli_returns_zero_when_ready(tmp_path: Path, monkeypatch):
    def fake_evaluate_launch_readiness():
        return LaunchReadinessReport(
            status="ready",
            checks=[
                LaunchReadinessCheck(
                    id="qwen_verification",
                    label="Qwen verification",
                    passed=True,
                    detail="Verification passed: data/generations/qwen_verify.wav",
                )
            ],
            blocking_reasons=[],
        )

    monkeypatch.setattr("app.cli.launch_readiness.evaluate_launch_readiness", fake_evaluate_launch_readiness)

    exit_code = main(["--report", str(tmp_path / "launch-readiness.json")])

    assert exit_code == 0
