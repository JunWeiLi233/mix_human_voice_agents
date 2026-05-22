from fastapi.testclient import TestClient
from pathlib import Path
import wave

from app.main import app

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


def test_generate_endpoint_can_use_qwen_with_imported_profiles(tmp_path: Path, monkeypatch):
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
                    "notes": "approved for qwen test",
                },
                files={"file": ("sample.wav", sample, "audio/wav")},
            )
        voices.append(response.json())

    class FakeQwenAdapter:
        name = "qwen3_tts"
        seen_profile_ids: list[str] = []

        @classmethod
        def from_pretrained(cls, output_root=None):
            cls.output_root = Path(output_root)
            cls.output_root.mkdir(parents=True, exist_ok=True)
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
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tts_backend"] == "qwen3_tts"
    assert Path(payload["audio_path"]).exists()
    assert FakeQwenAdapter.seen_profile_ids == sorted([voices[0]["id"], voices[1]["id"]])


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
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_name"] == "Alice"
    assert payload["consent"]["synthetic_voice_allowed"] is True
    assert Path(payload["source_audio_path"]).exists()
    assert payload["quality"]["duration_seconds"] == 5


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
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    assert response.status_code == 400
    assert "WAV header" in response.json()["detail"]


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
            },
            files={"file": ("sample.wav", sample, "audio/wav")},
        )

    response = client.get("/api/voices")

    assert response.status_code == 200
    payload = response.json()
    assert [voice["id"] for voice in payload] == [import_response.json()["id"]]
    assert payload[0]["display_name"] == "Alice"


def write_reference_wav(path: Path, duration_seconds: int = 5, sample_rate: int = 16000) -> None:
    frames = b"\x00\x00" * sample_rate * duration_seconds
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
