# Mixed Voice Agent Launch Checklist

## Required Verification

- Backend tests pass with `cd backend && .\.venv\Scripts\python -m pytest -v`.
- Frontend tests pass with `cd frontend && npm test`.
- Frontend production build passes with `cd frontend && npm run build`.
- Manual import of at least two valid 5-30 second consented WAV samples with matching reference transcripts succeeds.
- Import is disabled until the user confirms self or written-permission consent in the UI.
- Imported profile metadata records `confirmed_by` and consent notes from user input.
- Imported profile metadata records the user-provided reference transcript used by Qwen voice cloning.
- Malformed, non-WAV, shorter-than-5-second, and longer-than-30-second samples are rejected.
- Blend creation with two profiles succeeds and weights normalize to 100%.
- Agent provider settings accept either an OpenAI-compatible API configuration or an Ollama-compatible local endpoint.
- Agent reply generation succeeds through the selected provider before TTS synthesis.
- Audio generation creates a `.wav` file and adjacent `.json` metadata file.
- Metadata includes `synthetic_label`, `source_profile_ids`, and `blend_strategy`.
- Safety filter blocks impersonation or payment authorization language.
- Generated audio is disclosed as synthetic in UI and metadata.
- Deleting an imported voice profile removes its local profile/audio directory.
- Deleting an imported voice profile removes saved blend presets that reference that profile so stale blends cannot generate audio.
- Deleting an imported voice profile removes generated clip audio and metadata that reference that profile.

## Known MVP Limits

- Local development adapter produces valid WAV preview audio but does not clone voices.
- Qwen3-TTS adapter supports the real cloning path but requires model installation/configuration before real cloning.
- Microphone input and realtime WebRTC conversation are deferred.
- Public voice sharing and celebrity/public-figure cloning are out of scope.

## Optional Real Qwen3-TTS Verification

- Install Qwen dependencies with `cd backend && .\.venv\Scripts\python -m pip install -e ".[qwen]"`.
- Configure `QwenTtsAdapter.from_pretrained()` with the desired model id.
- Import two clean 5-30 second consented WAV samples and paste transcripts that match each sample.
- Create a blend using `multi_reference_prompt`.
- Run `cd backend && .\.venv\Scripts\python -m app.cli.verify_qwen_runtime --voice-profile-id <id-a> --voice-profile-id <id-b> --report data/qwen-runtime-verification-report.json`.
- Generate a short reply and confirm the output WAV is produced by Qwen3-TTS rather than the local development adapter.
- Confirm `data/qwen-runtime-verification-report.json` contains `"status": "passed"` and an existing `output_audio_path`.
- Follow `docs/qwen-runtime-verification.md` before claiming real acoustic cloning/mixing is verified on a target machine.
