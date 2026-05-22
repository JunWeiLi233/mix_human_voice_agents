from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app

client = TestClient(app)


def test_health_route_returns_ok():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
    sample_path.write_bytes(b"not a real wav but enough for storage")

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
