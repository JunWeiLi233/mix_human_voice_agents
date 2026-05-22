from types import SimpleNamespace

from app.core.launch import evaluate_launch_readiness
from app.models.schemas import AgentTrace, BlendProfile, GenerationResult, SourceProfileDetail, VoiceBlend


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
    assert qwen_verification_check.detail == "Qwen verification source details do not match the verified voice ids."


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
    assert generated_audio_check.detail == "Qwen mixed voice source details do not match generated source ids."


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
    assert generated_audio_check.detail == "Qwen mixed voice generation does not match the verified Qwen voice ids."


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
    assert saved_blend_check.detail == "No saved multi-reference blend matches verified Qwen voice ids."


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
