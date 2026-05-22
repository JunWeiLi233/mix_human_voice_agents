# Qwen3-TTS Runtime Verification

This project supports two voice engines:

- `local_development_wav`: deterministic preview audio for development.
- `qwen3_tts`: real imported-voice synthesis using Qwen3-TTS reference audio plus transcript, then weighted waveform mixing across the selected imported profiles.

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
5. Import at least two clean 5-30 second voice samples with consent and paste the transcript that matches each uploaded sample.
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

## CLI Verification

After importing two or more consented profiles, run this from `backend/` to exercise the real Qwen adapter and write a verification report:

```powershell
.\.venv\Scripts\python -m app.cli.verify_qwen_runtime `
  --voice-profile-id voice_a `
  --voice-profile-id voice_b `
  --text "This is a disclosed synthetic mixed voice runtime verification." `
  --report data/qwen-runtime-verification-report.json
```

The report must contain `"status": "passed"`, `"tts_backend": "qwen3_tts"`, and an `output_audio_path` that exists before claiming real Qwen mixed-voice synthesis is verified.

If Qwen generation fails with a missing reference text error, re-import the voice sample with the matching transcript. The transcript should describe the words spoken in the reference clip, not the speaker's name.

## Report in the Studio

The backend exposes the saved report at `/api/tts/qwen/verification`. The frontend reads that endpoint on load and shows `Verification passed`, `Verification failed`, or `Verification missing` in the `Voice Engine` panel. When a passed report includes `output_audio_path`, the panel shows the verified output file path.

## Safety Gate

Only use samples where the speaker is the user or has provided written permission. Do not use public figures, celebrities, politicians, or third-party voices without consent.
