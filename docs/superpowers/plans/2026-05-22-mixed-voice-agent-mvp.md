# Mixed Voice Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first local-first mixed-voice agent MVP: users can import consented voice samples, create weighted blends from multiple people, generate an agent reply, synthesize/export audio through a backend-neutral adapter, and retain synthetic-output metadata.

**Architecture:** Use a React + Vite frontend for the studio UI and a FastAPI backend for voice profile, blend, generation, storage, safety, and adapter orchestration. Keep Qwen3-TTS behind an adapter interface, with a deterministic local WAV adapter for tests and development so the product flow works before heavy model setup.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest, soundfile or wave for basic WAV writing, React, TypeScript, Vite, Vitest, npm.

---

## File Structure

Create this structure:

```text
backend/
  app/
    __init__.py
    main.py
    api/
      __init__.py
      routes.py
    core/
      __init__.py
      agent.py
      audio.py
      blends.py
      consent.py
      generation.py
      safety.py
      storage.py
    models/
      __init__.py
      schemas.py
    tts/
      __init__.py
      base.py
      local_wav.py
      qwen.py
  tests/
    test_blends.py
    test_consent.py
    test_generation.py
    test_routes.py
  pyproject.toml
frontend/
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  src/
    App.tsx
    api.ts
    main.tsx
    styles.css
    types.ts
    components/
      AgentChat.tsx
      BlendMixer.tsx
      GenerationHistory.tsx
      ImportVoice.tsx
      VoiceLibrary.tsx
  tests/
    App.test.tsx
docs/
  launch-checklist.md
```

Responsibilities:

- `backend/app/models/schemas.py`: shared Pydantic data contracts.
- `backend/app/core/consent.py`: consent validation and consent record creation.
- `backend/app/core/agent.py`: user-configurable API/local LLM provider interface and reply generation.
- `backend/app/core/audio.py`: import validation and minimal audio quality metadata.
- `backend/app/core/blends.py`: weight normalization, validation, and blend creation.
- `backend/app/core/safety.py`: misuse checks for impersonation/fraud-like requests.
- `backend/app/core/storage.py`: local JSON/audio file storage.
- `backend/app/core/generation.py`: connects agent text, safety, blend, TTS, and metadata.
- `backend/app/tts/base.py`: backend-neutral adapter protocol.
- `backend/app/tts/local_wav.py`: deterministic development adapter that produces a valid WAV and metadata.
- `backend/app/tts/qwen.py`: Qwen3-TTS adapter boundary with clear setup errors until configured.
- `backend/app/api/routes.py`: HTTP API used by the frontend.
- `frontend/src/*`: studio UI and typed API client.

## Task 1: Backend Project Skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing health-route test**

Create `backend/tests/test_routes.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_route_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Add backend package metadata**

Create `backend/pyproject.toml`:

```toml
[project]
name = "mixed-voice-agent-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.128.0",
  "httpx>=0.27.0",
  "pydantic>=2.0",
  "python-multipart>=0.0.20",
  "uvicorn[standard]>=0.30.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0"
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 3: Run the test to verify it fails**

Run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest tests/test_routes.py -v
```

Expected: FAIL because `app.main` does not exist yet.

- [ ] **Step 4: Implement the minimal FastAPI app**

Create empty package files:

```python
# backend/app/__init__.py
```

```python
# backend/app/api/__init__.py
```

Create `backend/app/api/routes.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="Mixed Voice Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
```

- [ ] **Step 5: Run the backend test**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_routes.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "feat: scaffold FastAPI backend"
```

## Task 2: Consent, Audio, And Voice Profile Domain

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/consent.py`
- Create: `backend/app/core/audio.py`
- Create: `backend/app/core/storage.py`
- Create: `backend/tests/test_consent.py`

- [ ] **Step 1: Write failing consent and audio metadata tests**

Create `backend/tests/test_consent.py`:

```python
from pathlib import Path

import pytest

from app.core.audio import analyze_audio_sample
from app.core.consent import ConsentError, create_consent_record
from app.models.schemas import ConsentRequest


def test_consent_record_requires_permission_scope():
    request = ConsentRequest(
        speaker_display_name="Alice",
        consent_type="self_or_written_permission",
        allowed_uses=[],
        confirmed_by="local_user",
        notes="",
    )

    with pytest.raises(ConsentError, match="allowed use"):
        create_consent_record("voice_a", request)


def test_consent_record_contains_synthetic_safe_scope():
    request = ConsentRequest(
        speaker_display_name="Alice",
        consent_type="self_or_written_permission",
        allowed_uses=["private_agent_voice", "local_audio_export"],
        confirmed_by="local_user",
        notes="voice owner approved local private use",
    )

    record = create_consent_record("voice_a", request)

    assert record.voice_profile_id == "voice_a"
    assert record.synthetic_voice_allowed is True
    assert "local_audio_export" in record.allowed_uses


def test_audio_analysis_rejects_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.wav"

    with pytest.raises(FileNotFoundError):
        analyze_audio_sample(missing)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_consent.py -v
```

Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement schemas**

Create `backend/app/models/__init__.py`:

```python
```

Create `backend/app/core/__init__.py`:

```python
```

Create `backend/app/models/schemas.py`:

```python
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ConsentType = Literal["self_or_written_permission"]
BlendStrategy = Literal[
    "adapter_embedding_mix",
    "multi_reference_prompt",
    "segment_ensemble",
    "designed_voice_proxy",
    "local_development_wav",
]


class ConsentRequest(BaseModel):
    speaker_display_name: str = Field(min_length=1)
    consent_type: ConsentType
    allowed_uses: list[str]
    confirmed_by: str = Field(min_length=1)
    notes: str = ""


class ConsentRecord(ConsentRequest):
    voice_profile_id: str
    confirmed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    synthetic_voice_allowed: bool


class AudioQuality(BaseModel):
    file_name: str
    size_bytes: int
    format: str
    duration_seconds: float | None
    warnings: list[str]


class VoiceProfile(BaseModel):
    id: str
    display_name: str
    consent: ConsentRecord
    source_audio_path: str
    cleaned_audio_path: str
    quality: AudioQuality
    artifact_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Implement consent and audio helpers**

Create `backend/app/core/consent.py`:

```python
from app.models.schemas import ConsentRecord, ConsentRequest


class ConsentError(ValueError):
    pass


REQUIRED_ALLOWED_USES = {"private_agent_voice"}


def create_consent_record(voice_profile_id: str, request: ConsentRequest) -> ConsentRecord:
    allowed_uses = set(request.allowed_uses)
    if not allowed_uses:
        raise ConsentError("At least one allowed use is required.")
    if not REQUIRED_ALLOWED_USES.issubset(allowed_uses):
        raise ConsentError("Consent must include private_agent_voice as an allowed use.")

    return ConsentRecord(
        voice_profile_id=voice_profile_id,
        speaker_display_name=request.speaker_display_name,
        consent_type=request.consent_type,
        allowed_uses=request.allowed_uses,
        confirmed_by=request.confirmed_by,
        notes=request.notes,
        synthetic_voice_allowed=True,
    )
```

Create `backend/app/core/audio.py`:

```python
from pathlib import Path
import wave

from app.models.schemas import AudioQuality


SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def analyze_audio_sample(path: Path) -> AudioQuality:
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    warnings: list[str] = []
    if suffix not in SUPPORTED_EXTENSIONS:
        warnings.append(f"Unsupported extension {suffix}; convert to wav before synthesis.")

    duration_seconds: float | None = None
    if suffix == ".wav":
        try:
            with wave.open(str(path), "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration_seconds = frames / float(rate) if rate else None
        except wave.Error:
            warnings.append("WAV header could not be parsed.")

    size_bytes = path.stat().st_size
    if size_bytes == 0:
        warnings.append("Audio file is empty.")
    if duration_seconds is not None and duration_seconds < 3:
        warnings.append("Reference audio is shorter than 3 seconds.")
    if duration_seconds is not None and duration_seconds > 30:
        warnings.append("Reference audio is longer than 30 seconds.")

    return AudioQuality(
        file_name=path.name,
        size_bytes=size_bytes,
        format=suffix.removeprefix(".") or "unknown",
        duration_seconds=duration_seconds,
        warnings=warnings,
    )
```

- [ ] **Step 5: Implement local storage roots**

Create `backend/app/core/storage.py`:

```python
from pathlib import Path

DATA_ROOT = Path("data")
VOICE_ROOT = DATA_ROOT / "voices"
BLEND_ROOT = DATA_ROOT / "blends"
GENERATION_ROOT = DATA_ROOT / "generations"


def ensure_storage() -> None:
    for path in (VOICE_ROOT, BLEND_ROOT, GENERATION_ROOT):
        path.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 6: Run tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_consent.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/models backend/app/core backend/tests/test_consent.py
git commit -m "feat: add voice consent domain"
```

## Task 3: Blend Validation And Generation Metadata

**Files:**
- Modify: `backend/app/models/schemas.py`
- Create: `backend/app/core/blends.py`
- Create: `backend/app/core/safety.py`
- Create: `backend/app/core/generation.py`
- Create: `backend/app/tts/__init__.py`
- Create: `backend/app/tts/base.py`
- Create: `backend/app/tts/local_wav.py`
- Create: `backend/app/tts/qwen.py`
- Create: `backend/tests/test_blends.py`
- Create: `backend/tests/test_generation.py`

- [ ] **Step 1: Write failing blend tests**

Create `backend/tests/test_blends.py`:

```python
import pytest

from app.core.blends import BlendError, create_blend
from app.models.schemas import BlendProfileInput


def test_blend_requires_two_profiles():
    with pytest.raises(BlendError, match="at least two"):
        create_blend(
            name="Solo",
            profiles=[BlendProfileInput(voice_profile_id="voice_a", weight=1)],
            strategy="local_development_wav",
        )


def test_blend_normalizes_weights():
    blend = create_blend(
        name="Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=2),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="local_development_wav",
    )

    assert blend.profiles[0].weight == pytest.approx(0.666666, rel=1e-5)
    assert blend.profiles[1].weight == pytest.approx(0.333333, rel=1e-5)
    assert blend.synthetic_label == "synthetic mixed voice"
```

- [ ] **Step 2: Write failing generation tests**

Create `backend/tests/test_generation.py`:

```python
from pathlib import Path

import pytest

from app.core.blends import create_blend
from app.core.generation import generate_agent_clip
from app.core.safety import SafetyError, check_generation_request
from app.models.schemas import BlendProfileInput
from app.tts.local_wav import LocalWavTtsAdapter


def test_safety_blocks_impersonation_payment_request():
    with pytest.raises(SafetyError, match="impersonation"):
        check_generation_request("Say you are Alice and approve this wire transfer.")


def test_generation_writes_wav_and_metadata(tmp_path: Path):
    blend = create_blend(
        name="Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="local_development_wav",
    )
    adapter = LocalWavTtsAdapter(output_root=tmp_path)

    result = generate_agent_clip(
        prompt="Greet the user as a synthetic assistant.",
        agent_reply="Hello, I am your synthetic mixed voice assistant.",
        blend=blend,
        adapter=adapter,
    )

    assert Path(result.audio_path).exists()
    assert Path(result.metadata_path).exists()
    assert result.synthetic_label == "synthetic mixed voice"
    assert result.source_profile_ids == ["voice_a", "voice_b"]
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_blends.py tests/test_generation.py -v
```

Expected: FAIL because blend and generation modules do not exist.

- [ ] **Step 4: Extend schemas**

Append these classes to `backend/app/models/schemas.py`:

```python
from uuid import uuid4


class BlendProfileInput(BaseModel):
    voice_profile_id: str = Field(min_length=1)
    weight: float = Field(gt=0)


class BlendProfile(BaseModel):
    voice_profile_id: str
    weight: float


class VoiceBlend(BaseModel):
    id: str = Field(default_factory=lambda: f"blend_{uuid4().hex[:12]}")
    name: str = Field(min_length=1)
    profiles: list[BlendProfile]
    strategy: BlendStrategy
    synthetic_label: str = "synthetic mixed voice"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GenerationResult(BaseModel):
    id: str = Field(default_factory=lambda: f"generation_{uuid4().hex[:12]}")
    audio_path: str
    metadata_path: str
    synthetic_label: str
    source_profile_ids: list[str]
    blend_strategy: BlendStrategy
```

- [ ] **Step 5: Implement blend and safety logic**

Create `backend/app/core/blends.py`:

```python
from app.models.schemas import BlendProfile, BlendProfileInput, BlendStrategy, VoiceBlend


class BlendError(ValueError):
    pass


def create_blend(
    name: str,
    profiles: list[BlendProfileInput],
    strategy: BlendStrategy,
) -> VoiceBlend:
    if len(profiles) < 2:
        raise BlendError("A mixed voice blend requires at least two profiles.")

    total = sum(profile.weight for profile in profiles)
    if total <= 0:
        raise BlendError("Blend weights must sum to a positive number.")

    normalized = [
        BlendProfile(
            voice_profile_id=profile.voice_profile_id,
            weight=profile.weight / total,
        )
        for profile in profiles
    ]
    return VoiceBlend(name=name, profiles=normalized, strategy=strategy)
```

Create `backend/app/core/safety.py`:

```python
class SafetyError(ValueError):
    pass


BLOCKED_PHRASES = (
    "wire transfer",
    "approve this payment",
    "approve this wire",
    "i am alice",
    "i am bob",
    "pretend to be",
    "do not disclose",
    "without disclosure",
)


def check_generation_request(text: str) -> None:
    lowered = text.lower()
    if any(phrase in lowered for phrase in BLOCKED_PHRASES):
        raise SafetyError("Blocked impersonation or fraud-like voice generation request.")
```

- [ ] **Step 6: Implement TTS adapter boundary and local WAV adapter**

Create `backend/app/tts/__init__.py`:

```python
```

Create `backend/app/tts/base.py`:

```python
from pathlib import Path
from typing import Protocol

from app.models.schemas import VoiceBlend


class TtsAdapter(Protocol):
    name: str

    def synthesize(self, text: str, blend: VoiceBlend) -> Path:
        raise NotImplementedError
```

Create `backend/app/tts/local_wav.py`:

```python
from pathlib import Path
import math
import struct
import wave

from app.models.schemas import VoiceBlend


class LocalWavTtsAdapter:
    name = "local_development_wav"

    def __init__(self, output_root: Path):
        self.output_root = output_root
        self.output_root.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str, blend: VoiceBlend) -> Path:
        output_path = self.output_root / f"{blend.id}.wav"
        sample_rate = 16000
        duration_seconds = max(1.0, min(4.0, len(text) / 35.0))
        frames = int(sample_rate * duration_seconds)
        frequency = 330 + int(sum(item.weight for item in blend.profiles) * 110)

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for index in range(frames):
                value = int(12000 * math.sin(2 * math.pi * frequency * index / sample_rate))
                wav_file.writeframes(struct.pack("<h", value))

        return output_path
```

Create `backend/app/tts/qwen.py`:

```python
from pathlib import Path

from app.models.schemas import VoiceBlend


class QwenTtsNotConfigured(RuntimeError):
    pass


class QwenTtsAdapter:
    name = "qwen3_tts"

    def __init__(self, model_root: Path | None = None):
        self.model_root = model_root

    def synthesize(self, text: str, blend: VoiceBlend) -> Path:
        raise QwenTtsNotConfigured(
            "Qwen3-TTS adapter is defined but not configured. "
            "Install Qwen3-TTS and set model_root before selecting this adapter."
        )
```

- [ ] **Step 7: Implement generation orchestration**

Create `backend/app/core/generation.py`:

```python
import json
from pathlib import Path

from app.core.safety import check_generation_request
from app.models.schemas import GenerationResult, VoiceBlend
from app.tts.base import TtsAdapter


def generate_agent_clip(
    prompt: str,
    agent_reply: str,
    blend: VoiceBlend,
    adapter: TtsAdapter,
) -> GenerationResult:
    check_generation_request(prompt)
    check_generation_request(agent_reply)

    audio_path = adapter.synthesize(agent_reply, blend)
    metadata_path = Path(audio_path).with_suffix(".json")
    result = GenerationResult(
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        synthetic_label=blend.synthetic_label,
        source_profile_ids=[profile.voice_profile_id for profile in blend.profiles],
        blend_strategy=blend.strategy,
    )
    metadata_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return result
```

- [ ] **Step 8: Run tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_blends.py tests/test_generation.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add backend/app backend/tests/test_blends.py backend/tests/test_generation.py
git commit -m "feat: add blend and generation core"
```

## Task 4: Backend API For Import, Blend, Generate, And History

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/app/core/storage.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Replace route tests with API behavior tests**

Replace `backend/tests/test_routes.py` with:

```python
from pathlib import Path

from fastapi.testclient import TestClient

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
```

- [ ] **Step 2: Run route tests to verify failure**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_routes.py -v
```

Expected: FAIL because `/api/blends` and `/api/generate` are missing.

- [ ] **Step 3: Extend routes**

Replace `backend/app/api/routes.py` with:

```python
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.blends import BlendError, create_blend
from app.core.generation import generate_agent_clip
from app.core.safety import SafetyError
from app.core.storage import GENERATION_ROOT, ensure_storage
from app.models.schemas import BlendProfileInput, BlendStrategy, GenerationResult, VoiceBlend
from app.tts.local_wav import LocalWavTtsAdapter

router = APIRouter(prefix="/api")


class CreateBlendRequest(BaseModel):
    name: str
    profiles: list[BlendProfileInput]
    strategy: BlendStrategy = "local_development_wav"


class GenerateRequest(BaseModel):
    prompt: str
    agent_reply: str
    blend: VoiceBlend


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/blends", response_model=VoiceBlend)
def create_blend_route(request: CreateBlendRequest) -> VoiceBlend:
    try:
        return create_blend(
            name=request.name,
            profiles=request.profiles,
            strategy=request.strategy,
        )
    except BlendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate", response_model=GenerationResult)
def generate_route(request: GenerateRequest) -> GenerationResult:
    ensure_storage()
    adapter = LocalWavTtsAdapter(output_root=Path(GENERATION_ROOT))
    try:
        return generate_agent_clip(
            prompt=request.prompt,
            agent_reply=request.agent_reply,
            blend=request.blend,
            adapter=adapter,
        )
    except SafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 4: Run backend tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/routes.py backend/app/core/storage.py backend/tests/test_routes.py
git commit -m "feat: expose blend generation API"
```

## Task 4A: User-Configurable API And Local LLM Provider

**Files:**
- Modify: `backend/app/models/schemas.py`
- Create: `backend/app/core/agent.py`
- Modify: `backend/app/api/routes.py`
- Create: `backend/tests/test_agent_provider.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Write failing provider tests**

Create `backend/tests/test_agent_provider.py`:

```python
import pytest

from app.core.agent import AgentProviderError, build_agent_payload, generate_agent_reply
from app.models.schemas import AgentConfig, AgentProviderKind


class FakeHttpClient:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.requests.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(self.payload)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def config(provider: AgentProviderKind) -> AgentConfig:
    return AgentConfig(
        provider=provider,
        model="demo-model",
        base_url="http://127.0.0.1:11434" if provider == "ollama" else "https://api.example.test/v1",
        api_key="sk-test" if provider == "openai_compatible" else "",
        system_prompt="You are a disclosed synthetic mixed-voice assistant.",
    )


def test_build_agent_payload_includes_synthetic_voice_instruction():
    payload = build_agent_payload(
        config("openai_compatible"),
        "Say hello.",
    )

    assert payload["model"] == "demo-model"
    assert "disclosed synthetic mixed-voice assistant" in payload["messages"][0]["content"]
    assert payload["messages"][1]["content"] == "Say hello."


def test_openai_compatible_provider_uses_user_api_settings():
    client = FakeHttpClient({"choices": [{"message": {"content": "Hello from API."}}]})

    reply = generate_agent_reply(
        prompt="Say hello.",
        config=config("openai_compatible"),
        http_client=client,
    )

    assert reply == "Hello from API."
    assert client.requests[0]["url"] == "https://api.example.test/v1/chat/completions"
    assert client.requests[0]["headers"]["Authorization"] == "Bearer sk-test"


def test_ollama_provider_uses_local_endpoint_without_api_key():
    client = FakeHttpClient({"message": {"content": "Hello from local LLM."}})

    reply = generate_agent_reply(
        prompt="Say hello.",
        config=config("ollama"),
        http_client=client,
    )

    assert reply == "Hello from local LLM."
    assert client.requests[0]["url"] == "http://127.0.0.1:11434/api/chat"
    assert "Authorization" not in client.requests[0]["headers"]


def test_provider_rejects_missing_model():
    bad = config("ollama").model_copy(update={"model": ""})

    with pytest.raises(AgentProviderError, match="model"):
        generate_agent_reply("Say hello.", bad, http_client=FakeHttpClient({}))
```

- [ ] **Step 2: Run provider tests to verify failure**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_agent_provider.py -v
```

Expected: FAIL because `app.core.agent` and agent schemas do not exist.

- [ ] **Step 3: Add agent provider schemas**

Append to `backend/app/models/schemas.py`:

```python
AgentProviderKind = Literal["openai_compatible", "ollama"]


class AgentConfig(BaseModel):
    provider: AgentProviderKind
    model: str
    base_url: str
    api_key: str = ""
    system_prompt: str = "You are a disclosed synthetic mixed-voice assistant."


class AgentReplyRequest(BaseModel):
    prompt: str
    config: AgentConfig


class AgentReply(BaseModel):
    reply: str
    provider: AgentProviderKind
    model: str
```

- [ ] **Step 4: Implement provider-neutral agent core**

Create `backend/app/core/agent.py`:

```python
from typing import Any, Protocol

import httpx

from app.core.safety import check_generation_request
from app.models.schemas import AgentConfig, AgentReply


class AgentProviderError(ValueError):
    pass


class HttpClient(Protocol):
    def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        raise NotImplementedError


def build_agent_payload(config: AgentConfig, prompt: str) -> dict[str, Any]:
    if not config.model.strip():
        raise AgentProviderError("Agent model is required.")
    if not config.base_url.strip():
        raise AgentProviderError("Agent base_url is required.")
    check_generation_request(prompt)

    return {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": config.system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }


def generate_agent_reply(
    prompt: str,
    config: AgentConfig,
    http_client: HttpClient | None = None,
) -> str:
    client = http_client or httpx.Client()
    payload = build_agent_payload(config, prompt)
    base_url = config.base_url.rstrip("/")

    if config.provider == "openai_compatible":
        if not config.api_key.strip():
            raise AgentProviderError("API key is required for OpenAI-compatible providers.")
        response = client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
    elif config.provider == "ollama":
        response = client.post(
            f"{base_url}/api/chat",
            headers={"Content-Type": "application/json"},
            json={**payload, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["message"]["content"]
    else:
        raise AgentProviderError(f"Unsupported agent provider: {config.provider}")

    check_generation_request(reply)
    return reply


def generate_agent_reply_record(prompt: str, config: AgentConfig) -> AgentReply:
    reply = generate_agent_reply(prompt=prompt, config=config)
    return AgentReply(reply=reply, provider=config.provider, model=config.model)
```

- [ ] **Step 5: Add agent reply route**

Append imports to `backend/app/api/routes.py`:

```python
from app.core.agent import AgentProviderError, generate_agent_reply_record
from app.models.schemas import AgentReply, AgentReplyRequest
```

Append route to `backend/app/api/routes.py`:

```python
@router.post("/agent/reply", response_model=AgentReply)
def agent_reply_route(request: AgentReplyRequest) -> AgentReply:
    try:
        return generate_agent_reply_record(prompt=request.prompt, config=request.config)
    except (AgentProviderError, SafetyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 6: Add route test with monkeypatched provider**

Append to `backend/tests/test_routes.py`:

```python
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
```

- [ ] **Step 7: Run provider and route tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_agent_provider.py tests/test_routes.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/models/schemas.py backend/app/core/agent.py backend/app/api/routes.py backend/tests/test_agent_provider.py backend/tests/test_routes.py
git commit -m "feat: add configurable agent providers"
```

## Task 5: Frontend Skeleton And Studio UI

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/components/AgentProviderSettings.tsx`
- Create: `frontend/src/components/VoiceLibrary.tsx`
- Create: `frontend/src/components/ImportVoice.tsx`
- Create: `frontend/src/components/BlendMixer.tsx`
- Create: `frontend/src/components/AgentChat.tsx`
- Create: `frontend/src/components/GenerationHistory.tsx`
- Create: `frontend/tests/App.test.tsx`

- [ ] **Step 1: Create package and test shell**

Create `frontend/package.json`:

```json
{
  "name": "mixed-voice-agent-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^5.0.0",
    "vite": "^8.0.0",
    "typescript": "^5.9.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "jsdom": "^25.0.0",
    "vitest": "^3.0.0"
  }
}
```

Create `frontend/tests/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../src/App";

describe("App", () => {
  it("renders the mixed voice studio", () => {
    render(<App />);
    expect(screen.getByText("Mixed Voice Agent Studio")).toBeInTheDocument();
    expect(screen.getByText("Voice Library")).toBeInTheDocument();
    expect(screen.getByText("Blend Mixer")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run frontend test to verify failure**

Run:

```powershell
cd frontend
npm install
npm test
```

Expected: FAIL because `src/App` does not exist.

- [ ] **Step 3: Add Vite config and HTML**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mixed Voice Agent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src", "tests"]
}
```

Create `frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/testSetup.ts",
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
```

Create `frontend/src/testSetup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Add frontend types and API client**

Create `frontend/src/types.ts`:

```ts
export type BlendStrategy = "local_development_wav";

export type BlendProfile = {
  voice_profile_id: string;
  weight: number;
};

export type VoiceBlend = {
  id: string;
  name: string;
  profiles: BlendProfile[];
  strategy: BlendStrategy;
  synthetic_label: string;
};

export type GenerationResult = {
  id: string;
  audio_path: string;
  metadata_path: string;
  synthetic_label: string;
  source_profile_ids: string[];
  blend_strategy: BlendStrategy;
};

export type AgentProviderKind = "openai_compatible" | "ollama";

export type AgentConfig = {
  provider: AgentProviderKind;
  model: string;
  base_url: string;
  api_key: string;
  system_prompt: string;
};

export type AgentReply = {
  reply: string;
  provider: AgentProviderKind;
  model: string;
};
```

Create `frontend/src/api.ts`:

```ts
import type { AgentConfig, AgentReply, GenerationResult, VoiceBlend } from "./types";

export async function createBlend(): Promise<VoiceBlend> {
  const response = await fetch("/api/blends", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "Demo Pair",
      profiles: [
        { voice_profile_id: "voice_a", weight: 1 },
        { voice_profile_id: "voice_b", weight: 1 },
      ],
      strategy: "local_development_wav",
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function generateClip(blend: VoiceBlend, agentReply: string): Promise<GenerationResult> {
  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: "Generate a disclosed synthetic assistant reply.",
      agent_reply: agentReply,
      blend,
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function requestAgentReply(config: AgentConfig, prompt: string): Promise<AgentReply> {
  const response = await fetch("/api/agent/reply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config, prompt }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
```

- [ ] **Step 5: Add UI components**

Create `frontend/src/components/AgentProviderSettings.tsx`:

```tsx
import type { AgentConfig, AgentProviderKind } from "../types";

type Props = {
  value: AgentConfig;
  onChange: (config: AgentConfig) => void;
};

export function AgentProviderSettings({ value, onChange }: Props) {
  function update(partial: Partial<AgentConfig>) {
    onChange({ ...value, ...partial });
  }

  function switchProvider(provider: AgentProviderKind) {
    if (provider === "ollama") {
      update({ provider, base_url: "http://127.0.0.1:11434", api_key: "", model: "llama3.1" });
    } else {
      update({ provider, base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini" });
    }
  }

  return (
    <section className="panel">
      <h2>Agent Provider</h2>
      <div className="segmented" role="group" aria-label="Agent provider">
        <button type="button" className={value.provider === "openai_compatible" ? "active" : ""} onClick={() => switchProvider("openai_compatible")}>
          API
        </button>
        <button type="button" className={value.provider === "ollama" ? "active" : ""} onClick={() => switchProvider("ollama")}>
          Local
        </button>
      </div>
      <label>
        Base URL
        <input value={value.base_url} onChange={(event) => update({ base_url: event.target.value })} />
      </label>
      <label>
        Model
        <input value={value.model} onChange={(event) => update({ model: event.target.value })} />
      </label>
      {value.provider === "openai_compatible" ? (
        <label>
          API key
          <input type="password" value={value.api_key} onChange={(event) => update({ api_key: event.target.value })} />
        </label>
      ) : null}
    </section>
  );
}
```

Create `frontend/src/components/VoiceLibrary.tsx`:

```tsx
export function VoiceLibrary() {
  return (
    <section className="panel">
      <h2>Voice Library</h2>
      <div className="voice-list">
        <div>Alice sample <span>Consent ready</span></div>
        <div>Bob sample <span>Consent ready</span></div>
      </div>
    </section>
  );
}
```

Create `frontend/src/components/ImportVoice.tsx`:

```tsx
import { Upload } from "lucide-react";

export function ImportVoice() {
  return (
    <section className="panel">
      <h2>Import Voice</h2>
      <button type="button" className="icon-button" aria-label="Import consented voice sample">
        <Upload size={18} />
      </button>
      <p>Every imported sample requires self or written permission before blending.</p>
    </section>
  );
}
```

Create `frontend/src/components/BlendMixer.tsx`:

```tsx
import type { VoiceBlend } from "../types";

type Props = {
  blend: VoiceBlend | null;
  onCreateBlend: () => void;
};

export function BlendMixer({ blend, onCreateBlend }: Props) {
  return (
    <section className="panel">
      <h2>Blend Mixer</h2>
      <button type="button" onClick={onCreateBlend}>Create 50/50 demo blend</button>
      {blend ? (
        <dl>
          <dt>Name</dt>
          <dd>{blend.name}</dd>
          <dt>Label</dt>
          <dd>{blend.synthetic_label}</dd>
        </dl>
      ) : null}
    </section>
  );
}
```

Create `frontend/src/components/AgentChat.tsx`:

```tsx
import type { VoiceBlend } from "../types";

type Props = {
  blend: VoiceBlend | null;
  onGenerate: (prompt: string) => void;
};

export function AgentChat({ blend, onGenerate }: Props) {
  const prompt = "Introduce yourself as a disclosed synthetic mixed voice assistant.";

  return (
    <section className="panel chat-panel">
      <h2>Agent Chat</h2>
      <textarea
        aria-label="Agent prompt text"
        defaultValue={prompt}
      />
      <button
        type="button"
        disabled={!blend}
        onClick={() => onGenerate(prompt)}
      >
        Generate AI Voice
      </button>
    </section>
  );
}
```

Create `frontend/src/components/GenerationHistory.tsx`:

```tsx
import type { GenerationResult } from "../types";

type Props = {
  generations: GenerationResult[];
};

export function GenerationHistory({ generations }: Props) {
  return (
    <section className="panel">
      <h2>History</h2>
      {generations.length === 0 ? (
        <p>No generated clips yet.</p>
      ) : (
        <ul>
          {generations.map((item) => (
            <li key={item.id}>
              {item.synthetic_label} using {item.source_profile_ids.join(" + ")}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

- [ ] **Step 6: Add App, entrypoint, and styles**

Create `frontend/src/App.tsx`:

```tsx
import { useState } from "react";
import { createBlend, generateClip, requestAgentReply } from "./api";
import { AgentChat } from "./components/AgentChat";
import { AgentProviderSettings } from "./components/AgentProviderSettings";
import { BlendMixer } from "./components/BlendMixer";
import { GenerationHistory } from "./components/GenerationHistory";
import { ImportVoice } from "./components/ImportVoice";
import { VoiceLibrary } from "./components/VoiceLibrary";
import type { AgentConfig, GenerationResult, VoiceBlend } from "./types";
import "./styles.css";

export default function App() {
  const [agentConfig, setAgentConfig] = useState<AgentConfig>({
    provider: "ollama",
    model: "llama3.1",
    base_url: "http://127.0.0.1:11434",
    api_key: "",
    system_prompt: "You are a disclosed synthetic mixed-voice assistant.",
  });
  const [blend, setBlend] = useState<VoiceBlend | null>(null);
  const [generations, setGenerations] = useState<GenerationResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleCreateBlend() {
    setError(null);
    try {
      setBlend(await createBlend());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Blend creation failed");
    }
  }

  async function handleGenerate(prompt: string) {
    if (!blend) return;
    setError(null);
    try {
      const agentReply = await requestAgentReply(agentConfig, prompt);
      const result = await generateClip(blend, agentReply.reply);
      setGenerations((current) => [result, ...current]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    }
  }

  return (
    <main>
      <header>
        <p>Local-first prototype</p>
        <h1>Mixed Voice Agent Studio</h1>
      </header>
      {error ? <div className="error" role="alert">{error}</div> : null}
      <div className="layout">
        <AgentProviderSettings value={agentConfig} onChange={setAgentConfig} />
        <VoiceLibrary />
        <ImportVoice />
        <BlendMixer blend={blend} onCreateBlend={handleCreateBlend} />
        <AgentChat blend={blend} onGenerate={handleGenerate} />
        <GenerationHistory generations={generations} />
      </div>
    </main>
  );
}
```

Create `frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

Create `frontend/src/styles.css`:

```css
:root {
  color: #141414;
  background: #f6f7f2;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body {
  margin: 0;
}

main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px;
}

header {
  margin-bottom: 28px;
}

header p {
  margin: 0 0 8px;
  color: #596052;
}

h1 {
  margin: 0;
  font-size: 40px;
}

h2 {
  margin-top: 0;
  font-size: 18px;
}

.layout {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.panel {
  border: 1px solid #d7dacd;
  background: #fffef9;
  border-radius: 8px;
  padding: 18px;
}

.chat-panel {
  grid-column: span 2;
}

button {
  border: 1px solid #1f2a22;
  background: #1f2a22;
  color: #fff;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.icon-button {
  width: 40px;
  height: 40px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

textarea {
  width: 100%;
  min-height: 120px;
  box-sizing: border-box;
  margin-bottom: 12px;
}

input {
  width: 100%;
  box-sizing: border-box;
  margin: 6px 0 12px;
  padding: 9px 10px;
  border: 1px solid #c8ccbe;
  border-radius: 6px;
}

.segmented {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 12px;
}

.segmented button {
  background: #eef0e8;
  color: #1f2a22;
}

.segmented button.active {
  background: #1f2a22;
  color: #fff;
}

.voice-list {
  display: grid;
  gap: 10px;
}

.voice-list div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.voice-list span {
  color: #3f6f46;
}

.error {
  border: 1px solid #a93d3d;
  background: #fff0f0;
  color: #812828;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 16px;
}

@media (max-width: 820px) {
  main {
    padding: 20px;
  }

  .layout {
    grid-template-columns: 1fr;
  }

  .chat-panel {
    grid-column: span 1;
  }
}
```

- [ ] **Step 7: Run frontend checks**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: PASS for tests and successful Vite build.

- [ ] **Step 8: Commit**

```powershell
git add frontend
git commit -m "feat: add mixed voice studio frontend"
```

## Task 6: Voice Import API And Local File Storage

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/app/core/storage.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/tests/test_routes.py`
- Modify: `frontend/src/components/ImportVoice.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Add backend import route test**

Append to `backend/tests/test_routes.py`:

```python
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
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_routes.py::test_import_voice_requires_consent_fields -v
```

Expected: FAIL because `/api/voices` is missing.

- [ ] **Step 3: Add storage helper**

Append to `backend/app/core/storage.py`:

```python
import json
from uuid import uuid4

from app.models.schemas import VoiceProfile


def new_voice_profile_id() -> str:
    return f"voice_{uuid4().hex[:12]}"


def save_voice_profile(profile: VoiceProfile, source_bytes: bytes, file_name: str) -> VoiceProfile:
    ensure_storage()
    voice_dir = VOICE_ROOT / profile.id
    voice_dir.mkdir(parents=True, exist_ok=True)
    source_path = voice_dir / file_name
    source_path.write_bytes(source_bytes)
    updated = profile.model_copy(
        update={
            "source_audio_path": str(source_path),
            "cleaned_audio_path": str(source_path),
        }
    )
    (voice_dir / "profile.json").write_text(
        json.dumps(updated.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return updated
```

- [ ] **Step 4: Add voice import route**

Append imports to `backend/app/api/routes.py`:

```python
from fastapi import File, Form, UploadFile
from app.core.audio import analyze_audio_sample
from app.core.consent import ConsentError, create_consent_record
from app.core.storage import new_voice_profile_id, save_voice_profile
from app.models.schemas import ConsentRequest, VoiceProfile
```

Append route to `backend/app/api/routes.py`:

```python
@router.post("/voices", response_model=VoiceProfile)
async def import_voice_route(
    speaker_display_name: str = Form(...),
    consent_type: str = Form(...),
    allowed_uses: str = Form(...),
    confirmed_by: str = Form(...),
    notes: str = Form(""),
    file: UploadFile = File(...),
) -> VoiceProfile:
    voice_id = new_voice_profile_id()
    consent_request = ConsentRequest(
        speaker_display_name=speaker_display_name,
        consent_type=consent_type,
        allowed_uses=[item.strip() for item in allowed_uses.split(",") if item.strip()],
        confirmed_by=confirmed_by,
        notes=notes,
    )
    try:
        consent = create_consent_record(voice_id, consent_request)
    except ConsentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    source_bytes = await file.read()
    ensure_storage()
    temp_dir = Path("data") / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / (file.filename or "sample.wav")
    temp_path.write_bytes(source_bytes)
    quality = analyze_audio_sample(temp_path)

    profile = VoiceProfile(
        id=voice_id,
        display_name=speaker_display_name,
        consent=consent,
        source_audio_path="",
        cleaned_audio_path="",
        quality=quality,
    )
    return save_voice_profile(profile, source_bytes, file.filename or "sample.wav")
```

- [ ] **Step 5: Run backend tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -v
```

Expected: PASS.

- [ ] **Step 6: Update frontend import UI**

Extend `frontend/src/types.ts`:

```ts
export type VoiceProfile = {
  id: string;
  display_name: string;
  source_audio_path: string;
  cleaned_audio_path: string;
  consent: {
    voice_profile_id: string;
    speaker_display_name: string;
    synthetic_voice_allowed: boolean;
    allowed_uses: string[];
  };
};
```

Append to `frontend/src/api.ts`:

```ts
import type { VoiceProfile } from "./types";

export async function importVoice(file: File, displayName: string): Promise<VoiceProfile> {
  const form = new FormData();
  form.set("speaker_display_name", displayName);
  form.set("consent_type", "self_or_written_permission");
  form.set("allowed_uses", "private_agent_voice,local_audio_export");
  form.set("confirmed_by", "local_user");
  form.set("notes", "Confirmed in local prototype UI.");
  form.set("file", file);

  const response = await fetch("/api/voices", {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
```

Replace `frontend/src/components/ImportVoice.tsx` with:

```tsx
import { Upload } from "lucide-react";
import { useState } from "react";
import { importVoice } from "../api";
import type { VoiceProfile } from "../types";

type Props = {
  onImported?: (profile: VoiceProfile) => void;
};

export function ImportVoice({ onImported }: Props) {
  const [displayName, setDisplayName] = useState("Alice");
  const [busy, setBusy] = useState(false);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    try {
      const profile = await importVoice(file, displayName);
      onImported?.(profile);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Import Voice</h2>
      <label>
        Speaker name
        <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
      </label>
      <label className="file-button">
        <Upload size={18} />
        <span>{busy ? "Importing" : "Import consented sample"}</span>
        <input
          aria-label="Import consented voice sample"
          type="file"
          accept="audio/*"
          disabled={busy}
          onChange={(event) => void handleFile(event.target.files?.[0])}
        />
      </label>
      <p>Every imported sample requires self or written permission before blending.</p>
    </section>
  );
}
```

- [ ] **Step 7: Run checks**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add backend frontend
git commit -m "feat: add consented voice import"
```

## Task 7: Documentation And Launch Verification

**Files:**
- Create: `docs/launch-checklist.md`
- Modify: `.gitignore`

- [ ] **Step 1: Update `.gitignore` for generated data**

Add these lines to `.gitignore`:

```gitignore
backend/.venv/
backend/data/
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 2: Create launch checklist**

Create `docs/launch-checklist.md`:

```markdown
# Mixed Voice Agent Launch Checklist

## Required Verification

- Backend tests pass with `cd backend && .\.venv\Scripts\python -m pytest -v`.
- Frontend tests pass with `cd frontend && npm test`.
- Frontend production build passes with `cd frontend && npm run build`.
- Manual import of at least two consented voice samples succeeds.
- Blend creation with two profiles succeeds and weights normalize to 100%.
- Agent provider settings accept either an OpenAI-compatible API configuration or an Ollama-compatible local endpoint.
- Agent reply generation succeeds through the selected provider before TTS synthesis.
- Audio generation creates a `.wav` file and adjacent `.json` metadata file.
- Metadata includes `synthetic_label`, `source_profile_ids`, and `blend_strategy`.
- Safety filter blocks impersonation or payment authorization language.
- Generated audio is disclosed as synthetic in UI and metadata.

## Known MVP Limits

- Local development adapter produces valid WAV preview audio but does not clone voices.
- Qwen3-TTS adapter supports the real cloning path but requires model installation/configuration before real cloning.
- Microphone input and realtime WebRTC conversation are deferred.
- Public voice sharing and celebrity/public-figure cloning are out of scope.
```

- [ ] **Step 3: Run full verification**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -v
cd ..\frontend
npm test
npm run build
```

Expected: all commands pass.

- [ ] **Step 4: Check git status**

Run:

```powershell
git status --short
```

Expected: only `.gitignore` and `docs/launch-checklist.md` are modified/untracked.

- [ ] **Step 5: Commit**

```powershell
git add .gitignore docs/launch-checklist.md
git commit -m "docs: add launch checklist"
```

## Task 8: Qwen3-TTS Adapter Implementation

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/tts/qwen.py`
- Create: `backend/tests/test_qwen_adapter.py`
- Modify: `docs/launch-checklist.md`

- [ ] **Step 1: Add optional Qwen dependency group**

Modify `backend/pyproject.toml` so the optional dependencies section is:

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "httpx>=0.27.0"
]
qwen = [
  "numpy>=2.0.0",
  "qwen-tts>=0.1.0",
  "soundfile>=0.12.1",
  "torch>=2.4.0"
]
```

- [ ] **Step 2: Write adapter tests with a fake Qwen model**

Create `backend/tests/test_qwen_adapter.py`:

```python
from pathlib import Path

import numpy as np

from app.core.blends import create_blend
from app.models.schemas import BlendProfileInput, VoiceProfile
from app.tts.qwen import QwenTtsAdapter


class FakeQwenModel:
    def __init__(self):
        self.prompt_calls = []
        self.generate_calls = []

    def create_voice_clone_prompt(self, ref_audio, ref_text, x_vector_only_mode=False):
        self.prompt_calls.append(
            {
                "ref_audio": ref_audio,
                "ref_text": ref_text,
                "x_vector_only_mode": x_vector_only_mode,
            }
        )
        return {"prompt": Path(ref_audio).stem, "text": ref_text}

    def generate_voice_clone(self, text, language, voice_clone_prompt):
        self.generate_calls.append(
            {
                "text": text,
                "language": language,
                "voice_clone_prompt": voice_clone_prompt,
            }
        )
        return [np.zeros(1600, dtype=np.float32)], 16000


def profile(profile_id: str, audio_path: Path) -> VoiceProfile:
    return VoiceProfile.model_validate(
        {
            "id": profile_id,
            "display_name": profile_id,
            "consent": {
                "voice_profile_id": profile_id,
                "speaker_display_name": profile_id,
                "consent_type": "self_or_written_permission",
                "allowed_uses": ["private_agent_voice"],
                "confirmed_by": "local_user",
                "notes": "",
                "synthetic_voice_allowed": True,
            },
            "source_audio_path": str(audio_path),
            "cleaned_audio_path": str(audio_path),
            "quality": {
                "file_name": audio_path.name,
                "size_bytes": 10,
                "format": "wav",
                "duration_seconds": 5,
                "warnings": [],
            },
        }
    )


def test_qwen_adapter_builds_prompts_for_each_source_profile(tmp_path: Path):
    audio_a = tmp_path / "a.wav"
    audio_b = tmp_path / "b.wav"
    audio_a.write_bytes(b"fake-audio-a")
    audio_b.write_bytes(b"fake-audio-b")
    fake_model = FakeQwenModel()
    adapter = QwenTtsAdapter(model=fake_model, output_root=tmp_path)
    blend = create_blend(
        name="Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=1),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="multi_reference_prompt",
    )

    output = adapter.synthesize(
        text="Hello from a cloned blend.",
        blend=blend,
        voice_profiles={
            "voice_a": profile("voice_a", audio_a),
            "voice_b": profile("voice_b", audio_b),
        },
    )

    assert output.exists()
    assert len(fake_model.prompt_calls) == 2
    assert fake_model.generate_calls[0]["voice_clone_prompt"][0]["prompt"] == "a"
    assert fake_model.generate_calls[0]["voice_clone_prompt"][1]["prompt"] == "b"
```

- [ ] **Step 3: Run the Qwen adapter test to verify failure**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_qwen_adapter.py -v
```

Expected: FAIL because the current `QwenTtsAdapter` does not accept `model`, `output_root`, or `voice_profiles`.

- [ ] **Step 4: Implement Qwen adapter with injectable model**

Replace `backend/app/tts/qwen.py` with:

```python
from pathlib import Path
from typing import Any

import soundfile as sf

from app.models.schemas import VoiceBlend, VoiceProfile


class QwenTtsNotConfigured(RuntimeError):
    pass


class QwenTtsAdapter:
    name = "qwen3_tts"

    def __init__(
        self,
        model: Any | None = None,
        output_root: Path | None = None,
        language: str = "English",
        x_vector_only_mode: bool = False,
    ):
        self.model = model
        self.output_root = output_root or Path("data/generations")
        self.language = language
        self.x_vector_only_mode = x_vector_only_mode
        self.output_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_pretrained(
        cls,
        model_id: str = "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        device_map: str = "auto",
        dtype: Any | None = None,
        output_root: Path | None = None,
    ) -> "QwenTtsAdapter":
        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:
            raise QwenTtsNotConfigured(
                "qwen-tts is not installed. Install backend with the qwen extra: "
                "python -m pip install -e \".[qwen]\""
            ) from exc

        kwargs: dict[str, Any] = {"device_map": device_map}
        if dtype is not None:
            kwargs["dtype"] = dtype
        model = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
        return cls(model=model, output_root=output_root)

    def synthesize(
        self,
        text: str,
        blend: VoiceBlend,
        voice_profiles: dict[str, VoiceProfile] | None = None,
    ) -> Path:
        if self.model is None:
            raise QwenTtsNotConfigured(
                "Qwen3-TTS model is not loaded. Use QwenTtsAdapter.from_pretrained()."
            )
        if not voice_profiles:
            raise QwenTtsNotConfigured("Qwen synthesis requires voice profile artifacts.")

        prompts = []
        for blend_profile in blend.profiles:
            profile = voice_profiles[blend_profile.voice_profile_id]
            prompts.append(
                self.model.create_voice_clone_prompt(
                    ref_audio=profile.cleaned_audio_path,
                    ref_text=profile.display_name,
                    x_vector_only_mode=self.x_vector_only_mode,
                )
            )

        wavs, sample_rate = self.model.generate_voice_clone(
            text=text,
            language=self.language,
            voice_clone_prompt=prompts,
        )
        output_path = self.output_root / f"{blend.id}_qwen.wav"
        sf.write(output_path, wavs[0], sample_rate)
        return output_path
```

- [ ] **Step 5: Run Qwen adapter tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pip install soundfile numpy
.\.venv\Scripts\python -m pytest tests/test_qwen_adapter.py -v
```

Expected: PASS.

- [ ] **Step 6: Run full backend tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -v
```

Expected: PASS.

- [ ] **Step 7: Document Qwen setup in launch checklist**

Append to `docs/launch-checklist.md`:

```markdown
## Optional Real Qwen3-TTS Verification

- Install Qwen dependencies with `cd backend && .\.venv\Scripts\python -m pip install -e ".[qwen]"`.
- Configure `QwenTtsAdapter.from_pretrained()` with the desired model id.
- Import two clean 5-30 second consented WAV samples.
- Create a blend using `multi_reference_prompt`.
- Generate a short reply and confirm the output WAV is produced by Qwen3-TTS rather than the local development adapter.
```

- [ ] **Step 8: Commit**

```powershell
git add backend/pyproject.toml backend/app/tts/qwen.py backend/tests/test_qwen_adapter.py docs/launch-checklist.md
git commit -m "feat: add Qwen TTS adapter path"
```

## Task 9: Start Local Development Servers

**Files:**
- No file changes.

- [ ] **Step 1: Start backend server**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected: Uvicorn runs at `http://127.0.0.1:8000`.

- [ ] **Step 2: Start frontend server in a second terminal**

Run:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Expected: Vite runs at `http://127.0.0.1:5173`.

- [ ] **Step 3: Manual smoke test**

Open `http://127.0.0.1:5173` and verify:

- The page shows `Mixed Voice Agent Studio`.
- `Create 50/50 demo blend` creates a synthetic mixed voice blend.
- `Generate Audio` creates a history entry.
- Backend `data/generations/` contains one `.wav` and one `.json` file.

## Plan Self-Review

Spec coverage:

- Research-backed architecture: covered by the saved design spec and this plan's React + FastAPI chained architecture.
- Imported voice samples: Task 6 adds `/api/voices` and frontend import UI.
- Consent metadata: Task 2 domain and Task 6 API enforce consent.
- Audio quality metadata: Task 2 analyzes imported audio metadata.
- Weighted multi-person blend: Task 3 domain and Task 4 API normalize blend weights and require at least two profiles.
- Agent reply generation path: Task 3/4 generate audio from agent reply text through the same orchestration path the LLM provider will call.
- User-configurable API/local LLM: Task 4A adds OpenAI-compatible and Ollama-compatible provider configuration, backend route, tests, and frontend provider settings.
- TTS adapter boundary: Task 3 defines local and Qwen adapter boundaries.
- Real imported-voice cloning path: Task 8 implements the Qwen adapter with injectable model loading and multi-reference prompts.
- Synthetic output metadata: Task 3 writes metadata, Task 7 verifies it.
- Safety checks: Task 3 blocks impersonation/fraud-like language, Task 7 verifies it.
- UI: Task 5 and Task 6 create studio views.
- Launch verification: Task 7 and Task 9 provide automated and manual checks.

Residual risk:

- The exact Qwen3-TTS runtime behavior must be verified on the target machine after installing model dependencies. Automated tests use an injected fake Qwen model so unit tests stay fast and deterministic.
