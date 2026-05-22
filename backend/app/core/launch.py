from __future__ import annotations

import json
from pathlib import Path

from app.core.generation import METADATA_WATERMARK_DISCLOSURE
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
REQUIRED_VOICE_USE = "private_agent_voice"
REQUIRED_SYNTHETIC_LABEL = "synthetic mixed voice"


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
    qwen_runtime = _qwen_runtime_status(qwen_status, qwen_verification)
    imported_voices = _imported_voices_status(voices, qwen_verification)
    saved_blend = _saved_blend_status(blends, qwen_verification)
    research_review = _research_review_status()
    qwen_generation = _qwen_mixed_generation_status(
        generations,
        agent_provider_verification,
        qwen_verification,
    )
    agent_provider = _agent_provider_verification_status(agent_provider_verification)

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
            passed=imported_voices["passed"],
            detail=imported_voices["detail"],
        ),
        LaunchReadinessCheck(
            id="saved_blend",
            label="Saved blend",
            passed=saved_blend["passed"],
            detail=saved_blend["detail"],
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
            passed=agent_provider["passed"],
            detail=agent_provider["detail"],
        ),
        LaunchReadinessCheck(
            id="qwen_runtime",
            label="Qwen runtime",
            passed=qwen_runtime["passed"],
            detail=qwen_runtime["detail"],
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


def _agent_provider_verification_status(report: AgentProviderVerificationReport) -> dict[str, object]:
    if report.status != "passed":
        return {
            "passed": False,
            "detail": _agent_provider_verification_detail(report),
        }
    if not report.provider or not report.model or not (report.reply or "").strip():
        return {
            "passed": False,
            "detail": "Agent provider verification report is missing provider, model, or reply.",
        }
    return {
        "passed": True,
        "detail": _agent_provider_verification_detail(report),
    }


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
    if report.tts_backend != "qwen3_tts":
        return {
            "passed": False,
            "detail": "Qwen verification report was not produced by the Qwen3-TTS backend.",
        }
    if len(set(report.voice_profile_ids)) < 2:
        return {
            "passed": False,
            "detail": "Qwen verification requires at least two distinct imported voice ids.",
        }
    if report.blend_strategy != "multi_reference_prompt":
        return {
            "passed": False,
            "detail": "Qwen verification report did not use the multi-reference mixed voice strategy.",
        }
    if len(report.source_profile_details) < 2:
        return {
            "passed": False,
            "detail": "Qwen verification report lacks imported source profile details.",
        }
    if sorted(detail.voice_profile_id for detail in report.source_profile_details) != sorted(report.voice_profile_ids):
        return {
            "passed": False,
            "detail": "Qwen verification source details do not match each verified voice id exactly once.",
        }
    if not all(detail.reference_text_present for detail in report.source_profile_details):
        return {
            "passed": False,
            "detail": "Qwen verification report includes a source profile without reference text.",
        }
    if not _details_allow_private_agent_voice(report.source_profile_details):
        return {
            "passed": False,
            "detail": "Qwen verification report includes a source profile not allowed for private agent voice use.",
        }
    return {
        "passed": True,
        "detail": _qwen_verification_detail(report, output_exists),
    }


def _qwen_runtime_status(status: TtsRuntimeStatus, verification: QwenVerificationReport) -> dict[str, object]:
    if not status.available:
        return {
            "passed": False,
            "detail": status.message,
        }
    if verification.status == "passed" and verification.model_id and status.model_id != verification.model_id:
        return {
            "passed": False,
            "detail": (
                f"Loaded Qwen model {status.model_id} does not match verified model "
                f"{verification.model_id}."
            ),
        }
    return {
        "passed": True,
        "detail": status.message,
    }


def _saved_blend_status(blends: list[object], verification: QwenVerificationReport) -> dict[str, object]:
    if not blends:
        return {
            "passed": False,
            "detail": "0 saved blends",
        }
    if verification.status != "passed" or not verification.voice_profile_ids:
        return {
            "passed": True,
            "detail": f"{len(blends)} saved blends",
        }

    verified_ids = sorted(verification.voice_profile_ids)
    for blend in blends:
        if not hasattr(blend, "profiles") or not hasattr(blend, "strategy"):
            continue
        if blend.strategy != "multi_reference_prompt":
            continue
        if sorted(profile.voice_profile_id for profile in blend.profiles) == verified_ids:
            return {
                "passed": True,
                "detail": f"Saved Qwen blend matches verified voices: {blend.id}",
            }

    return {
        "passed": False,
        "detail": "No saved multi-reference blend matches each verified Qwen voice id exactly once.",
    }


def _imported_voices_status(voices: list[object], verification: QwenVerificationReport) -> dict[str, object]:
    if len(voices) < 2:
        return {
            "passed": False,
            "detail": f"{len(voices)} imported voices",
        }
    if verification.status != "passed" or not verification.voice_profile_ids:
        return {
            "passed": True,
            "detail": f"{len(voices)} imported voices",
        }

    imported_by_id = {voice.id: voice for voice in voices if hasattr(voice, "id")}
    if not set(verification.voice_profile_ids).issubset(imported_by_id):
        return {
            "passed": False,
            "detail": "Imported voices do not include all verified Qwen voice ids.",
        }
    if not all(_voice_allows_private_agent_voice(imported_by_id[voice_id]) for voice_id in verification.voice_profile_ids):
        return {
            "passed": False,
            "detail": "Imported verified voices must still allow private agent voice use.",
        }
    if not all(_voice_has_reference_text(imported_by_id[voice_id]) for voice_id in verification.voice_profile_ids):
        return {
            "passed": False,
            "detail": "Imported verified voices must still include reference transcripts.",
        }
    if not all(_voice_has_reference_audio(imported_by_id[voice_id]) for voice_id in verification.voice_profile_ids):
        return {
            "passed": False,
            "detail": "Imported verified voices must still have reference audio files.",
        }
    if not all(_voice_has_clean_quality(imported_by_id[voice_id]) for voice_id in verification.voice_profile_ids):
        return {
            "passed": False,
            "detail": "Imported verified voices must not have audio quality warnings.",
        }
    return {
        "passed": True,
        "detail": f"{len(voices)} imported voices",
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


def _qwen_mixed_generation_status(
    generations: list[GenerationResult],
    agent_provider_verification: AgentProviderVerificationReport,
    qwen_verification: QwenVerificationReport,
) -> dict[str, object]:
    for generation in generations:
        if generation.tts_backend != "qwen3_tts":
            continue
        if generation.blend_strategy != "multi_reference_prompt":
            continue
        if len(generation.source_profile_details) < 2:
            continue
        if sorted(detail.voice_profile_id for detail in generation.source_profile_details) != sorted(
            generation.source_profile_ids
        ):
            return {
                "passed": False,
                "detail": "Qwen mixed voice source details do not match each generated source id exactly once.",
            }
        if (
            qwen_verification.status == "passed"
            and sorted(generation.source_profile_ids) != sorted(qwen_verification.voice_profile_ids)
        ):
            return {
                "passed": False,
                "detail": "Qwen mixed voice generation does not match each verified Qwen voice id exactly once.",
            }
        if (
            qwen_verification.status == "passed"
            and _qwen_verification_runtime_config(qwen_verification)
            and generation.qwen_runtime_config != _qwen_verification_runtime_config(qwen_verification)
        ):
            return {
                "passed": False,
                "detail": "Qwen mixed voice generation runtime config does not match verification.",
            }
        if not all(detail.reference_text_present for detail in generation.source_profile_details):
            continue
        if not _details_allow_private_agent_voice(generation.source_profile_details):
            return {
                "passed": False,
                "detail": "Qwen mixed voice clips include a source profile not allowed for private agent voice use.",
            }
        if generation.agent_trace is None:
            return {
                "passed": False,
                "detail": "Qwen mixed voice clips must include an agent provider trace.",
            }
        if (
            agent_provider_verification.status == "passed"
            and (
                generation.agent_trace.provider != agent_provider_verification.provider
                or generation.agent_trace.model != agent_provider_verification.model
            )
        ):
            return {
                "passed": False,
                "detail": (
                    "Qwen mixed voice clip uses "
                    f"{generation.agent_trace.provider} / {generation.agent_trace.model}, "
                    "but verified provider is "
                    f"{agent_provider_verification.provider} / {agent_provider_verification.model}."
                ),
            }
        if (
            qwen_verification.status == "passed"
            and qwen_verification.output_audio_path
            and _same_audio_path(generation.audio_path, qwen_verification.output_audio_path)
        ):
            return {
                "passed": False,
                "detail": "Qwen verification output and generated mixed voice audio must be separate files.",
            }
        if not generation.prompt.strip() or not generation.agent_reply.strip():
            return {
                "passed": False,
                "detail": "Qwen mixed voice clips must include the agent prompt and spoken reply transcript.",
            }
        if not _generation_has_synthetic_disclosure(generation):
            return {
                "passed": False,
                "detail": "Qwen mixed voice clips must include synthetic disclosure metadata.",
            }
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


def _qwen_verification_runtime_config(report: QwenVerificationReport) -> dict[str, str | None]:
    return {
        key: value
        for key, value in {
            "model_id": report.model_id,
            "device_map": report.device_map,
            "dtype": report.dtype,
            "attn_implementation": report.attn_implementation,
        }.items()
        if value is not None
    }


def _same_audio_path(left: str, right: str) -> bool:
    return Path(left).resolve(strict=False) == Path(right).resolve(strict=False)


def _details_allow_private_agent_voice(details: list[object]) -> bool:
    return all(REQUIRED_VOICE_USE in detail.allowed_uses for detail in details)


def _generation_has_synthetic_disclosure(generation: GenerationResult) -> bool:
    return (
        generation.synthetic_label == REQUIRED_SYNTHETIC_LABEL
        and generation.watermark.label == REQUIRED_SYNTHETIC_LABEL
        and generation.watermark.disclosure == METADATA_WATERMARK_DISCLOSURE
    )


def _voice_allows_private_agent_voice(voice: object) -> bool:
    consent = getattr(voice, "consent", None)
    if consent is None:
        return False
    if not getattr(consent, "synthetic_voice_allowed", False):
        return False
    return REQUIRED_VOICE_USE in getattr(consent, "allowed_uses", [])


def _voice_has_reference_text(voice: object) -> bool:
    return bool(getattr(voice, "reference_text", "").strip())


def _voice_has_reference_audio(voice: object) -> bool:
    cleaned_audio_path = getattr(voice, "cleaned_audio_path", "")
    return bool(cleaned_audio_path) and Path(cleaned_audio_path).exists()


def _voice_has_clean_quality(voice: object) -> bool:
    quality = getattr(voice, "quality", None)
    if quality is None:
        return True
    return not getattr(quality, "warnings", [])


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
