from fastapi.testclient import TestClient
from pathlib import Path
import json
import math
import struct
import wave

from app.main import app
from app.models.schemas import VoiceProfile

client = TestClient(app)


def test_health_route_returns_ok():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_qwen_status_route_reports_runtime_availability(monkeypatch):
    def fake_status():
        return {
            "backend": "qwen3_tts",
            "available": False,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts is not installed.",
        }

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.runtime_status", fake_status)

    response = client.get("/api/tts/qwen/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "qwen3_tts"
    assert payload["available"] is False
    assert payload["model_id"] == "Qwen/Qwen3-TTS-12Hz-0.6B-Base"


def test_qwen_verification_report_returns_missing_when_no_report(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.get("/api/tts/qwen/verification")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "missing"
    assert payload["tts_backend"] == "qwen3_tts"
    assert payload["report_path"] == str(Path("data") / "qwen-runtime-verification-report.json")


def test_qwen_verification_report_returns_saved_report(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "data" / "qwen-runtime-verification-report.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "voice_profile_ids": ["voice_a", "voice_b"],
                "tts_backend": "qwen3_tts",
                "blend_strategy": "multi_reference_prompt",
                "output_audio_path": "data/generations/qwen_verify.wav",
                "text": "verification text",
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/api/tts/qwen/verification")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "passed"
    assert payload["voice_profile_ids"] == ["voice_a", "voice_b"]
    assert payload["blend_strategy"] == "multi_reference_prompt"
    assert payload["output_audio_path"] == "data/generations/qwen_verify.wav"


def test_agent_provider_verification_report_returns_missing_when_no_report(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.get("/api/agent/provider-verification")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "missing"
    assert payload["report_path"] == str(Path("data") / "agent-provider-verification-report.json")


def test_agent_provider_verification_route_persists_passed_report(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_reply_record(prompt, config):
        return {
            "reply": f"Provider ready: {prompt}",
            "provider": config.provider,
            "model": config.model,
        }

    monkeypatch.setattr("app.api.routes.generate_agent_reply_record", fake_reply_record)

    response = client.post(
        "/api/agent/provider-verification",
        json={
            "prompt": "Reply with one short sentence confirming this provider is connected.",
            "config": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "base_url": "https://api.anthropic.com",
                "api_key": "sk-test",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "passed"
    assert payload["provider"] == "anthropic"
    assert payload["model"] == "claude-sonnet-4-5"
    assert payload["base_url"] == "https://api.anthropic.com"
    assert payload["reply"].startswith("Provider ready:")
    assert Path(payload["report_path"]).exists()

    saved_report = client.get("/api/agent/provider-verification").json()
    assert saved_report["status"] == "passed"
    assert saved_report["provider"] == "anthropic"
    assert saved_report["base_url"] == "https://api.anthropic.com"


def test_qwen_verification_route_runs_with_selected_imported_profiles(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    voices = []

    for name in ("Alice", "Bob"):
        with sample_path.open("rb") as sample:
            response = client.post(
                "/api/voices",
                data={
                    "speaker_display_name": name,
                    "consent_type": "self_or_written_permission",
                    "allowed_uses": "private_agent_voice,local_audio_export",
                    "confirmed_by": "local_user",
                    "notes": "approved for qwen verification",
                    "reference_text": f"{name} reads a clean reference sentence for Qwen cloning.",
                },
                files={"file": ("sample.wav", sample, "audio/wav")},
            )
        voices.append(response.json())

    class FakeQwenAdapter:
        seen_text = ""
        seen_profile_ids: list[str] = []
        seen_load_kwargs: dict[str, object] = {}

        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
            cls.seen_load_kwargs = kwargs
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            self.__class__.seen_text = text
            self.__class__.seen_profile_ids = sorted((voice_profiles or {}).keys())
            output = self.__class__.output_root / f"{blend.id}_qwen.wav"
            output.write_bytes(b"fake-qwen-wav")
            return output

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter", FakeQwenAdapter)

    response = client.post(
        "/api/tts/qwen/verification",
        json={
            "voice_profile_ids": [voices[0]["id"], voices[1]["id"]],
            "text": "This is a studio Qwen verification.",
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "device_map": "cuda:0",
            "dtype": "bfloat16",
            "attn_implementation": "flash_attention_2",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "passed"
    assert payload["voice_profile_ids"] == [voices[0]["id"], voices[1]["id"]]
    assert payload["blend_strategy"] == "multi_reference_prompt"
    assert payload["text"] == "This is a studio Qwen verification."
    assert payload["model_id"] == "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    assert payload["device_map"] == "cuda:0"
    assert payload["dtype"] == "bfloat16"
    assert payload["attn_implementation"] == "flash_attention_2"
    assert payload["source_profile_details"] == [
        {
            "voice_profile_id": voices[0]["id"],
            "display_name": "Alice",
            "weight": 0.5,
            "consent_confirmed_by": "local_user",
            "allowed_uses": ["private_agent_voice", "local_audio_export"],
            "reference_text_present": True,
        },
        {
            "voice_profile_id": voices[1]["id"],
            "display_name": "Bob",
            "weight": 0.5,
            "consent_confirmed_by": "local_user",
            "allowed_uses": ["private_agent_voice", "local_audio_export"],
            "reference_text_present": True,
        },
    ]
    assert Path(payload["output_audio_path"]).exists()
    assert FakeQwenAdapter.seen_text == "This is a studio Qwen verification."
    assert FakeQwenAdapter.seen_profile_ids == sorted([voices[0]["id"], voices[1]["id"]])
    assert FakeQwenAdapter.seen_load_kwargs == {
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "device_map": "cuda:0",
        "dtype": "bfloat16",
        "attn_implementation": "flash_attention_2",
    }

    saved_report = client.get("/api/tts/qwen/verification").json()
    assert saved_report["status"] == "passed"
    assert saved_report["output_audio_path"] == payload["output_audio_path"]
    assert saved_report["source_profile_details"] == payload["source_profile_details"]


def test_qwen_verification_route_requires_two_profiles(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.post(
        "/api/tts/qwen/verification",
        json={
            "voice_profile_ids": ["voice_a"],
            "text": "This is a studio Qwen verification.",
        },
    )

    assert response.status_code == 400
    assert "at least two" in response.json()["detail"]


def test_qwen_verification_route_requires_distinct_profiles(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.post(
        "/api/tts/qwen/verification",
        json={
            "voice_profile_ids": ["voice_a", "voice_a"],
            "text": "This is a studio Qwen verification.",
        },
    )

    assert response.status_code == 400
    assert "distinct" in response.json()["detail"]


def test_qwen_verification_route_rejects_quality_warnings_before_loading_runtime(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("quality warnings should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)
    monkeypatch.setattr(
        "app.api.routes.get_voice_profiles_by_ids",
        lambda profile_ids: {
            "voice_a": voice_profile(
                "voice_a",
                "Alice",
                quality_warnings=["Reference audio appears clipped; record a cleaner sample."],
            ),
            "voice_b": voice_profile("voice_b", "Bob"),
        },
    )

    response = client.post(
        "/api/tts/qwen/verification",
        json={
            "voice_profile_ids": ["voice_a", "voice_b"],
            "text": "This is a studio Qwen verification.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["error"] == "Voice profile voice_a must not have audio quality warnings for Qwen synthesis."


def test_launch_readiness_reports_blockers_when_requirements_are_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.get("/api/launch/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "Import at least two consented voice profiles." in payload["blocking_reasons"]
    assert "Review docs/research-review.md before launch." in payload["blocking_reasons"]
    assert "Test the selected agent provider successfully before launch." in payload["blocking_reasons"]
    assert "Run Qwen runtime verification successfully before launch." in payload["blocking_reasons"]
    assert {check["id"]: check["passed"] for check in payload["checks"]} == {
        "research_review": False,
        "imported_voices": False,
        "saved_blend": False,
        "generated_audio": False,
        "agent_provider": False,
        "qwen_runtime": False,
        "qwen_verification": False,
    }


def test_launch_readiness_reports_ready_after_full_qwen_verification(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- OpenAI Voice Agents\n"
        "- LiveKit Agents\n"
        "- Pipecat\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    voices = []

    for name in ("Alice", "Bob"):
        with sample_path.open("rb") as sample:
            response = client.post(
                "/api/voices",
                data={
                    "speaker_display_name": name,
                    "consent_type": "self_or_written_permission",
                    "allowed_uses": "private_agent_voice,local_audio_export",
                    "confirmed_by": "local_user",
                    "notes": "approved for launch readiness",
                    "reference_text": f"{name} reads a clean reference sentence for Qwen cloning.",
                },
                files={"file": ("sample.wav", sample, "audio/wav")},
            )
        voices.append(response.json())

    blend = client.post(
        "/api/blends",
        json={
            "name": "Launch Pair",
            "profiles": [
                {"voice_profile_id": voices[0]["id"], "weight": 1},
                {"voice_profile_id": voices[1]["id"], "weight": 1},
            ],
            "strategy": "multi_reference_prompt",
        },
    ).json()
    write_agent_provider_verification_report(base_url="https://api.openai.com/v1")
    write_qwen_runtime_verification_report([voices[0]["id"], voices[1]["id"]])

    class FakeQwenAdapter:
        name = "qwen3_tts"

        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            output = self.__class__.output_root / f"{blend.id}_qwen.wav"
            output.write_bytes(b"fake-qwen-wav")
            return output

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter", FakeQwenAdapter)
    generated = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a launch-ready mixed voice.",
            "blend": blend,
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "base_url": "https://api.openai.com/v1",
            },
        },
    ).json()
    report_path = tmp_path / "data" / "qwen-runtime-verification-report.json"
    verification_output_path = tmp_path / "data" / "generations" / "qwen_verify.wav"
    verification_output_path.write_bytes(b"fake-qwen-verification-wav")
    verification_output = str(Path("data") / "generations" / "qwen_verify.wav")
    report_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "voice_profile_ids": [voices[0]["id"], voices[1]["id"]],
                "source_profile_details": [
                    {
                        "voice_profile_id": voices[0]["id"],
                        "display_name": "Alice",
                        "weight": 0.5,
                        "consent_confirmed_by": "local_user",
                        "allowed_uses": ["private_agent_voice", "local_audio_export"],
                        "reference_text_present": True,
                    },
                    {
                        "voice_profile_id": voices[1]["id"],
                        "display_name": "Bob",
                        "weight": 0.5,
                        "consent_confirmed_by": "local_user",
                        "allowed_uses": ["private_agent_voice", "local_audio_export"],
                        "reference_text_present": True,
                    },
                ],
                "tts_backend": "qwen3_tts",
                "blend_strategy": "multi_reference_prompt",
                "output_audio_path": verification_output,
                "text": "Launch readiness verification.",
            }
        ),
        encoding="utf-8",
    )
    FakeQwenAdapter.runtime_status = staticmethod(
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        }
    )
    monkeypatch.setattr("app.core.launch.QwenTtsAdapter.runtime_status", FakeQwenAdapter.runtime_status)

    response = client.get("/api/launch/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["blocking_reasons"] == []
    assert all(check["passed"] for check in payload["checks"])


def test_launch_readiness_blocks_when_qwen_verification_lacks_source_details(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- OpenAI Voice Agents\n"
        "- LiveKit Agents\n"
        "- Pipecat\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    voices = []

    for name in ("Alice", "Bob"):
        with sample_path.open("rb") as sample:
            response = client.post(
                "/api/voices",
                data={
                    "speaker_display_name": name,
                    "consent_type": "self_or_written_permission",
                    "allowed_uses": "private_agent_voice,local_audio_export",
                    "confirmed_by": "local_user",
                    "notes": "approved for launch readiness",
                    "reference_text": f"{name} reads a clean reference sentence for Qwen cloning.",
                },
                files={"file": ("sample.wav", sample, "audio/wav")},
            )
        voices.append(response.json())

    blend = client.post(
        "/api/blends",
        json={
            "name": "Launch Pair",
            "profiles": [
                {"voice_profile_id": voices[0]["id"], "weight": 1},
                {"voice_profile_id": voices[1]["id"], "weight": 1},
            ],
            "strategy": "multi_reference_prompt",
        },
    ).json()
    write_agent_provider_verification_report()
    write_qwen_runtime_verification_report([voices[0]["id"], voices[1]["id"]])

    class FakeQwenAdapter:
        name = "qwen3_tts"

        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            output = self.__class__.output_root / f"{blend.id}_qwen.wav"
            output.write_bytes(b"fake-qwen-wav")
            return output

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter", FakeQwenAdapter)
    generated = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a launch-ready mixed voice.",
            "blend": blend,
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
        },
    ).json()
    report_path = tmp_path / "data" / "qwen-runtime-verification-report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "voice_profile_ids": [voices[0]["id"], voices[1]["id"]],
                "tts_backend": "qwen3_tts",
                "blend_strategy": "multi_reference_prompt",
                "output_audio_path": generated["audio_path"],
                "text": "Launch readiness verification.",
            }
        ),
        encoding="utf-8",
    )
    FakeQwenAdapter.runtime_status = staticmethod(
        lambda: {
            "backend": "qwen3_tts",
            "available": True,
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "message": "qwen-tts package is importable.",
        }
    )
    monkeypatch.setattr("app.core.launch.QwenTtsAdapter.runtime_status", FakeQwenAdapter.runtime_status)

    response = client.get("/api/launch/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "Run Qwen runtime verification successfully before launch." in payload["blocking_reasons"]
    assert {check["id"]: check["passed"] for check in payload["checks"]}["qwen_verification"] is False


def test_launch_readiness_blocks_when_only_local_preview_audio_exists(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    research_review_path = tmp_path / "docs" / "research-review.md"
    research_review_path.parent.mkdir(parents=True)
    research_review_path.write_text(
        "# Mixed Voice Agent Research Review\n\n"
        "## Sources Reviewed\n\n"
        "- OpenAI Voice Agents\n"
        "- LiveKit Agents\n"
        "- Pipecat\n"
        "- Qwen3-TTS\n",
        encoding="utf-8",
    )
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    voices = []

    for name in ("Alice", "Bob"):
        with sample_path.open("rb") as sample:
            response = client.post(
                "/api/voices",
                data={
                    "speaker_display_name": name,
                    "consent_type": "self_or_written_permission",
                    "allowed_uses": "private_agent_voice,local_audio_export",
                    "confirmed_by": "local_user",
                    "notes": "approved for launch readiness",
                    "reference_text": f"{name} reads a clean reference sentence for Qwen cloning.",
                },
                files={"file": ("sample.wav", sample, "audio/wav")},
            )
        voices.append(response.json())

    blend = client.post(
        "/api/blends",
        json={
            "name": "Local Only Pair",
            "profiles": [
                {"voice_profile_id": voices[0]["id"], "weight": 1},
                {"voice_profile_id": voices[1]["id"], "weight": 1},
            ],
            "strategy": "multi_reference_prompt",
        },
    ).json()
    generated = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a local preview mixed voice.",
            "blend": blend,
            "tts_backend": "local_development_wav",
        },
    ).json()
    provider_report_path = tmp_path / "data" / "agent-provider-verification-report.json"
    provider_report_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "reply": "Provider ready.",
                "report_path": str(Path("data") / "agent-provider-verification-report.json"),
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "data" / "qwen-runtime-verification-report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "voice_profile_ids": [voices[0]["id"], voices[1]["id"]],
                "source_profile_details": [
                    {
                        "voice_profile_id": voices[0]["id"],
                        "display_name": "Alice",
                        "weight": 0.5,
                        "consent_confirmed_by": "local_user",
                        "allowed_uses": ["private_agent_voice", "local_audio_export"],
                        "reference_text_present": True,
                    },
                    {
                        "voice_profile_id": voices[1]["id"],
                        "display_name": "Bob",
                        "weight": 0.5,
                        "consent_confirmed_by": "local_user",
                        "allowed_uses": ["private_agent_voice", "local_audio_export"],
                        "reference_text_present": True,
                    },
                ],
                "tts_backend": "qwen3_tts",
                "blend_strategy": "multi_reference_prompt",
                "output_audio_path": generated["audio_path"],
                "text": "Launch readiness verification.",
            }
        ),
        encoding="utf-8",
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

    response = client.get("/api/launch/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "Generate at least one Qwen3-TTS mixed voice clip from imported profiles." in payload["blocking_reasons"]
    assert {check["id"]: check["passed"] for check in payload["checks"]}["generated_audio"] is False


def test_create_blend_endpoint_normalizes_weights():
    response = client.post(
        "/api/blends",
        json={
            "name": "Pair",
            "profiles": [
                {"voice_profile_id": "voice_a", "weight": 2},
                {"voice_profile_id": "voice_b", "weight": 1},
            ],
            "strategy": "local_development_wav",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Pair"
    assert payload["profiles"][0]["weight"] > payload["profiles"][1]["weight"]
    assert payload["synthetic_label"] == "synthetic mixed voice"


def test_list_blends_returns_persisted_blends(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    created = client.post(
        "/api/blends",
        json={
            "name": "Persisted Pair",
            "profiles": [
                {"voice_profile_id": "voice_a", "weight": 2},
                {"voice_profile_id": "voice_b", "weight": 1},
            ],
            "strategy": "multi_reference_prompt",
        },
    ).json()

    response = client.get("/api/blends")

    assert response.status_code == 200
    payload = response.json()
    assert [blend["id"] for blend in payload] == [created["id"]]
    assert payload[0]["name"] == "Persisted Pair"
    assert payload[0]["strategy"] == "multi_reference_prompt"


def test_generate_endpoint_returns_audio_metadata(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    blend_response = client.post(
        "/api/blends",
        json={
            "name": "Pair",
            "profiles": [
                {"voice_profile_id": "voice_a", "weight": 1},
                {"voice_profile_id": "voice_b", "weight": 1},
            ],
            "strategy": "local_development_wav",
        },
    )
    blend = blend_response.json()

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "blend": blend,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert Path(payload["audio_path"]).exists()
    assert Path(payload["metadata_path"]).exists()
    assert payload["source_profile_ids"] == ["voice_a", "voice_b"]

    audio_response = client.get(f"/api/generations/{payload['id']}/audio")

    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"] == "audio/wav"
    assert audio_response.content.startswith(b"RIFF")

    metadata_response = client.get(f"/api/generations/{payload['id']}/metadata")

    assert metadata_response.status_code == 200
    assert metadata_response.headers["content-type"] == "application/json"
    assert metadata_response.json()["id"] == payload["id"]
    assert metadata_response.json()["synthetic_label"] == "synthetic mixed voice"
    assert metadata_response.json()["watermark"]["type"] == "metadata"
    assert "synthetic" in metadata_response.json()["watermark"]["disclosure"]
    assert metadata_response.json()["source_profiles"] == [
        {"voice_profile_id": "voice_a", "weight": 0.5},
        {"voice_profile_id": "voice_b", "weight": 0.5},
    ]


def test_generate_endpoint_records_imported_voice_details_for_local_preview(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    voices = []

    for name in ("Alice", "Bob"):
        with sample_path.open("rb") as sample:
            response = client.post(
                "/api/voices",
                data={
                    "speaker_display_name": name,
                    "consent_type": "self_or_written_permission",
                    "allowed_uses": "private_agent_voice,local_audio_export",
                    "confirmed_by": "Junwei",
                    "notes": "approved for local preview traceability",
                    "reference_text": f"{name} reads a clean reference sentence for Qwen cloning.",
                },
                files={"file": ("sample.wav", sample, "audio/wav")},
            )
        voices.append(response.json())

    blend = client.post(
        "/api/blends",
        json={
            "name": "Local Traceable Pair",
            "profiles": [
                {"voice_profile_id": voices[0]["id"], "weight": 3},
                {"voice_profile_id": voices[1]["id"], "weight": 1},
            ],
            "strategy": "local_development_wav",
        },
    ).json()

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a traceable local mixed voice.",
            "blend": blend,
            "tts_backend": "local_development_wav",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_profile_details"] == [
        {
            "voice_profile_id": voices[0]["id"],
            "display_name": "Alice",
            "weight": 0.75,
            "consent_confirmed_by": "Junwei",
            "allowed_uses": ["private_agent_voice", "local_audio_export"],
            "reference_text_present": True,
        },
        {
            "voice_profile_id": voices[1]["id"],
            "display_name": "Bob",
            "weight": 0.25,
            "consent_confirmed_by": "Junwei",
            "allowed_uses": ["private_agent_voice", "local_audio_export"],
            "reference_text_present": True,
        },
    ]

    metadata = client.get(f"/api/generations/{payload['id']}/metadata").json()
    assert metadata["source_profile_details"] == payload["source_profile_details"]


def test_generate_endpoint_rejects_duplicate_voice_profile_ids(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "blend": {
                "id": "blend_duplicate",
                "name": "Duplicate",
                "strategy": "local_development_wav",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert "distinct" in response.json()["detail"]


def test_generate_endpoint_rejects_duplicate_qwen_profiles_before_loading_runtime(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("duplicate profile ids should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)
    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", lambda profile_ids: {})

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "blend": {
                "id": "blend_duplicate",
                "name": "Duplicate",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert "distinct" in response.json()["detail"]


def test_generate_endpoint_rejects_qwen_without_agent_trace_before_loading_runtime(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("missing agent trace should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)
    monkeypatch.setattr(
        "app.api.routes.get_voice_profiles_by_ids",
        lambda profile_ids: {
            "voice_a": voice_profile("voice_a", "Alice"),
            "voice_b": voice_profile("voice_b", "Bob"),
        },
    )

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "blend": {
                "id": "blend_missing_trace",
                "name": "Missing trace",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Qwen generation requires an agent provider trace."


def test_generate_endpoint_rejects_qwen_without_provider_preflight_before_loading_runtime(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    def fail_if_profiles_load(profile_ids):
        raise AssertionError("missing provider preflight should be rejected before loading voice profiles")

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("missing provider preflight should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", fail_if_profiles_load)
    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_missing_provider_preflight",
                "name": "Missing provider preflight",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Agent provider preflight must pass before Qwen generation."


def test_generate_endpoint_rejects_qwen_agent_trace_that_differs_from_provider_preflight(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report(provider="anthropic", model="claude-sonnet-4-5")

    def fail_if_profiles_load(profile_ids):
        raise AssertionError("mismatched provider preflight should be rejected before loading voice profiles")

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("mismatched provider preflight should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", fail_if_profiles_load)
    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_mismatched_provider_preflight",
                "name": "Mismatched provider preflight",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Qwen generation agent trace must match the passed agent provider preflight."


def test_generate_endpoint_rejects_qwen_agent_trace_with_mismatched_provider_base_url(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report(
        provider="openai_compatible",
        model="custom-voice-agent-model",
        base_url="https://llm.example.test/v1",
    )

    def fail_if_profiles_load(profile_ids):
        raise AssertionError("mismatched provider endpoint should be rejected before loading voice profiles")

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("mismatched provider endpoint should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", fail_if_profiles_load)
    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai_compatible",
                "model": "custom-voice-agent-model",
                "base_url": "http://127.0.0.1:11434",
            },
            "blend": {
                "id": "blend_mismatched_provider_endpoint",
                "name": "Mismatched provider endpoint",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Qwen generation agent trace must match the passed agent provider preflight."


def test_generate_endpoint_rejects_qwen_without_runtime_verification_before_loading_profiles(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()

    def fail_if_profiles_load(profile_ids):
        raise AssertionError("missing Qwen verification should be rejected before loading voice profiles")

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("missing Qwen verification should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", fail_if_profiles_load)
    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_missing_qwen_verification",
                "name": "Missing Qwen verification",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Qwen runtime verification must pass before Qwen generation."


def test_generate_endpoint_rejects_qwen_with_mismatched_runtime_verification_voices(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()
    write_qwen_runtime_verification_report(["voice_a", "voice_c"])

    def fail_if_profiles_load(profile_ids):
        raise AssertionError("mismatched Qwen verification should be rejected before loading voice profiles")

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("mismatched Qwen verification should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", fail_if_profiles_load)
    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_mismatched_qwen_verification",
                "name": "Mismatched Qwen verification",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Qwen generation voices must match the passed Qwen runtime verification."


def test_generate_endpoint_rejects_qwen_with_mismatched_runtime_config_before_loading_profiles(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()
    write_qwen_runtime_verification_report(
        model_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        device_map="cuda:0",
        dtype="bfloat16",
        attn_implementation="flash_attention_2",
    )

    def fail_if_profiles_load(profile_ids):
        raise AssertionError("mismatched Qwen runtime config should be rejected before loading voice profiles")

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("mismatched Qwen runtime config should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", fail_if_profiles_load)
    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "device_map": "cuda:0",
            "dtype": "bfloat16",
            "attn_implementation": "flash_attention_2",
            "blend": {
                "id": "blend_mismatched_qwen_runtime",
                "name": "Mismatched Qwen runtime",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Qwen generation runtime config must match the passed Qwen verification."


def test_generate_endpoint_rejects_qwen_when_verification_output_is_missing_before_loading_profiles(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()
    write_qwen_runtime_verification_report(write_output=False)

    def fail_if_profiles_load(profile_ids):
        raise AssertionError("missing Qwen verification output should be rejected before loading voice profiles")

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("missing Qwen verification output should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", fail_if_profiles_load)
    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_missing_qwen_output",
                "name": "Missing Qwen output",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Qwen verification output audio must exist before Qwen generation."


def test_generate_endpoint_rejects_qwen_when_verification_output_is_empty_before_loading_profiles(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()
    write_qwen_runtime_verification_report(output_bytes=b"")

    def fail_if_profiles_load(profile_ids):
        raise AssertionError("empty Qwen verification output should be rejected before loading voice profiles")

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("empty Qwen verification output should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.get_voice_profiles_by_ids", fail_if_profiles_load)
    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_empty_qwen_output",
                "name": "Empty Qwen output",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Qwen verification output audio must be non-empty."


def test_generate_endpoint_rejects_qwen_profile_without_private_voice_consent_before_loading_runtime(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()
    write_qwen_runtime_verification_report()

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("revoked voice consent should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)
    monkeypatch.setattr(
        "app.api.routes.get_voice_profiles_by_ids",
        lambda profile_ids: {
            "voice_a": voice_profile("voice_a", "Alice", synthetic_voice_allowed=False),
            "voice_b": voice_profile("voice_b", "Bob"),
        },
    )

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_revoked",
                "name": "Revoked consent",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Voice profile voice_a is not allowed for private agent voice use."


def test_generate_endpoint_rejects_qwen_profile_without_reference_text_before_loading_runtime(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()
    write_qwen_runtime_verification_report()

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("missing reference text should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)
    monkeypatch.setattr(
        "app.api.routes.get_voice_profiles_by_ids",
        lambda profile_ids: {
            "voice_a": voice_profile("voice_a", "Alice", reference_text=""),
            "voice_b": voice_profile("voice_b", "Bob"),
        },
    )

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_missing_text",
                "name": "Missing text",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Voice profile voice_a must include reference text for Qwen synthesis."


def test_generate_endpoint_rejects_qwen_profile_with_quality_warnings_before_loading_runtime(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()
    write_qwen_runtime_verification_report()

    def fail_if_qwen_loads(**kwargs):
        raise AssertionError("quality warnings should be rejected before loading Qwen")

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter.from_pretrained", fail_if_qwen_loads)
    monkeypatch.setattr(
        "app.api.routes.get_voice_profiles_by_ids",
        lambda profile_ids: {
            "voice_a": voice_profile(
                "voice_a",
                "Alice",
                quality_warnings=["Reference audio appears clipped; record a cleaner sample."],
            ),
            "voice_b": voice_profile("voice_b", "Bob"),
        },
    )

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a synthetic mixed voice.",
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "blend": {
                "id": "blend_warning",
                "name": "Warning",
                "strategy": "multi_reference_prompt",
                "synthetic_label": "synthetic mixed voice",
                "profiles": [
                    {"voice_profile_id": "voice_a", "weight": 0.5},
                    {"voice_profile_id": "voice_b", "weight": 0.5},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Voice profile voice_a must not have audio quality warnings for Qwen synthesis."


def test_list_generations_returns_persisted_metadata(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    blend_response = client.post(
        "/api/blends",
        json={
            "name": "Pair",
            "profiles": [
                {"voice_profile_id": "voice_a", "weight": 1},
                {"voice_profile_id": "voice_b", "weight": 1},
            ],
            "strategy": "local_development_wav",
        },
    )
    generated = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a persisted synthetic mixed voice.",
            "blend": blend_response.json(),
        },
    ).json()

    response = client.get("/api/generations")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [generated["id"]]
    assert payload[0]["source_profile_ids"] == ["voice_a", "voice_b"]


def test_generation_audio_endpoint_returns_not_found(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.get("/api/generations/missing/audio")

    assert response.status_code == 404


def test_generation_metadata_endpoint_returns_not_found(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.get("/api/generations/missing/metadata")

    assert response.status_code == 404


def test_generate_endpoint_can_use_qwen_with_imported_profiles(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_agent_provider_verification_report()
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    voices = []

    for name in ("Alice", "Bob"):
        with sample_path.open("rb") as sample:
            response = client.post(
                "/api/voices",
                data={
                    "speaker_display_name": name,
                    "consent_type": "self_or_written_permission",
                    "allowed_uses": "private_agent_voice,local_audio_export",
                    "confirmed_by": "local_user",
                    "notes": "approved for qwen test",
                    "reference_text": f"{name} reads a clean reference sentence for Qwen cloning.",
                },
                files={"file": ("sample.wav", sample, "audio/wav")},
            )
        voices.append(response.json())
    write_qwen_runtime_verification_report([voices[0]["id"], voices[1]["id"]])

    class FakeQwenAdapter:
        name = "qwen3_tts"
        seen_profile_ids: list[str] = []
        seen_load_kwargs: dict[str, object] = {}

        @classmethod
        def from_pretrained(cls, output_root=None, **kwargs):
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
            cls.seen_load_kwargs = kwargs
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            self.__class__.seen_profile_ids = sorted((voice_profiles or {}).keys())
            output = self.__class__.output_root / f"{blend.id}_qwen.wav"
            output.write_bytes(b"fake-qwen-wav")
            return output

    monkeypatch.setattr("app.api.routes.QwenTtsAdapter", FakeQwenAdapter)
    blend_response = client.post(
        "/api/blends",
        json={
            "name": "Imported Qwen Pair",
            "profiles": [
                {"voice_profile_id": voices[0]["id"], "weight": 1},
                {"voice_profile_id": voices[1]["id"], "weight": 1},
            ],
            "strategy": "multi_reference_prompt",
        },
    )

    response = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from a qwen mixed voice.",
            "blend": blend_response.json(),
            "tts_backend": "qwen3_tts",
            "agent_trace": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
            },
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "device_map": "cuda:0",
            "dtype": "bfloat16",
            "attn_implementation": "flash_attention_2",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tts_backend"] == "qwen3_tts"
    assert payload["qwen_runtime_config"] == {
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "device_map": "cuda:0",
        "dtype": "bfloat16",
        "attn_implementation": "flash_attention_2",
    }
    assert Path(payload["audio_path"]).exists()
    assert FakeQwenAdapter.seen_profile_ids == sorted([voices[0]["id"], voices[1]["id"]])
    assert FakeQwenAdapter.seen_load_kwargs == {
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "device_map": "cuda:0",
        "dtype": "bfloat16",
        "attn_implementation": "flash_attention_2",
    }


def test_agent_reply_route_accepts_local_llm_config(monkeypatch):
    def fake_reply_record(prompt, config):
        return {
            "reply": f"Local reply to: {prompt}",
            "provider": config.provider,
            "model": config.model,
        }

    monkeypatch.setattr("app.api.routes.generate_agent_reply_record", fake_reply_record)

    response = client.post(
        "/api/agent/reply",
        json={
            "prompt": "Introduce the synthetic mixed voice.",
            "config": {
                "provider": "ollama",
                "model": "llama3.1",
                "base_url": "http://127.0.0.1:11434",
                "api_key": "",
                "system_prompt": "You are a disclosed synthetic mixed-voice assistant.",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Local reply to: Introduce the synthetic mixed voice."
    assert response.json()["provider"] == "ollama"


def test_import_voice_requires_consent_fields(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)

    with sample_path.open("rb") as sample:
        response = client.post(
            "/api/voices",
            data={
                "speaker_display_name": "Alice",
                "consent_type": "self_or_written_permission",
                "allowed_uses": "private_agent_voice,local_audio_export",
                "confirmed_by": "local_user",
                "notes": "approved for local prototype",
                "reference_text": "This is Alice reading a consented reference sample.",
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_name"] == "Alice"
    assert payload["reference_text"] == "This is Alice reading a consented reference sample."
    assert payload["consent"]["synthetic_voice_allowed"] is True
    assert Path(payload["source_audio_path"]).exists()
    assert payload["quality"]["duration_seconds"] == 5
    assert payload["quality"]["sample_rate_hz"] == 16000
    assert payload["quality"]["channel_count"] == 1


def test_import_voice_requires_reference_text(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)

    with sample_path.open("rb") as sample:
        response = client.post(
            "/api/voices",
            data={
                "speaker_display_name": "Alice",
                "consent_type": "self_or_written_permission",
                "allowed_uses": "private_agent_voice,local_audio_export",
                "confirmed_by": "local_user",
                "notes": "approved for local prototype",
                "reference_text": "   ",
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    assert response.status_code == 400
    assert "reference transcript" in response.json()["detail"]


def test_import_voice_rejects_invalid_wav(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    sample_path.write_bytes(b"not a real wav")

    with sample_path.open("rb") as sample:
        response = client.post(
            "/api/voices",
            data={
                "speaker_display_name": "Alice",
                "consent_type": "self_or_written_permission",
                "allowed_uses": "private_agent_voice,local_audio_export",
                "confirmed_by": "local_user",
                "notes": "approved for local prototype",
                "reference_text": "Alice reads a clean reference sentence for Qwen cloning.",
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    assert response.status_code == 400
    assert "WAV header" in response.json()["detail"]


def test_import_voice_rejects_silent_wav(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_silent_wav(sample_path)

    with sample_path.open("rb") as sample:
        response = client.post(
            "/api/voices",
            data={
                "speaker_display_name": "Alice",
                "consent_type": "self_or_written_permission",
                "allowed_uses": "private_agent_voice,local_audio_export",
                "confirmed_by": "local_user",
                "notes": "approved for local prototype",
                "reference_text": "Alice reads a clean reference sentence for Qwen cloning.",
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    assert response.status_code == 400
    assert "silence" in response.json()["detail"]


def test_import_voice_records_clipping_warning(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_clipped_wav(sample_path)

    with sample_path.open("rb") as sample:
        response = client.post(
            "/api/voices",
            data={
                "speaker_display_name": "Alice",
                "consent_type": "self_or_written_permission",
                "allowed_uses": "private_agent_voice,local_audio_export",
                "confirmed_by": "local_user",
                "notes": "approved for local prototype",
                "reference_text": "Alice reads a clean reference sentence for Qwen cloning.",
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    assert response.status_code == 200
    assert response.json()["quality"]["warnings"] == ["Reference audio appears clipped; record a cleaner sample."]


def test_import_voice_blocks_public_figure_label(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)

    with sample_path.open("rb") as sample:
        response = client.post(
            "/api/voices",
            data={
                "speaker_display_name": "Famous politician voice",
                "consent_type": "self_or_written_permission",
                "allowed_uses": "private_agent_voice,local_audio_export",
                "confirmed_by": "local_user",
                "notes": "approved for local prototype",
                "reference_text": "Famous politician reads a clean reference sentence for Qwen cloning.",
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    assert response.status_code == 400
    assert "public figure" in response.json()["detail"]


def test_list_voices_returns_imported_profiles(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)

    with sample_path.open("rb") as sample:
        import_response = client.post(
            "/api/voices",
            data={
                "speaker_display_name": "Alice",
                "consent_type": "self_or_written_permission",
                "allowed_uses": "private_agent_voice,local_audio_export",
                "confirmed_by": "local_user",
                "notes": "approved for local prototype",
                "reference_text": "Alice reads a clean reference sentence for Qwen cloning.",
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    response = client.get("/api/voices")

    assert response.status_code == 200
    payload = response.json()
    assert [voice["id"] for voice in payload] == [import_response.json()["id"]]
    assert payload[0]["display_name"] == "Alice"


def test_voice_audio_endpoint_returns_imported_source_sample(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)

    with sample_path.open("rb") as sample:
        import_response = client.post(
            "/api/voices",
            data={
                "speaker_display_name": "Alice",
                "consent_type": "self_or_written_permission",
                "allowed_uses": "private_agent_voice,local_audio_export",
                "confirmed_by": "local_user",
                "notes": "approved for local prototype",
                "reference_text": "Alice reads a clean reference sentence for Qwen cloning.",
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    response = client.get(f"/api/voices/{import_response.json()['id']}/audio")

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content.startswith(b"RIFF")


def test_voice_audio_endpoint_returns_not_found_for_missing_profile(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response = client.get("/api/voices/voice_missing/audio")

    assert response.status_code == 404


def test_delete_voice_removes_profile_and_dependent_blends(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    imported = []

    for name in ("Alice", "Bob", "Cara"):
        with sample_path.open("rb") as sample:
            response = client.post(
                "/api/voices",
                data={
                    "speaker_display_name": name,
                    "consent_type": "self_or_written_permission",
                    "allowed_uses": "private_agent_voice,local_audio_export",
                    "confirmed_by": "local_user",
                    "notes": "approved for local prototype",
                    "reference_text": f"{name} reads a clean reference sentence for Qwen cloning.",
                },
                files={"file": ("sample.wav", sample, "audio/wav")},
            )
        imported.append(response.json())

    removed_voice_id = imported[0]["id"]
    dependent_blend = client.post(
        "/api/blends",
        json={
            "name": "Alice + Bob",
            "profiles": [
                {"voice_profile_id": imported[0]["id"], "weight": 1},
                {"voice_profile_id": imported[1]["id"], "weight": 1},
            ],
            "strategy": "local_development_wav",
        },
    ).json()
    unrelated_blend = client.post(
        "/api/blends",
        json={
            "name": "Bob + Cara",
            "profiles": [
                {"voice_profile_id": imported[1]["id"], "weight": 1},
                {"voice_profile_id": imported[2]["id"], "weight": 1},
            ],
            "strategy": "local_development_wav",
        },
    ).json()

    dependent_generation = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from Alice and Bob.",
            "blend": dependent_blend,
        },
    ).json()
    unrelated_generation = client.post(
        "/api/generate",
        json={
            "prompt": "Say hello as a disclosed synthetic assistant.",
            "agent_reply": "Hello from Bob and Cara.",
            "blend": unrelated_blend,
        },
    ).json()

    response = client.delete(f"/api/voices/{removed_voice_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "deleted_voice_profile_id": removed_voice_id,
        "deleted_blend_ids": [dependent_blend["id"]],
        "deleted_generation_ids": [dependent_generation["id"]],
    }
    assert not Path(imported[0]["source_audio_path"]).parent.exists()
    assert not Path(dependent_generation["audio_path"]).exists()
    assert not Path(dependent_generation["metadata_path"]).exists()
    assert Path(unrelated_generation["audio_path"]).exists()
    assert Path(unrelated_generation["metadata_path"]).exists()
    remaining_voice_ids = {voice["id"] for voice in client.get("/api/voices").json()}
    assert remaining_voice_ids == {imported[1]["id"], imported[2]["id"]}
    assert [blend["id"] for blend in client.get("/api/blends").json()] == [unrelated_blend["id"]]
    assert [generation["id"] for generation in client.get("/api/generations").json()] == [unrelated_generation["id"]]


def write_agent_provider_verification_report(
    provider: str = "openai",
    model: str = "gpt-4.1-mini",
    base_url: str | None = None,
) -> None:
    report_path = Path("data") / "agent-provider-verification-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "provider": provider,
                "model": model,
                "base_url": base_url,
                "reply": "Provider ready.",
                "report_path": str(report_path),
            }
        ),
        encoding="utf-8",
    )


def write_qwen_runtime_verification_report(
    voice_profile_ids: list[str] | None = None,
    model_id: str | None = None,
    device_map: str | None = None,
    dtype: str | None = None,
    attn_implementation: str | None = None,
    write_output: bool = True,
    output_bytes: bytes = b"fake-qwen-verification-wav",
) -> None:
    resolved_voice_profile_ids = voice_profile_ids or ["voice_a", "voice_b"]
    output_path = Path("data") / "generations" / "qwen_verify.wav"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if write_output:
        output_path.write_bytes(output_bytes)
    report_path = Path("data") / "qwen-runtime-verification-report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "tts_backend": "qwen3_tts",
                "report_path": str(report_path),
                "voice_profile_ids": resolved_voice_profile_ids,
                "model_id": model_id,
                "device_map": device_map,
                "dtype": dtype,
                "attn_implementation": attn_implementation,
                "output_audio_path": str(output_path),
            }
        ),
        encoding="utf-8",
    )


def write_reference_wav(path: Path, duration_seconds: int = 5, sample_rate: int = 16000) -> None:
    frames = build_tone_frames(duration_seconds, sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)


def write_silent_wav(path: Path, duration_seconds: int = 5, sample_rate: int = 16000) -> None:
    frames = b"\x00\x00" * sample_rate * duration_seconds
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)


def write_clipped_wav(path: Path, duration_seconds: int = 5, sample_rate: int = 16000) -> None:
    frames = b"".join(struct.pack("<h", 32767) for _ in range(sample_rate * duration_seconds))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)


def voice_profile(
    profile_id: str,
    display_name: str,
    synthetic_voice_allowed: bool = True,
    reference_text: str | None = None,
    quality_warnings: list[str] | None = None,
) -> VoiceProfile:
    resolved_reference_text = (
        f"{display_name} reads a clean reference sentence." if reference_text is None else reference_text
    )
    resolved_quality_warnings = [] if quality_warnings is None else quality_warnings
    return VoiceProfile.model_validate(
        {
            "id": profile_id,
            "display_name": display_name,
            "reference_text": resolved_reference_text,
            "consent": {
                "voice_profile_id": profile_id,
                "speaker_display_name": display_name,
                "consent_type": "self_or_written_permission",
                "allowed_uses": ["private_agent_voice", "local_audio_export"],
                "confirmed_by": "local_user",
                "notes": "Written permission captured.",
                "synthetic_voice_allowed": synthetic_voice_allowed,
            },
            "source_audio_path": f"data/voices/{profile_id}/source.wav",
            "cleaned_audio_path": f"data/voices/{profile_id}/source.wav",
            "quality": {
                "file_name": "source.wav",
                "size_bytes": 10,
                "format": "wav",
                "duration_seconds": 5,
                "sample_rate_hz": 16000,
                "channel_count": 1,
                "warnings": resolved_quality_warnings,
            },
        }
    )


def build_tone_frames(duration_seconds: int, sample_rate: int) -> bytes:
    samples = sample_rate * duration_seconds
    return b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * index / sample_rate)))
        for index in range(samples)
    )
