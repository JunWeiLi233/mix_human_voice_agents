# TASKS

This file is the handoff point for JunWeiLi233's AI agents. When Codex is close to a usage/session/context limit, update this file before stopping so another agent can continue without guessing.

## Handoff Rule

- Refresh this file before ending a limited session.
- Include the latest branch, commit, verification status, running server URL, and unresolved blockers.
- Keep tasks concrete and checkable.
- Do not mark the launch goal complete unless real imported consented voices, saved blend, provider preflight, installed/loadable Qwen runtime, Qwen verification with two profiles, and real Qwen mixed-voice generation are all verified.
- Preserve commit identity: `JunWeiLi233 <mcpejunwei@gmail.com>`.

## Current State

- Branch: `main`
- Remote: `https://github.com/JunWeiLi233/mix_human_voice_agents.git`
- Frontend UI page work has been committed and pushed.
- Local Vite dev server for review: `http://127.0.0.1:5174/`
- Backend launch readiness is still blocked because the repo does not yet have real imported voices, a saved real blend, installed/loadable Qwen runtime verification, or real Qwen mixed-voice output.

## Completed In Current Working Tree

- Added frontend page navigation for `Studio`, `Evidence`, and `Launch`.
- Kept `Studio` as the default full workflow page.
- Added `Evidence` page for voice records and generation exports.
- Added `Launch` page for readiness, agent provider, and Qwen runtime checks.
- Redesigned the frontend shell with a responsive hero, status summary, page tabs, refined neutral palette, and mobile wrapping fixes.
- Added a frontend test that first failed, then passed, for switching between Studio, Evidence, and Launch pages.
- Added a stricter launch-readiness research gate: `docs/research-review.md` must include `Last checked: YYYY-MM-DD` and that date must be within 45 days before launch.
- Added actionable `Next launch actions` in the launch-readiness panel so agents can convert failed readiness checks into concrete next steps.
- Added `app.cli.launch_readiness --tasks ..\TASKS.md` so readiness failures can refresh this handoff file automatically before a usage/session limit.
- Hardened provider URL handling so Claude accepts `https://api.anthropic.com` or `https://api.anthropic.com/v1`, and Local accepts `http://127.0.0.1:11434` or `http://127.0.0.1:11434/api`.
- Added structured `next_actions` to launch-readiness reports and made the UI render those backend-provided actions.
- Added `app.cli.verify_agent_provider` so terminal agents can create the persisted provider preflight report required by launch readiness.
- Added `app.cli.import_voice` so terminal agents can import consented WAV voice profiles with matching transcripts into the same local storage as the UI.
- Added `app.cli.create_blend` so terminal agents can save a multi-reference blend from imported voice profile ids.
- Added `app.cli.generate_voice` so terminal agents can create a Qwen mixed-voice generation from a saved blend after provider and Qwen verification pass.
- Added `app.cli.run_launch_sequence` so terminal agents can run import, blend, provider preflight, Qwen verification, Qwen generation, and readiness refresh from one JSON manifest.
- Hardened `app.cli.run_launch_sequence` so it fails if the final launch-readiness audit remains blocked.
- Hardened `app.cli.run_launch_sequence` so it validates manifest audio paths before importing any voices.
- Hardened `app.cli.run_launch_sequence` so manifest audio must be parseable WAV with audible signal before any import starts.
- Hardened `app.cli.run_launch_sequence` so the launch manifest must name at least two distinct speakers before any import starts.
- Added `app.cli.run_launch_sequence --dry-run` so agents can validate manifest voices, WAV files, provider fields, and prompts without importing voices or calling providers.
- Hardened launch readiness so passed agent-provider and Qwen verification reports expire after 7 days.
- Hardened `app.cli.generate_voice` so it refuses Qwen verification reports that launch readiness would reject before calling the LLM or Qwen adapter.
- Hardened `app.cli.run_launch_sequence` so launch manifests reject unsupported agent provider names during dry-run validation.
- Hardened `app.cli.run_launch_sequence` so launch manifests reject nonpositive or nonnumeric voice blend weights before any import starts.
- Hardened `app.cli.run_launch_sequence` so Qwen launch manifests reject non-`multi_reference_prompt` blend strategies before any import starts.
- Hardened `app.cli.run_launch_sequence` so launch manifests reject blank supplied `qwen.text` before any import starts.
- Hardened launch readiness so `docs/research-review.md` must include primary source links for OpenAI Voice Agents, LiveKit Voice AI, Pipecat, and Qwen3-TTS.
- Hardened launch readiness so metadata-only Qwen generations report a missing generated audio artifact directly.
- Hardened `app.cli.run_launch_sequence` so launch manifests reject blank supplied `agent_provider.prompt` before any import starts.
- Hardened `app.cli.run_launch_sequence` so launch manifests reject blank supplied Qwen runtime options before any import starts.
- Hardened `app.cli.run_launch_sequence` so launch manifests reject blank supplied `blend.name` before any import starts.
- Hardened `app.cli.run_launch_sequence` so malformed non-object voice entries fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so malformed non-object `blend`, `agent_provider`, `generation`, and `qwen` sections fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so non-object JSON manifests fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so non-array `voices` manifests fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so malformed non-string required agent provider fields fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so malformed non-string voice text fields, generation prompts, and Qwen text fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so malformed non-string blend strategies fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so malformed non-string optional voice notes and provider command fields fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so reference audio shorter than 5 seconds or longer than 30 seconds fails with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence` so clipped reference audio quality warnings fail with a structured report before any import starts.
- Hardened `app.cli.run_launch_sequence --dry-run` so unsafe consent claims fail with a structured report before any import starts.
- Hardened `app.cli.generate_voice` so requested Qwen runtime options that mismatch verification fail before agent provider or Qwen adapter calls.
- Hardened `app.cli.run_launch_sequence --dry-run` so unsafe generation/provider prompts fail with a structured report before imports or provider calls.
- Hardened `app.cli.verify_qwen_runtime` and launch dry-run validation so unsafe Qwen verification text fails before profile loading or Qwen calls.
- Hardened `app.cli.import_voice` so clipped reference audio is rejected before a voice profile is saved.
- Hardened the `/api/voices` UI import path so clipped reference audio is rejected before a voice profile is saved.
- Hardened `app.cli.create_blend` so terminal blends require at least two distinct speaker display names before saving.
- Hardened `/api/tts/qwen/verification` so unsafe verification text fails before loading voice profiles or Qwen.
- Hardened `/api/blends` so Qwen mixed-voice blends require saved imported profiles from at least two distinct speaker display names before saving.
- Hardened launch readiness so pre-verification imported voices and saved blends must represent at least two distinct speaker display names.
- Hardened Qwen runtime status so launch readiness reports the `QWEN_TTS_MODEL_ID` environment model when no explicit model id is supplied.
- Hardened Qwen verification in both CLI and API paths so passed verification output must be stored under `data/generations`.
- Hardened launch readiness so verified imported voice ids must still resolve to at least two distinct current speaker display names.
- Hardened launch readiness so persisted passed agent-provider reports are rejected if the stored reply fails the voice safety gate.
- Hardened launch readiness so persisted Qwen mixed-voice generation prompt and reply metadata must still pass the voice safety gate.
- Hardened launch readiness so persisted Qwen verification text must still pass the voice safety gate.
- Hardened launch readiness so verified imported voice audio must still live under the managed `data/voices/<id>` profile storage.
- Hardened voice profile listing so malformed profile metadata is ignored instead of crashing launch readiness.
- Hardened blend listing so malformed blend metadata is ignored instead of crashing launch readiness.
- Hardened voice deletion cleanup so malformed blend or generation metadata is ignored while valid references are still removed.
- Persisted non-secret frontend agent provider settings so user-selected API/local LLM endpoint, model, provider, and system prompt survive reloads without storing API keys.
- Added generated-clip blend traceability so audio metadata and history show the saved blend id/name that produced each mixed voice clip.
- Hardened launch readiness so Qwen generated clips must reference a current saved blend whose name, strategy, and source weights match the generated metadata.
- Hardened the `/api/generate` Qwen path so it rejects unsaved or stale blend payloads before loading voice profiles or Qwen.
- Added `app.cli.run_launch_sequence --write-template` so another agent can generate a launch manifest skeleton before filling in real consented voice files and provider details.

## Verification Already Run

- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- Chrome headless desktop screenshot was captured from `http://127.0.0.1:5174/`.
- Chrome headless mobile screenshot was captured and mobile clipping was fixed.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 262 tests.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_storage.py -q` passed: 10 tests.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_generation.py -q` passed: 14 tests.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_core.py -q -k "without_matching_saved_blend or generation_metadata or generated_audio"` passed: 3 tests.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_routes.py -q` passed: 70 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 263 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q -k "template"` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q` passed: 29 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.run_launch_sequence --write-template data\launch-sequence\launch-manifest.template.json --report data\launch-sequence\template-report.json` passed and wrote the manifest skeleton.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 264 tests.

## Next Tasks

1. Re-run frontend verification after any further edits:
   `cd frontend; npm test -- --run`
2. Re-run TypeScript and production build:
   `cd frontend; npx tsc --noEmit`
   `cd frontend; npm run build`
3. Re-run backend tests after any backend edits:
   `cd backend; .\.venv\Scripts\python -m pytest -q`
4. Audit Git identity before commit:
   `git config user.name`
   `git config user.email`
   `git var GIT_AUTHOR_IDENT`
   `git var GIT_COMMITTER_IDENT`
5. Commit as `JunWeiLi233 <mcpejunwei@gmail.com>` and push to `main`.
6. Audit the latest commit identity after commit:
   `git show -s --format="%h %an <%ae> | %cn <%ce> | %s" HEAD`
7. Watch GitHub Actions for the pushed commit until it finishes.

## Launch Readiness Remaining Tasks

- Status: `blocked`
- Checked at: `2026-05-23T14:27:48.080258+00:00`

The following tasks are generated from failed launch-readiness checks:
- [ ] imported_voices: Import two consented WAV voice samples with matching transcripts.
  Evidence: 1 imported voices
- [ ] saved_blend: Create and save a multi-reference blend from imported voices.
  Evidence: No saved blend references at least two currently imported voices.
- [ ] generated_audio: Generate a Qwen mixed voice clip with imported source details.
  Evidence: 0 Qwen mixed voice clips with imported source details
- [ ] agent_provider: Run Test provider and keep the passed provider verification report.
  Evidence: Run the Agent Provider Test provider preflight before launch.
- [ ] qwen_runtime: Install and load qwen-tts with the selected Qwen model.
  Evidence: qwen-tts is not installed. Run: python -m pip install -e ".[qwen]"
- [ ] qwen_verification: Run Qwen verification with two imported voices and keep the passed report.
  Evidence: Run python -m app.cli.verify_qwen_runtime with two consented voice profile ids.

Blocking reasons:
- Import at least two consented voice profiles.
- Create and save a mixed voice blend.
- Generate at least one Qwen3-TTS mixed voice clip from imported profiles.
- Test the selected agent provider successfully before launch.
- Install and load the Qwen3-TTS runtime before launch.
- Run Qwen runtime verification successfully before launch.
