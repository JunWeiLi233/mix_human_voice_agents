from __future__ import annotations

import json
from pathlib import Path

from app.core.storage import list_blends, list_generation_results, list_voice_profiles
from app.models.schemas import (
    AgentProviderVerificationReport,
    GenerationResult,
    LaunchReadinessCheck,
    LaunchReadinessReport,
    QwenVerificationReport,
    TtsRuntimeStatus,
)
from app.tts.qwen import QwenTtsAdapter


QWEN_VERIFICATION_REPORT_PATH = Path("data") / "qwen-runtime-verification-report.json"
AGENT_PROVIDER_VERIFICATION_REPORT_PATH = Path("data") / "agent-provider-verification-report.json"
RESEARCH_REVIEW_PATH = Path("docs") / "research-review.md"


def get_qwen_verification_report() -> QwenVerificationReport:
    report_path = QWEN_VERIFICATION_REPORT_PATH
    if not report_path.exists():
        return QwenVerificationReport(
            status="missing",
            report_path=str(report_path),
            error="Run python -m app.cli.verify_qwen_runtime with two consented voice profile ids.",
        )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload.setdefault("report_path", str(report_path))
    return QwenVerificationReport.model_validate(payload)


def get_agent_provider_verification_report() -> AgentProviderVerificationReport:
    report_path = AGENT_PROVIDER_VERIFICATION_REPORT_PATH
    if not report_path.exists():
        return AgentProviderVerificationReport(
            status="missing",
            report_path=str(report_path),
            error="Run the Agent Provider Test provider preflight before launch.",
        )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload.setdefault("report_path", str(report_path))
    return AgentProviderVerificationReport.model_validate(payload)


def evaluate_launch_readiness() -> LaunchReadinessReport:
    voices = list_voice_profiles()
    blends = list_blends()
    generations = list_generation_results()
    qwen_status = TtsRuntimeStatus.model_validate(QwenTtsAdapter.runtime_status())
    agent_provider_verification = get_agent_provider_verification_report()
    qwen_verification = get_qwen_verification_report()
    qwen_output_exists = bool(
        qwen_verification.output_audio_path
        and Path(qwen_verification.output_audio_path).exists()
    )
    qwen_verification_status = _qwen_verification_status(qwen_verification, qwen_output_exists)
    research_review = _research_review_status()
    qwen_generation = _qwen_mixed_generation_status(generations)

    checks = [
        LaunchReadinessCheck(
            id="research_review",
            label="Research review",
            passed=research_review["passed"],
            detail=research_review["detail"],
        ),
        LaunchReadinessCheck(
            id="imported_voices",
            label="Imported voices",
            passed=len(voices) >= 2,
            detail=f"{len(voices)} imported voices",
        ),
        LaunchReadinessCheck(
            id="saved_blend",
            label="Saved blend",
            passed=len(blends) >= 1,
            detail=f"{len(blends)} saved blends",
        ),
        LaunchReadinessCheck(
            id="generated_audio",
            label="Generated audio",
            passed=qwen_generation["passed"],
            detail=qwen_generation["detail"],
        ),
        LaunchReadinessCheck(
            id="agent_provider",
            label="Agent provider",
            passed=agent_provider_verification.status == "passed",
            detail=_agent_provider_verification_detail(agent_provider_verification),
        ),
        LaunchReadinessCheck(
            id="qwen_runtime",
            label="Qwen runtime",
            passed=qwen_status.available,
            detail=qwen_status.message,
        ),
        LaunchReadinessCheck(
            id="qwen_verification",
            label="Qwen verification",
            passed=qwen_verification_status["passed"],
            detail=qwen_verification_status["detail"],
        ),
    ]
    blocking_reasons = _launch_blocking_reasons(checks)
    return LaunchReadinessReport(
        status="ready" if not blocking_reasons else "blocked",
        checks=checks,
        blocking_reasons=blocking_reasons,
    )


def _agent_provider_verification_detail(report: AgentProviderVerificationReport) -> str:
    if report.status == "passed":
        return f"Provider verified: {report.provider} / {report.model}"
    if report.error:
        return report.error
    return "No passed agent provider verification report."


def _qwen_verification_detail(report: QwenVerificationReport, output_exists: bool) -> str:
    if report.status == "passed" and output_exists:
        return f"Verification passed: {report.output_audio_path}"
    if report.status == "passed":
        return "Verification report passed, but verified output audio is missing."
    if report.error:
        return report.error
    return "No passed Qwen runtime verification report."


def _qwen_verification_status(report: QwenVerificationReport, output_exists: bool) -> dict[str, object]:
    if report.status != "passed":
        return {
            "passed": False,
            "detail": _qwen_verification_detail(report, output_exists),
        }
    if not output_exists:
        return {
            "passed": False,
            "detail": _qwen_verification_detail(report, output_exists),
        }
    if len(report.source_profile_details) < 2:
        return {
            "passed": False,
            "detail": "Qwen verification report lacks imported source profile details.",
        }
    if not all(detail.reference_text_present for detail in report.source_profile_details):
        return {
            "passed": False,
            "detail": "Qwen verification report includes a source profile without reference text.",
        }
    return {
        "passed": True,
        "detail": _qwen_verification_detail(report, output_exists),
    }


def _research_review_status() -> dict[str, object]:
    review_path = _resolve_research_review_path()
    if not review_path.exists():
        return {
            "passed": False,
            "detail": f"Missing {RESEARCH_REVIEW_PATH}.",
        }

    content = review_path.read_text(encoding="utf-8")
    required_markers = ("Sources Reviewed", "Qwen3-TTS")
    missing_markers = [marker for marker in required_markers if marker not in content]
    if missing_markers:
        return {
            "passed": False,
            "detail": f"{RESEARCH_REVIEW_PATH} is missing required section markers: {', '.join(missing_markers)}.",
        }

    return {
        "passed": True,
        "detail": f"Reviewed: {RESEARCH_REVIEW_PATH}",
    }


def _resolve_research_review_path() -> Path:
    cwd_path = RESEARCH_REVIEW_PATH
    if cwd_path.exists():
        return cwd_path
    backend_parent_path = Path("..") / RESEARCH_REVIEW_PATH
    if Path.cwd().name == "backend" and backend_parent_path.exists():
        return backend_parent_path
    return cwd_path


def _qwen_mixed_generation_status(generations: list[GenerationResult]) -> dict[str, object]:
    for generation in generations:
        if generation.tts_backend != "qwen3_tts":
            continue
        if generation.blend_strategy != "multi_reference_prompt":
            continue
        if len(generation.source_profile_details) < 2:
            continue
        if not all(detail.reference_text_present for detail in generation.source_profile_details):
            continue
        if not Path(generation.audio_path).exists():
            continue
        return {
            "passed": True,
            "detail": f"Qwen mixed voice generated: {generation.id}",
        }

    qwen_count = sum(1 for generation in generations if generation.tts_backend == "qwen3_tts")
    return {
        "passed": False,
        "detail": f"{qwen_count} Qwen mixed voice clips with imported source details",
    }


def _launch_blocking_reasons(checks: list[LaunchReadinessCheck]) -> list[str]:
    reasons = {
        "research_review": "Review docs/research-review.md before launch.",
        "imported_voices": "Import at least two consented voice profiles.",
        "saved_blend": "Create and save a mixed voice blend.",
        "generated_audio": "Generate at least one Qwen3-TTS mixed voice clip from imported profiles.",
        "agent_provider": "Test the selected agent provider successfully before launch.",
        "qwen_runtime": "Install and load the Qwen3-TTS runtime before launch.",
        "qwen_verification": "Run Qwen runtime verification successfully before launch.",
    }
    return [reasons[check.id] for check in checks if not check.passed]
