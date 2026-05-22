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
