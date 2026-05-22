# Mixed Human Voice Agent

Local-first prototype for an AI voice agent that imports multiple consented voice samples, creates a weighted mixed-voice blend, asks a user-configured LLM for a reply, and generates labeled synthetic audio.

## What It Does

- Imports 5-30 second WAV voice samples with explicit self or written-permission consent metadata.
- Lists imported voice profiles from local storage.
- Builds a mixed voice from two or more imported profiles with user-controlled weights.
- Lets the user choose an OpenAI-compatible API provider or an Ollama-compatible local LLM endpoint.
- Generates an agent reply first, then synthesizes audio with either:
  - `local_development_wav`: deterministic preview WAV for development.
  - `qwen3_tts`: Qwen3-TTS voice-clone path, then weighted waveform mixing across imported profiles.
- Labels generated audio as synthetic in metadata and UI.
- Blocks high-risk impersonation/payment authorization language.

## Current Verification Status

The app, API flow, consent checks, provider configuration, blend weights, local preview audio, and mocked Qwen integration are covered by tests.

Real Qwen acoustic cloning/mixing is not verified in this checkout because the Qwen runtime and consented sample set are not installed here. Use `docs/qwen-runtime-verification.md` before claiming real cloned mixed-voice output on a target machine.

## Project Layout

```text
backend/   FastAPI app, storage, consent, blend, LLM provider, and TTS adapters
frontend/  React/Vite studio UI
docs/      design notes, launch checklist, and Qwen runtime verification
```

## Backend Setup

From the repository root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health
```

Qwen preflight:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/tts/qwen/status
```

## Frontend Setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## Typical Use

1. Start backend and frontend.
2. Configure the agent provider:
   - `Local`: Ollama-compatible endpoint such as `http://127.0.0.1:11434`.
   - `API`: OpenAI-compatible base URL, model, and API key.
3. Import at least two clean 5-30 second WAV voice samples where the speaker is you or has given written permission.
4. Adjust each voice's blend weight in `Blend Mixer`.
5. Select `Local preview` or `Qwen3-TTS` in `Voice Engine`.
6. Create the blend.
7. Enter the agent prompt and generate AI voice.

## Qwen Runtime

Install optional Qwen dependencies from `backend/`:

```powershell
.\.venv\Scripts\python -m pip install -e ".[qwen]"
```

If the selected model requires GPU acceleration, install the appropriate PyTorch build for the machine first. Then follow `docs/qwen-runtime-verification.md` with two or more consented samples.

## Tests

Backend:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -v
```

Frontend:

```powershell
cd frontend
npm test
npm run build
```

## Safety Rules

- Do not import public figures, celebrities, politicians, or third-party voices without explicit permission.
- Do not import malformed, non-WAV, shorter-than-5-second, or longer-than-30-second reference audio.
- Do not use generated audio for impersonation, payment authorization, identity verification, fraud, or deception.
- Keep generated audio disclosed as synthetic.
- Treat `local_development_wav` as a preview adapter only; it does not clone voices.
