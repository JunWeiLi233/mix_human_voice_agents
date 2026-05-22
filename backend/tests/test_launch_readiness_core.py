from app.core.launch import evaluate_launch_readiness
from app.models.schemas import AgentTrace, GenerationResult, SourceProfileDetail


def test_core_launch_readiness_evaluator_reports_missing_requirements(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    report = evaluate_launch_readiness()

    assert report.status == "blocked"
    assert "Import at least two consented voice profiles." in report.blocking_reasons
    assert "Run Qwen runtime verification successfully before launch." in report.blocking_reasons


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
