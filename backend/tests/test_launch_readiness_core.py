from types import SimpleNamespace

from app.core.launch import _qwen_mixed_generation_status, _qwen_verification_status, evaluate_launch_readiness
from app.models.schemas import (
    AgentProviderVerificationReport,
    AgentTrace,
    BlendProfile,
    GenerationResult,
    MetadataWatermark,
    QwenVerificationReport,
    SourceProfileDetail,
    VoiceBlend,
)


def test_core_launch_readiness_evaluator_reports_missing_requirements(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    assert "Import at least two consented voice profiles." in report.blocking_reasons
    assert "Run Qwen runtime verification successfully before launch." in report.blocking_reasons


def test_core_launch_readiness_blocks_passed_agent_provider_report_without_provider_details(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )

    report = evaluate_launch_readiness()

    agent_provider_check = next(check for check in report.checks if check.id == "agent_provider")
    assert agent_provider_check.passed is False
    assert agent_provider_check.detail == "Agent provider verification report is missing provider, model, or reply."


def test_core_launch_readiness_blocks_passed_qwen_verification_without_text(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    output_path.parent.mkdir(parents=True)
    output_path.write_bytes(b"fake-qwen-wav")
    report = QwenVerificationReport(
        status="passed",
        report_path="data/qwen-runtime-verification-report.json",
        voice_profile_ids=["voice_a", "voice_b"],
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        source_profile_details=[
            SourceProfileDetail(
                voice_profile_id="voice_a",
                display_name="Alice",
                weight=0.5,
                consent_confirmed_by="local_user",
                allowed_uses=["private_agent_voice", "local_audio_export"],
                reference_text_present=True,
            ),
            SourceProfileDetail(
                voice_profile_id="voice_b",
                display_name="Bob",
                weight=0.5,
                consent_confirmed_by="local_user",
                allowed_uses=["private_agent_voice", "local_audio_export"],
                reference_text_present=True,
            ),
        ],
        output_audio_path=str(output_path),
        text="   ",
    )

    status = _qwen_verification_status(report, output_exists=True)

    assert status == {
        "passed": False,
        "detail": "Qwen verification report must include the synthesized verification text.",
    }


def test_core_launch_readiness_blocks_passed_qwen_verification_output_outside_generation_storage(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    output_path = tmp_path / "qwen_verify.wav"
    output_path.write_bytes(b"fake-qwen-wav")
    report = QwenVerificationReport(
        status="passed",
        report_path="data/qwen-runtime-verification-report.json",
        voice_profile_ids=["voice_a", "voice_b"],
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        source_profile_details=[
            SourceProfileDetail(
                voice_profile_id="voice_a",
                display_name="Alice",
                weight=0.5,
                consent_confirmed_by="local_user",
                allowed_uses=["private_agent_voice", "local_audio_export"],
                reference_text_present=True,
            ),
            SourceProfileDetail(
                voice_profile_id="voice_b",
                display_name="Bob",
                weight=0.5,
                consent_confirmed_by="local_user",
                allowed_uses=["private_agent_voice", "local_audio_export"],
                reference_text_present=True,
            ),
        ],
        output_audio_path=str(output_path),
        text="This is a disclosed synthetic mixed voice runtime verification.",
    )

    status = _qwen_verification_status(report, output_exists=True)

    assert status == {
        "passed": False,
        "detail": "Qwen verification output must be stored under data/generations.",
    }


def test_core_launch_readiness_blocks_qwen_generation_without_synthetic_disclosure_metadata(tmp_path):
    audio_path = tmp_path / "mixed.wav"
    audio_path.write_bytes(b"fake-qwen-wav")
    generation = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(tmp_path / "mixed.json"),
        prompt="Say hello as a disclosed synthetic assistant.",
        agent_reply="Hello from a launch-ready mixed voice.",
        synthetic_label="natural voice",
        source_profile_ids=["voice_a", "voice_b"],
        source_profile_details=[
            SourceProfileDetail(
                voice_profile_id="voice_a",
                display_name="Alice",
                weight=0.5,
                consent_confirmed_by="local_user",
                allowed_uses=["private_agent_voice", "local_audio_export"],
                reference_text_present=True,
            ),
            SourceProfileDetail(
                voice_profile_id="voice_b",
                display_name="Bob",
                weight=0.5,
                consent_confirmed_by="local_user",
                allowed_uses=["private_agent_voice", "local_audio_export"],
                reference_text_present=True,
            ),
        ],
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
        watermark=MetadataWatermark(label="natural voice", disclosure=""),
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )
    provider_report = AgentProviderVerificationReport(
        status="passed",
        provider="openai",
        model="gpt-4.1-mini",
        reply="Provider ready.",
        report_path="data/agent-provider-verification-report.json",
    )
    qwen_report = QwenVerificationReport(
        status="passed",
        report_path="data/qwen-runtime-verification-report.json",
        voice_profile_ids=["voice_a", "voice_b"],
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        output_audio_path=str(tmp_path / "qwen_verify.wav"),
    )

    status = _qwen_mixed_generation_status([generation], provider_report, qwen_report)

    assert status == {
        "passed": False,
        "detail": "Qwen mixed voice clips must include synthetic disclosure metadata.",
    }


def test_core_launch_readiness_blocks_qwen_generation_audio_outside_generation_storage(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "mixed.wav"
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.parent.mkdir(parents=True)
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    generation = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
        prompt="Say hello as a disclosed synthetic assistant.",
        agent_reply="Hello from a launch-ready mixed voice.",
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        source_profile_details=source_details,
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )
    provider_report = AgentProviderVerificationReport(
        status="passed",
        provider="openai",
        model="gpt-4.1-mini",
        reply="Provider ready.",
        report_path="data/agent-provider-verification-report.json",
    )
    qwen_report = QwenVerificationReport(
        status="passed",
        report_path="data/qwen-runtime-verification-report.json",
        voice_profile_ids=["voice_a", "voice_b"],
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        source_profile_details=source_details,
        output_audio_path=str(verification_path),
        text="This is a disclosed synthetic mixed voice runtime verification.",
    )

    status = _qwen_mixed_generation_status([generation], provider_report, qwen_report)

    assert status == {
        "passed": False,
        "detail": "Qwen mixed voice audio must be stored under data/generations.",
    }


def test_core_launch_readiness_blocks_qwen_generation_metadata_outside_generation_storage(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    metadata_path = tmp_path / "mixed.json"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    metadata_path.write_text("{}", encoding="utf-8")
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    generation = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        prompt="Say hello as a disclosed synthetic assistant.",
        agent_reply="Hello from a launch-ready mixed voice.",
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        source_profile_details=source_details,
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )
    provider_report = AgentProviderVerificationReport(
        status="passed",
        provider="openai",
        model="gpt-4.1-mini",
        reply="Provider ready.",
        report_path="data/agent-provider-verification-report.json",
    )
    qwen_report = QwenVerificationReport(
        status="passed",
        report_path="data/qwen-runtime-verification-report.json",
        voice_profile_ids=["voice_a", "voice_b"],
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        source_profile_details=source_details,
        output_audio_path=str(verification_path),
        text="This is a disclosed synthetic mixed voice runtime verification.",
    )

    status = _qwen_mixed_generation_status([generation], provider_report, qwen_report)

    assert status == {
        "passed": False,
        "detail": "Qwen mixed voice metadata must be stored under data/generations.",
    }


def test_core_launch_readiness_blocks_qwen_generation_with_missing_metadata_artifact(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    metadata_path = tmp_path / "data" / "generations" / "mixed.json"
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    generation = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        prompt="Say hello as a disclosed synthetic assistant.",
        agent_reply="Hello from a launch-ready mixed voice.",
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        source_profile_details=source_details,
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )
    provider_report = AgentProviderVerificationReport(
        status="passed",
        provider="openai",
        model="gpt-4.1-mini",
        reply="Provider ready.",
        report_path="data/agent-provider-verification-report.json",
    )
    qwen_report = QwenVerificationReport(
        status="passed",
        report_path="data/qwen-runtime-verification-report.json",
        voice_profile_ids=["voice_a", "voice_b"],
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        source_profile_details=source_details,
        output_audio_path=str(verification_path),
        text="This is a disclosed synthetic mixed voice runtime verification.",
    )

    status = _qwen_mixed_generation_status([generation], provider_report, qwen_report)

    assert status == {
        "passed": False,
        "detail": "Qwen mixed voice metadata is missing.",
    }


def test_core_launch_readiness_blocks_qwen_generation_with_mismatched_metadata_artifact(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    metadata_path = tmp_path / "data" / "generations" / "mixed.json"
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    generation = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        prompt="Say hello as a disclosed synthetic assistant.",
        agent_reply="Hello from a launch-ready mixed voice.",
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        source_profile_details=source_details,
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )
    metadata_path.write_text(
        '{"id": "generation_other", "audio_path": "data/generations/other.wav"}',
        encoding="utf-8",
    )
    provider_report = AgentProviderVerificationReport(
        status="passed",
        provider="openai",
        model="gpt-4.1-mini",
        reply="Provider ready.",
        report_path="data/agent-provider-verification-report.json",
    )
    qwen_report = QwenVerificationReport(
        status="passed",
        report_path="data/qwen-runtime-verification-report.json",
        voice_profile_ids=["voice_a", "voice_b"],
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        source_profile_details=source_details,
        output_audio_path=str(verification_path),
        text="This is a disclosed synthetic mixed voice runtime verification.",
    )

    status = _qwen_mixed_generation_status([generation], provider_report, qwen_report)

    assert status == {
        "passed": False,
        "detail": "Qwen mixed voice metadata does not match generated audio.",
    }


def test_core_launch_readiness_blocks_qwen_generation_with_invalid_metadata_artifact(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    metadata_path = tmp_path / "data" / "generations" / "mixed.json"
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    metadata_path.write_text("{invalid-json", encoding="utf-8")
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    generation = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        prompt="Say hello as a disclosed synthetic assistant.",
        agent_reply="Hello from a launch-ready mixed voice.",
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        source_profile_details=source_details,
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
        agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
    )
    provider_report = AgentProviderVerificationReport(
        status="passed",
        provider="openai",
        model="gpt-4.1-mini",
        reply="Provider ready.",
        report_path="data/agent-provider-verification-report.json",
    )
    qwen_report = QwenVerificationReport(
        status="passed",
        report_path="data/qwen-runtime-verification-report.json",
        voice_profile_ids=["voice_a", "voice_b"],
        tts_backend="qwen3_tts",
        blend_strategy="multi_reference_prompt",
        source_profile_details=source_details,
        output_audio_path=str(verification_path),
        text="This is a disclosed synthetic mixed voice runtime verification.",
    )

    status = _qwen_mixed_generation_status([generation], provider_report, qwen_report)

    assert status == {
        "passed": False,
        "detail": "Qwen mixed voice metadata is invalid.",
    }


def test_core_launch_readiness_blocks_when_generation_trace_differs_from_verified_provider(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="anthropic", model="claude-sonnet-4-5"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == "Qwen mixed voice clip uses anthropic / claude-sonnet-4-5, but verified provider is openai / gpt-4.1-mini."


def test_core_launch_readiness_blocks_when_qwen_verification_uses_wrong_backend(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "local_development_wav",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    qwen_verification_check = next(check for check in report.checks if check.id == "qwen_verification")
    assert qwen_verification_check.passed is False
    assert qwen_verification_check.detail == "Qwen verification report was not produced by the Qwen3-TTS backend."


def test_core_launch_readiness_blocks_when_qwen_verification_uses_wrong_strategy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "local_development_wav",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    qwen_verification_check = next(check for check in report.checks if check.id == "qwen_verification")
    assert qwen_verification_check.passed is False
    assert qwen_verification_check.detail == "Qwen verification report did not use the multi-reference mixed voice strategy."


def test_core_launch_readiness_blocks_when_qwen_verification_reuses_one_voice_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    verification_path.parent.mkdir(parents=True)
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_a"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice duplicate",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [])
    monkeypatch.setattr("app.core.launch.list_generation_results", lambda: [])
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    qwen_verification_check = next(check for check in report.checks if check.id == "qwen_verification")
    assert qwen_verification_check.passed is False
    assert qwen_verification_check.detail == "Qwen verification requires at least two distinct imported voice ids."


def test_core_launch_readiness_blocks_when_qwen_verification_has_duplicate_source_details(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    verification_path.parent.mkdir(parents=True)
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice duplicate",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [])
    monkeypatch.setattr("app.core.launch.list_generation_results", lambda: [])
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    qwen_verification_check = next(check for check in report.checks if check.id == "qwen_verification")
    assert qwen_verification_check.passed is False
    assert qwen_verification_check.detail == "Qwen verification source details do not match each verified voice id exactly once."


def test_core_launch_readiness_blocks_when_qwen_source_details_do_not_match_verified_voice_ids(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_c",
              "display_name": "Cara",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    qwen_verification_check = next(check for check in report.checks if check.id == "qwen_verification")
    assert qwen_verification_check.passed is False
    assert qwen_verification_check.detail == (
        "Qwen verification source details do not match each verified voice id exactly once."
    )


def test_core_launch_readiness_blocks_when_qwen_generation_source_details_do_not_match_source_ids(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_c",
            display_name="Cara",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == (
        "Qwen mixed voice source details do not match each generated source id exactly once."
    )


def test_core_launch_readiness_blocks_when_qwen_generation_has_duplicate_source_details(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    generation_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice duplicate",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                prompt="Say hello as a disclosed synthetic assistant.",
                agent_reply="Hello from a launch-ready mixed voice.",
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=generation_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == (
        "Qwen mixed voice source details do not match each generated source id exactly once."
    )


def test_core_launch_readiness_blocks_when_qwen_generation_uses_unverified_voice_set(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_c",
            display_name="Cara",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_c"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == (
        "Qwen mixed voice generation does not match each verified Qwen voice id exactly once."
    )


def test_core_launch_readiness_blocks_when_qwen_generation_repeats_verified_voice_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    generation_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.4,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice duplicate",
            weight=0.1,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                prompt="Say hello as a disclosed synthetic assistant.",
                agent_reply="Hello from a launch-ready mixed voice.",
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_a", "voice_b"],
                source_profile_details=generation_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == (
        "Qwen mixed voice generation does not match each verified Qwen voice id exactly once."
    )


def test_core_launch_readiness_blocks_when_qwen_generation_runtime_differs_from_verification(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
          "device_map": "cuda:0",
          "dtype": "bfloat16",
          "attn_implementation": "flash_attention_2",
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                qwen_runtime_config={
                    "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                    "device_map": "cuda:0",
                    "dtype": "bfloat16",
                    "attn_implementation": "flash_attention_2",
                },
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == "Qwen mixed voice generation runtime config does not match verification."


def test_core_launch_readiness_blocks_when_loaded_qwen_model_differs_from_verification(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [object()])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                qwen_runtime_config={
                    "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                },
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    qwen_runtime_check = next(check for check in report.checks if check.id == "qwen_runtime")
    assert qwen_runtime_check.passed is False
    assert qwen_runtime_check.detail == (
        "Loaded Qwen model Qwen/Qwen3-TTS-12Hz-0.6B-Base does not match verified model "
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base."
    )


def test_core_launch_readiness_blocks_when_saved_blend_does_not_match_verified_qwen_voices(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    unrelated_blend = VoiceBlend(
        name="Unrelated blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_c", weight=0.5),
            BlendProfile(voice_profile_id="voice_d", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [unrelated_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    saved_blend_check = next(check for check in report.checks if check.id == "saved_blend")
    assert saved_blend_check.passed is False
    assert saved_blend_check.detail == (
        "No saved multi-reference blend matches each verified Qwen voice id exactly once."
    )


def test_core_launch_readiness_blocks_when_saved_blend_repeats_verified_qwen_voice(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    duplicate_blend = VoiceBlend(
        name="Duplicate voice blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.4),
            BlendProfile(voice_profile_id="voice_a", weight=0.1),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    monkeypatch.setattr("app.core.launch.list_voice_profiles", lambda: [object(), object()])
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [duplicate_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    saved_blend_check = next(check for check in report.checks if check.id == "saved_blend")
    assert saved_blend_check.passed is False
    assert saved_blend_check.detail == (
        "No saved multi-reference blend matches each verified Qwen voice id exactly once."
    )


def test_core_launch_readiness_blocks_when_imported_voices_do_not_include_verified_qwen_ids(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    matching_blend = VoiceBlend(
        name="Verified blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [SimpleNamespace(id="voice_c"), SimpleNamespace(id="voice_d")],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    imported_voices_check = next(check for check in report.checks if check.id == "imported_voices")
    assert imported_voices_check.passed is False
    assert imported_voices_check.detail == "Imported voices do not include all verified Qwen voice ids."


def test_core_launch_readiness_blocks_when_imported_verified_voice_consent_is_revoked(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    matching_blend = VoiceBlend(
        name="Verified blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [
            SimpleNamespace(
                id="voice_a",
                consent=SimpleNamespace(
                    allowed_uses=["private_agent_voice", "local_audio_export"],
                    synthetic_voice_allowed=False,
                ),
            ),
            SimpleNamespace(
                id="voice_b",
                consent=SimpleNamespace(
                    allowed_uses=["private_agent_voice", "local_audio_export"],
                    synthetic_voice_allowed=True,
                ),
            ),
        ],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                prompt="Say hello as a disclosed synthetic assistant.",
                agent_reply="Hello from a launch-ready mixed voice.",
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    imported_voices_check = next(check for check in report.checks if check.id == "imported_voices")
    assert imported_voices_check.passed is False
    assert imported_voices_check.detail == "Imported verified voices must still allow private agent voice use."


def test_core_launch_readiness_blocks_when_current_imported_voice_lacks_reference_text(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    matching_blend = VoiceBlend(
        name="Verified blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [
            SimpleNamespace(
                id="voice_a",
                reference_text="",
                consent=SimpleNamespace(
                    allowed_uses=["private_agent_voice", "local_audio_export"],
                    synthetic_voice_allowed=True,
                ),
            ),
            SimpleNamespace(
                id="voice_b",
                reference_text="Bob reads a clean reference sentence.",
                consent=SimpleNamespace(
                    allowed_uses=["private_agent_voice", "local_audio_export"],
                    synthetic_voice_allowed=True,
                ),
            ),
        ],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                prompt="Say hello as a disclosed synthetic assistant.",
                agent_reply="Hello from a launch-ready mixed voice.",
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    imported_voices_check = next(check for check in report.checks if check.id == "imported_voices")
    assert imported_voices_check.passed is False
    assert imported_voices_check.detail == "Imported verified voices must still include reference transcripts."


def test_core_launch_readiness_blocks_when_current_imported_voice_audio_is_missing(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    voice_b_audio = tmp_path / "data" / "voices" / "voice_b" / "source.wav"
    audio_path.parent.mkdir(parents=True)
    voice_b_audio.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    voice_b_audio.write_bytes(b"fake-voice-b-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    matching_blend = VoiceBlend(
        name="Verified blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [
            SimpleNamespace(
                id="voice_a",
                reference_text="Alice reads a clean reference sentence.",
                cleaned_audio_path=str(tmp_path / "data" / "voices" / "voice_a" / "source.wav"),
                consent=SimpleNamespace(
                    allowed_uses=["private_agent_voice", "local_audio_export"],
                    synthetic_voice_allowed=True,
                ),
            ),
            SimpleNamespace(
                id="voice_b",
                reference_text="Bob reads a clean reference sentence.",
                cleaned_audio_path=str(voice_b_audio),
                consent=SimpleNamespace(
                    allowed_uses=["private_agent_voice", "local_audio_export"],
                    synthetic_voice_allowed=True,
                ),
            ),
        ],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                prompt="Say hello as a disclosed synthetic assistant.",
                agent_reply="Hello from a launch-ready mixed voice.",
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    imported_voices_check = next(check for check in report.checks if check.id == "imported_voices")
    assert imported_voices_check.passed is False
    assert imported_voices_check.detail == "Imported verified voices must still have reference audio files."


def test_core_launch_readiness_blocks_when_current_imported_voice_has_quality_warnings(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    voice_a_audio = tmp_path / "data" / "voices" / "voice_a" / "source.wav"
    voice_b_audio = tmp_path / "data" / "voices" / "voice_b" / "source.wav"
    audio_path.parent.mkdir(parents=True)
    voice_a_audio.parent.mkdir(parents=True)
    voice_b_audio.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    voice_a_audio.write_bytes(b"fake-voice-a-wav")
    voice_b_audio.write_bytes(b"fake-voice-b-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    matching_blend = VoiceBlend(
        name="Verified blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [
            SimpleNamespace(
                id="voice_a",
                reference_text="Alice reads a clean reference sentence.",
                cleaned_audio_path=str(voice_a_audio),
                quality=SimpleNamespace(warnings=["Reference audio appears clipped; record a cleaner sample."]),
                consent=SimpleNamespace(
                    allowed_uses=["private_agent_voice", "local_audio_export"],
                    synthetic_voice_allowed=True,
                ),
            ),
            SimpleNamespace(
                id="voice_b",
                reference_text="Bob reads a clean reference sentence.",
                cleaned_audio_path=str(voice_b_audio),
                quality=SimpleNamespace(warnings=[]),
                consent=SimpleNamespace(
                    allowed_uses=["private_agent_voice", "local_audio_export"],
                    synthetic_voice_allowed=True,
                ),
            ),
        ],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                prompt="Say hello as a disclosed synthetic assistant.",
                agent_reply="Hello from a launch-ready mixed voice.",
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    imported_voices_check = next(check for check in report.checks if check.id == "imported_voices")
    assert imported_voices_check.passed is False
    assert imported_voices_check.detail == "Imported verified voices must not have audio quality warnings."


def test_core_launch_readiness_blocks_when_qwen_verification_reuses_generated_audio_path(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    matching_blend = VoiceBlend(
        id="blend_launch",
        name="Launch blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/mixed.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [SimpleNamespace(id="voice_a"), SimpleNamespace(id="voice_b")],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == "Qwen verification output and generated mixed voice audio must be separate files."


def test_core_launch_readiness_blocks_when_qwen_generation_lacks_agent_transcript(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    matching_blend = VoiceBlend(
        id="blend_launch",
        name="Launch blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [SimpleNamespace(id="voice_a"), SimpleNamespace(id="voice_b")],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == "Qwen mixed voice clips must include the agent prompt and spoken reply transcript."


def test_core_launch_readiness_blocks_when_qwen_verification_lacks_private_voice_use(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    source_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    matching_blend = VoiceBlend(
        id="blend_launch",
        name="Launch blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [SimpleNamespace(id="voice_a"), SimpleNamespace(id="voice_b")],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                prompt="Say hello as a disclosed synthetic assistant.",
                agent_reply="Hello from a launch-ready mixed voice.",
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=source_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    qwen_verification_check = next(check for check in report.checks if check.id == "qwen_verification")
    assert qwen_verification_check.passed is False
    assert qwen_verification_check.detail == "Qwen verification report includes a source profile not allowed for private agent voice use."


def test_core_launch_readiness_blocks_when_qwen_generation_lacks_private_voice_use(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    audio_path = tmp_path / "data" / "generations" / "mixed.wav"
    verification_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-qwen-wav")
    verification_path.write_bytes(b"fake-qwen-verification-wav")
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    verified_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
        SourceProfileDetail(
            voice_profile_id="voice_b",
            display_name="Bob",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            reference_text_present=True,
        ),
    ]
    generated_details = [
        SourceProfileDetail(
            voice_profile_id="voice_a",
            display_name="Alice",
            weight=0.5,
            consent_confirmed_by="local_user",
            allowed_uses=["local_audio_export"],
            reference_text_present=True,
        ),
        verified_details[1],
    ]
    matching_blend = VoiceBlend(
        id="blend_launch",
        name="Launch blend",
        profiles=[
            BlendProfile(voice_profile_id="voice_a", weight=0.5),
            BlendProfile(voice_profile_id="voice_b", weight=0.5),
        ],
        strategy="multi_reference_prompt",
    )
    (tmp_path / "data" / "agent-provider-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "provider": "openai",
          "model": "gpt-4.1-mini",
          "reply": "Provider ready.",
          "report_path": "data/agent-provider-verification-report.json"
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "data" / "qwen-runtime-verification-report.json").write_text(
        """
        {
          "status": "passed",
          "voice_profile_ids": ["voice_a", "voice_b"],
          "source_profile_details": [
            {
              "voice_profile_id": "voice_a",
              "display_name": "Alice",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            },
            {
              "voice_profile_id": "voice_b",
              "display_name": "Bob",
              "weight": 0.5,
              "consent_confirmed_by": "local_user",
              "allowed_uses": ["private_agent_voice", "local_audio_export"],
              "reference_text_present": true
            }
          ],
          "tts_backend": "qwen3_tts",
          "blend_strategy": "multi_reference_prompt",
          "output_audio_path": "data/generations/qwen_verify.wav",
          "text": "Launch readiness verification."
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.core.launch.list_voice_profiles",
        lambda: [SimpleNamespace(id="voice_a"), SimpleNamespace(id="voice_b")],
    )
    monkeypatch.setattr("app.core.launch.list_blends", lambda: [matching_blend])
    monkeypatch.setattr(
        "app.core.launch.list_generation_results",
        lambda: [
            GenerationResult(
                audio_path=str(audio_path),
                metadata_path=str(tmp_path / "data" / "generations" / "mixed.json"),
                prompt="Say hello as a disclosed synthetic assistant.",
                agent_reply="Hello from a launch-ready mixed voice.",
                synthetic_label="synthetic mixed voice",
                source_profile_ids=["voice_a", "voice_b"],
                source_profile_details=generated_details,
                blend_strategy="multi_reference_prompt",
                tts_backend="qwen3_tts",
                agent_trace=AgentTrace(provider="openai", model="gpt-4.1-mini"),
            )
        ],
    )
    monkeypatch.setattr(
        "app.core.launch.QwenTtsAdapter.runtime_status",
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        },
    )

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    generated_audio_check = next(check for check in report.checks if check.id == "generated_audio")
    assert generated_audio_check.passed is False
    assert generated_audio_check.detail == "Qwen mixed voice clips include a source profile not allowed for private agent voice use."
