from pathlib import Path
from datetime import datetime
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
    assert datetime.fromisoformat(payload.pop("checked_at"))
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
        "next_actions": [],
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


def test_launch_readiness_cli_updates_tasks_handoff_with_remaining_launch_work(
    tmp_path: Path, monkeypatch
):
    def fake_evaluate_launch_readiness():
        return LaunchReadinessReport(
            status="blocked",
            checks=[
                LaunchReadinessCheck(
                    id="imported_voices",
                    label="Imported voices",
                    passed=False,
                    detail="0 imported voices",
                ),
                LaunchReadinessCheck(
                    id="qwen_verification",
                    label="Qwen verification",
                    passed=False,
                    detail="No passed Qwen runtime verification report.",
                ),
            ],
            blocking_reasons=[
                "Import at least two consented voice profiles.",
                "Run Qwen runtime verification successfully before launch.",
            ],
        )

    monkeypatch.setattr("app.cli.launch_readiness.evaluate_launch_readiness", fake_evaluate_launch_readiness)
    tasks_path = tmp_path / "TASKS.md"
    tasks_path.write_text("# TASKS\n\nExisting handoff notes.\n", encoding="utf-8")

    exit_code = main(["--report", str(tmp_path / "launch-readiness.json"), "--tasks", str(tasks_path)])

    assert exit_code == 1
    content = tasks_path.read_text(encoding="utf-8")
    assert "## Launch Readiness Remaining Tasks" in content
    assert "- [ ] imported_voices: Import two consented WAV voice samples with matching transcripts." in content
    assert "Evidence: 0 imported voices" in content
    assert "- [ ] qwen_verification: Run Qwen verification with two imported voices and keep the passed report." in content
    assert "Evidence: No passed Qwen runtime verification report." in content
