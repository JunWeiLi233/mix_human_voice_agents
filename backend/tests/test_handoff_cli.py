from pathlib import Path

from app.cli.handoff import main, update_usage_limit_handoff


def test_handoff_cli_refreshes_tasks_for_usage_limit(tmp_path: Path, monkeypatch, capsys):
    calls: list[tuple[str, list[str]]] = []

    def fake_launch_artifacts_main(argv: list[str]) -> int:
        calls.append(("launch_artifacts", argv))
        tasks_path = Path(argv[argv.index("--tasks") + 1])
        tasks_path.write_text(
            "# TASKS\n\n"
            "## Launch Artifact Inventory\n\n"
            "- Voices: `0` total; `0` usable; `0` unusable\n",
            encoding="utf-8",
        )
        return 0

    def fake_launch_readiness_main(argv: list[str]) -> int:
        calls.append(("launch_readiness", argv))
        tasks_path = Path(argv[argv.index("--tasks") + 1])
        tasks_path.write_text(
            tasks_path.read_text(encoding="utf-8")
            + "\n## Launch Readiness Remaining Tasks\n\n"
            "- [ ] imported_voices: Import at least two clean consented WAV voices.\n",
            encoding="utf-8",
        )
        return 1

    monkeypatch.setattr("app.cli.handoff.launch_artifacts_main", fake_launch_artifacts_main)
    monkeypatch.setattr("app.cli.handoff.launch_readiness_main", fake_launch_readiness_main)
    tasks_path = tmp_path / "TASKS.md"

    exit_code = main(["--tasks", str(tasks_path)])

    assert exit_code == 0
    assert calls == [
        (
            "launch_artifacts",
            [
                "--report",
                "data/launch-artifacts-report.json",
                "--tasks",
                str(tasks_path),
                "--summary",
            ],
        ),
        (
            "launch_readiness",
            [
                "--report",
                "data/launch-readiness-report.json",
                "--tasks",
                str(tasks_path),
                "--summary",
            ],
        ),
    ]
    content = tasks_path.read_text(encoding="utf-8")
    assert "## Usage Limit Handoff" in content
    assert "- Last refreshed:" in content
    assert "- Reason: Codex usage/session/context limit handoff." in content
    assert "- Next agent should start from `## Next Tasks`, `## Launch Readiness Remaining Tasks`, and `## Launch Artifact Inventory`." in content
    assert "## Launch Artifact Inventory" in content
    assert "## Launch Readiness Remaining Tasks" in content
    output = capsys.readouterr().out
    assert "Usage-limit handoff written to" in output


def test_usage_limit_handoff_only_replaces_real_section_headings(tmp_path: Path):
    tasks_path = tmp_path / "TASKS.md"
    tasks_path.write_text(
        "# TASKS\n\n"
        "## Current State\n\n"
        "- Latest handoff work writes a `## Usage Limit Handoff` section.\n\n"
        "## Next Tasks\n\n"
        "1. Keep going.\n",
        encoding="utf-8",
    )

    update_usage_limit_handoff(tasks_path)

    content = tasks_path.read_text(encoding="utf-8")
    assert "- Latest handoff work writes a `## Usage Limit Handoff` section." in content
    assert content.count("\n## Usage Limit Handoff\n") == 1
    assert "## Next Tasks\n\n1. Keep going." in content


def test_usage_limit_handoff_preserves_next_heading_when_replacing_section(tmp_path: Path):
    tasks_path = tmp_path / "TASKS.md"
    tasks_path.write_text(
        "# TASKS\n\n"
        "## Usage Limit Handoff\n\n"
        "- Old stamp.\n\n"
        "## Launch Readiness Remaining Tasks\n\n"
        "- [ ] Keep going.\n",
        encoding="utf-8",
    )

    update_usage_limit_handoff(tasks_path)

    content = tasks_path.read_text(encoding="utf-8")
    assert "- Old stamp." not in content
    assert "## Launch Readiness Remaining Tasks\n\n- [ ] Keep going." in content
    assert "\n# Launch Readiness Remaining Tasks" not in content
