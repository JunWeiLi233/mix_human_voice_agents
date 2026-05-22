# Qwen3-TTS Runtime Verification

This project supports two voice engines:

- `local_development_wav`: deterministic preview audio for development.
- `qwen3_tts`: real imported-voice synthesis using Qwen3-TTS, then weighted waveform mixing across the selected imported profiles.

## Install Runtime Dependencies

From the backend directory:

```powershell
.\.venv\Scripts\python -m pip install -e ".[qwen]"
```

If the selected Qwen model requires GPU acceleration, install the correct PyTorch build for the machine before running the command above.

## Verify With Consented Samples

1. Start the backend:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. Start the frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

3. Open `http://127.0.0.1:5173`.
4. In `Voice Engine`, select `Qwen3-TTS`.
5. Import at least two clean 5-30 second voice samples with consent.
6. Create a blend from the imported voices.
7. Generate the agent reply.
8. Confirm the generated metadata includes:

```json
{
  "tts_backend": "qwen3_tts",
  "blend_strategy": "multi_reference_prompt",
  "synthetic_label": "synthetic mixed voice"
}
```

9. Listen to the generated audio and confirm it reflects the selected imported voices.

## Safety Gate

Only use samples where the speaker is the user or has provided written permission. Do not use public figures, celebrities, politicians, or third-party voices without consent.

