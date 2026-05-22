from app.core.launch import evaluate_launch_readiness


def test_core_launch_readiness_evaluator_reports_missing_requirements(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    assert "Import at least two consented voice profiles." in report.blocking_reasons
    assert "Run Qwen runtime verification successfully before launch." in report.blocking_reasons
