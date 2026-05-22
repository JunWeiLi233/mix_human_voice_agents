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

Qwen's published package examples load Base voice-clone models with `Qwen3TTSModel.from_pretrained(...)`, then call `create_voice_clone_prompt(ref_audio=..., ref_text=...)` and `generate_voice_clone(...)`. This project follows that pattern once per imported profile, then mixes the generated waveforms by the user's blend weights.

Useful runtime settings:

```powershell
$env:QWEN_TTS_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
$env:QWEN_TTS_DEVICE_MAP = "cuda:0"
$env:QWEN_TTS_DTYPE = "bfloat16"
$env:QWEN_TTS_ATTN_IMPLEMENTATION = "flash_attention_2"
```

For a smaller Base model, use `Qwen/Qwen3-TTS-12Hz-0.6B-Base`. For CPU-only diagnostics, set `QWEN_TTS_DEVICE_MAP=cpu` and omit dtype/FlashAttention settings if the local install does not support them.

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

## Studio Verification

After importing at least two consented profiles from distinct speakers, use the `Voice Engine` panel:

1. Select `Qwen3-TTS`.
2. Select at least two distinct imported voices to include in the verification run.
3. Edit `Qwen verification text` if needed.
4. Click `Run Qwen verification`.
5. Confirm the panel shows `Verification passed` and the verified output path exists.

The studio writes the same report file as the CLI at `data/qwen-runtime-verification-report.json`.

## CLI Verification

After importing two or more consented profiles, you can also run this from `backend/` to exercise the real Qwen adapter and write a verification report:

```powershell
.\.venv\Scripts\python -m app.cli.verify_qwen_runtime `
  --voice-profile-id voice_a `
  --voice-profile-id voice_b `
  --text "This is a disclosed synthetic mixed voice runtime verification." `
  --model-id Qwen/Qwen3-TTS-12Hz-1.7B-Base `
  --device-map cuda:0 `
  --dtype bfloat16 `
  --attn-implementation flash_attention_2 `
  --report data/qwen-runtime-verification-report.json
```

The report must contain `"status": "passed"`, `"tts_backend": "qwen3_tts"`, `source_profile_details` for at least two imported consented profiles, and an `output_audio_path` that exists before claiming real Qwen mixed-voice synthesis is verified.

If Qwen generation fails with a missing reference text error, re-import the voice sample with the matching transcript. The transcript should describe the words spoken in the reference clip, not the speaker's name.

## Report Display

The backend exposes the saved report at `/api/tts/qwen/verification`. The frontend reads that endpoint on load and shows `Verification passed`, `Verification failed`, or `Verification missing` in the `Voice Engine` panel. When a passed report includes `output_audio_path`, the panel shows the verified output file path.

## Safety Gate

Only use samples where the speaker is the user or has provided written permission. Do not use public figures, celebrities, politicians, or third-party voices without consent.

## Current Qwen Sources Checked

- QwenLM/Qwen3-TTS GitHub README: documents local demo commands for `Qwen/Qwen3-TTS-12Hz-1.7B-Base` and Qwen3-TTS API/runtime options.
- Qwen/Qwen3-TTS-12Hz-1.7B-Base Hugging Face model card: lists released 1.7B and 0.6B Base voice-clone models, package install guidance, and the `create_voice_clone_prompt` / `generate_voice_clone` workflow.
- qwen-tts PyPI package page: documents the same Python package workflow and reusable voice-clone prompts.
