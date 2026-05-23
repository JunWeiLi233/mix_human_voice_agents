# Mixed Human Voice Agent

Local-first prototype for an AI voice agent that imports multiple consented voice samples, creates a weighted mixed-voice blend, asks a user-configured LLM for a reply, and generates labeled synthetic audio.

## What It Does

- Imports 5-30 second WAV voice samples and matching reference transcripts only after explicit self or written-permission consent confirmation.
- Lists imported voice profiles from local storage.
- Builds a mixed voice from two or more imported profiles with user-controlled weights.
- Deletes imported voice profiles, saved blends, and generated clips that depend on deleted voices.
- Lets the user choose ChatGPT/OpenAI, Claude/Anthropic, Gemini/Google, Grok/xAI, a custom OpenAI-compatible API, or an Ollama-compatible local LLM endpoint.
- Generates an agent reply first, then synthesizes audio with either:
  - `local_development_wav`: deterministic preview WAV for development.
  - `qwen3_tts`: Qwen3-TTS voice-clone path, then weighted waveform mixing across imported profiles.
- Surfaces the saved Qwen runtime verification report in the Voice Engine panel.
- Can run Qwen runtime verification from the studio after two or more consented voices are imported.
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

Qwen runtime verification report:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/tts/qwen/verification
```

Saved launch readiness audit:

```powershell
cd backend
.\.venv\Scripts\python -m app.cli.launch_readiness --report data/launch-readiness-report.json
```

The JSON report includes `next_actions`, a structured list of failed check ids, action text, and evidence for the UI and other agents.
The research review gate requires a current `Last checked: YYYY-MM-DD` date plus `Source Links` for OpenAI Voice Agents, LiveKit Voice AI, Pipecat, and Qwen3-TTS before launch readiness can pass.
Passed agent-provider and Qwen verification reports must be no older than 7 days at launch readiness time.

Agent provider preflight report:

```powershell
cd backend
.\.venv\Scripts\python -m app.cli.verify_agent_provider --provider openai_compatible --model local-qwen-agent --base-url http://127.0.0.1:1234/v1 --report data/agent-provider-verification-report.json
```

Terminal voice import:

```powershell
cd backend
.\.venv\Scripts\python -m app.cli.import_voice --speaker-display-name Alice --confirmed-by Junwei --notes "Written permission captured for private local mixed voice testing." --reference-text "Alice reads a clean reference sentence for Qwen cloning." --audio C:\path\to\alice.wav --metadata data\voices\last-imported-alice.json
```

Terminal blend creation from imported voices:

```powershell
cd backend
.\.venv\Scripts\python -m app.cli.create_blend --name "Launch blend" --profile voice_a=1 --profile voice_b=1 --strategy multi_reference_prompt --metadata data\blends\last-created-blend.json
```

Terminal Qwen mixed-voice generation after provider and Qwen verification:

```powershell
cd backend
.\.venv\Scripts\python -m app.cli.generate_voice --blend-id blend_launch --prompt "Greet the user as a disclosed synthetic assistant." --provider openai_compatible --model local-qwen-agent --base-url http://127.0.0.1:1234/v1 --metadata data\generations\last-generated-mixed-voice.json
```

This generation command refuses Qwen verification evidence that launch readiness would reject, including wrong backend, wrong strategy, missing source details, missing or invalid verified WAV output, or mismatched verified voice ids. Launch readiness also requires the generated Qwen mixed-voice `.wav` artifact to still exist alongside matching metadata.

Single-command launch sequence from a JSON manifest:

```powershell
cd backend
.\.venv\Scripts\python -m app.cli.run_launch_sequence --manifest launch-manifest.json --tasks ..\TASKS.md
```

Validate a launch manifest without importing voices, calling the agent provider, running Qwen, or refreshing readiness:

```powershell
cd backend
.\.venv\Scripts\python -m app.cli.run_launch_sequence --manifest launch-manifest.json --dry-run --report data\launch-sequence\sequence-report.json
```

The sequence validates at least two distinct speaker display names, checks each listed audio file exists, is a parseable WAV, contains audible signal, requires any supplied voice `weight` to be positive, requires the launch blend strategy to be `multi_reference_prompt`, requires any supplied `blend.name`, `qwen.text`, Qwen runtime option, and `agent_provider.prompt` to be non-blank, and confirms `agent_provider.provider` is one of `openai`, `anthropic`, `google`, `xai`, `openai_compatible`, or `ollama` before importing anything. A normal run exits successfully only if the final launch-readiness audit is ready.

Manifest shape:

```json
{
  "voices": [
    {
      "speaker_display_name": "Alice",
      "confirmed_by": "Junwei",
      "notes": "Written permission captured for private local mixed voice testing.",
      "reference_text": "Alice reads a clean reference sentence for Qwen cloning.",
      "audio": "C:\\path\\to\\alice.wav",
      "weight": 1
    },
    {
      "speaker_display_name": "Bob",
      "confirmed_by": "Junwei",
      "reference_text": "Bob reads a clean reference sentence for Qwen cloning.",
      "audio": "C:\\path\\to\\bob.wav",
      "weight": 1
    }
  ],
  "blend": { "name": "Launch blend" },
  "agent_provider": {
    "provider": "openai_compatible",
    "model": "local-qwen-agent",
    "base_url": "http://127.0.0.1:1234/v1",
    "api_key": ""
  },
  "qwen": {
    "text": "This is a disclosed synthetic mixed voice runtime verification.",
    "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    "device_map": "auto"
  },
  "generation": {
    "prompt": "Greet the user as a disclosed synthetic assistant."
  }
}
```

Refresh the handoff tasks from the same launch-readiness evidence:

```powershell
cd backend
.\.venv\Scripts\python -m app.cli.launch_readiness --report data/launch-readiness-report.json --tasks ..\TASKS.md
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
   - `ChatGPT`: OpenAI chat completions endpoint, model, and API key.
   - `Claude`: Anthropic Messages API endpoint, model, and API key.
   - `Grok`: xAI chat completions endpoint, model, and API key.
   - `Gemini`: Google Gemini `generateContent` endpoint, model, and API key.
   - `API`: custom OpenAI-compatible base URL, model, and API key.
   - `Local`: Ollama-compatible endpoint such as `http://127.0.0.1:11434`.
   Versioned base URLs are accepted for providers that commonly expose them, such as `https://api.anthropic.com/v1` and `http://127.0.0.1:11434/api`.
3. For each voice, enter who confirmed consent, add consent notes, paste the reference transcript, check the consent confirmation box, and import a clean 5-30 second WAV sample where the speaker is you or has given written permission.
4. Adjust each voice's blend weight in `Blend Mixer`.
5. Select `Local preview` or `Qwen3-TTS` in `Voice Engine`.
6. For Qwen launch checks, select the imported voices to verify in `Voice Engine`, run Qwen verification, and confirm the report passes.
7. Create the blend.
8. Enter the agent prompt and generate AI voice.

## Qwen Runtime

Install optional Qwen dependencies from `backend/`:

```powershell
.\.venv\Scripts\python -m pip install -e ".[qwen]"
```

If the selected model requires GPU acceleration, install the appropriate PyTorch build for the machine first. Then follow `docs/qwen-runtime-verification.md` with two or more consented samples.

## Research Notes

Current voice-agent practice splits into realtime speech-to-speech agents and chained STT/LLM/TTS pipelines. OpenAI's voice-agent docs recommend realtime sessions for low-latency speech-to-speech and chained pipelines when the application needs more control over each stage. LiveKit and Pipecat follow the same pipeline pattern for production voice agents. Qwen3-TTS voice cloning takes reference audio plus its transcript as reference text for cloned synthesis, so this app keeps imported voice profiles, transcripts, blend metadata, and TTS adapters separate instead of assuming a realtime model can directly own multi-person voice blending.

See `docs/research-review.md` for the dated source review used as the launch architecture rationale.

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
- Do not import a voice until the UI consent confirmation is checked and the consent record describes who confirmed permission.
- Do not import malformed, non-WAV, shorter-than-5-second, or longer-than-30-second reference audio, and keep each reference transcript matched to the uploaded sample.
- Do not use generated audio for impersonation, payment authorization, identity verification, fraud, or deception.
- Keep generated audio disclosed as synthetic.
- Treat `local_development_wav` as a preview adapter only; it does not clone voices.
