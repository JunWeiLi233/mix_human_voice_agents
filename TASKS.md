# TASKS

This file is the handoff point for JunWeiLi233's AI agents. When Codex is close to a usage/session/context limit, update this file before stopping so another agent can continue without guessing.

## Handoff Rule

- Refresh this file before ending a limited session.
- Preferred limit-session command:
  `cd backend; .\.venv\Scripts\python -m app.cli.handoff --tasks ..\TASKS.md`
- Include the latest branch, commit, verification status, running server URL, and unresolved blockers.
- Keep tasks concrete and checkable.
- Do not mark the launch goal complete unless real imported consented voices, saved blend, provider preflight, installed/loadable Qwen runtime, Qwen verification with two profiles, and real Qwen mixed-voice generation are all verified.
- Preserve commit identity: `JunWeiLi233 <mcpejunwei@gmail.com>`.

## Current State

- Branch: `main`
- Remote: `https://github.com/JunWeiLi233/mix_human_voice_agents.git`
- Recent pushed work includes structured launch-manifest voice diagnostics for browser and CLI dry-runs.
- Latest work blocks clipped browser microphone recordings before import and keeps recorded imports inside the launch voice quality requirements.
- Latest handoff work adds a dedicated usage-limit CLI that refreshes launch artifacts, readiness, and a `## Usage Limit Handoff` section in `TASKS.md`.
- Latest cleanup work adds a dry-run-first stale blend prune command so agents can clear old nonmatching blends before creating the real launch blend.
- Latest import hardening rejects too-short reference transcripts across CLI import, browser/API import, and launch-manifest dry-runs before Qwen verification.
- Latest artifact inventory work now requires two distinct launch-usable speaker names before suggesting blend creation, Qwen verification, or Qwen generation commands.
- Current local smoke-test servers: backend `http://127.0.0.1:8001`, frontend `http://127.0.0.1:5176`.

## Usage Limit Handoff

- Last refreshed: `2026-05-23T17:43:29.189679+00:00`
- Reason: Codex usage/session/context limit handoff.
- Next agent should start from `## Next Tasks`, `## Launch Readiness Remaining Tasks`, and `## Launch Artifact Inventory`.
- Preserve commit identity: `JunWeiLi233 <mcpejunwei@gmail.com>`.

## Launch Readiness Remaining Tasks

- Status: `blocked`
- Checked at: `2026-05-23T18:14:08.000439+00:00`

The following tasks are generated from failed launch-readiness checks:
- [ ] imported_voices: Re-record or replace unusable voice samples, then import at least two clean consented WAV voices with matching transcripts.
  Evidence: 1 launch-usable imported voices; 2 imported voices; unusable: voice_93dc1ef39402 has audio quality warnings.
- [ ] saved_blend: Create and save a multi-reference blend from imported voices.
  Evidence: No saved blend references at least two currently imported voices.
- [ ] generated_audio: Generate a Qwen mixed voice clip with imported source details.
  Evidence: 0 Qwen mixed voice clips with imported source details
- [ ] agent_provider: Run Test provider and keep the passed provider verification report.
  Evidence: Run the Agent Provider Test provider preflight before launch.
- [ ] qwen_verification: Run Qwen verification with two imported voices and keep the passed report.
  Evidence: Run python -m app.cli.verify_qwen_runtime with two consented voice profile ids.

Blocking reasons:
- Import at least two consented voice profiles.
- Create and save a mixed voice blend.
- Generate at least one Qwen3-TTS mixed voice clip from imported profiles.
- Test the selected agent provider successfully before launch.
- Run Qwen runtime verification successfully before launch.

## Launch Artifact Inventory

- Voices: `2` total; `1` usable; `1` unusable; `1` distinct usable speakers
- Blends: `280` total; `0` launch-eligible; `280` stale/nonmatching
- Generations: `0` total; `0` Qwen; `0` launch-eligible; `0` stale/nonmatching
- Usable voice IDs: `voice_93f62f27a5b4`
- Usable distinct-speaker voice IDs: `voice_93f62f27a5b4`
- Launch-eligible blend IDs: `none`
- Launch-eligible generation IDs: `none`
- Provider preflight status: `missing`
- Qwen verification status: `missing`
- Qwen runtime: `available` (`Qwen/Qwen3-TTS-12Hz-0.6B-Base`)

Unusable voices:
- `voice_93dc1ef39402` Alice: Audio quality warnings must be resolved before launch.

Stale blend reason summary:
- `280` Blend must reference at least two distinct speaker display names.
- `280` Blend must use the multi_reference_prompt strategy for Qwen launch.
- `280` Blend references voices that are missing or not launch-usable: voice_a, voice_b.

Reviewed prune apply command:
- [ ] `python -m app.cli.prune_launch_artifacts --apply --report data\prune-launch-artifacts-report.json`

Provider preflight command options:
- ChatGPT: `python -m app.cli.verify_agent_provider --provider openai --model gpt-4.1-mini --base-url https://api.openai.com/v1 --api-key <openai-api-key>`
- Claude: `python -m app.cli.verify_agent_provider --provider anthropic --model claude-sonnet-4-5 --base-url https://api.anthropic.com --api-key <anthropic-api-key>`
- Grok: `python -m app.cli.verify_agent_provider --provider xai --model grok-4 --base-url https://api.x.ai/v1 --api-key <xai-api-key>`
- Gemini: `python -m app.cli.verify_agent_provider --provider google --model gemini-2.5-flash --base-url https://generativelanguage.googleapis.com/v1beta --api-key <google-api-key>`
- API: `python -m app.cli.verify_agent_provider --provider openai_compatible --model <model> --base-url <base-url> --api-key <api-key>`
- Local: `python -m app.cli.verify_agent_provider --provider ollama --model llama3.1 --base-url http://127.0.0.1:11434`

Next artifact commands:
- [ ] `python -m app.cli.prune_launch_artifacts --report data/prune-launch-artifacts-report.json`
- [ ] `python -m app.cli.run_launch_sequence --write-template data/launch-sequence/launch-manifest.template.json`

## Completed In Current Working Tree

- Added frontend page navigation for `Studio`, `Evidence`, and `Launch`.
- Kept `Studio` as the default full workflow page.
- Added `Evidence` page for voice records and generation exports.
- Added `Launch` page for readiness, agent provider, and Qwen runtime checks.
- Redesigned the frontend shell with a responsive hero, status summary, page tabs, refined neutral palette, and mobile wrapping fixes.
- Added a frontend test that first failed, then passed, for switching between Studio, Evidence, and Launch pages.
- Added a stricter launch-readiness research gate: `docs/research-review.md` must include `Last checked: YYYY-MM-DD` and that date must be within 45 days before launch.
- Added actionable `Next launch actions` in the launch-readiness panel so agents can convert failed readiness checks into concrete next steps.
- Hardened the launch research gate so a recent source list is not enough; `docs/research-review.md` must also include adopted practices, avoided practices, the architecture decision, and launch requirements from research.
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
- Updated Launch Readiness next actions so the imported-voices blocker points directly to the `run_launch_sequence --write-template` manifest flow.
- Added `/api/launch/manifest-template` and a Launch page download link so browser users can get the same launch manifest template as terminal agents.
- Added `/api/launch/manifest/validate` and a Launch page JSON file validator so browser users can dry-run a filled launch manifest without importing voices or calling providers.
- Added `app.cli.launch_readiness --summary` so terminal agents can print the current launch status, failed checks, evidence, and next actions while refreshing the JSON report and `TASKS.md`.
- Installed the backend Qwen extra into the local venv so `qwen-tts` is importable for the selected Qwen model.
- Stabilized the missing-requirements launch readiness route test so it explicitly simulates an unavailable Qwen runtime instead of depending on local optional packages.
- Added `app.cli.launch_artifacts --summary` so terminal agents can inventory real voice, blend, generation, provider, and Qwen artifacts and get concrete next commands before handoff.
- Added provider-specific preflight commands to `app.cli.launch_artifacts --summary` for ChatGPT/OpenAI, Claude, Grok/xAI, Gemini, generic OpenAI-compatible APIs, and local Ollama.
- Added launch-eligible vs stale blend counts to `app.cli.launch_artifacts --summary` so agents can see when saved blends do not match current imported voices.
- Added per-voice launch usability reasons to `app.cli.launch_artifacts --summary` so agents can see whether consent, transcript, or audio quality blocks an imported voice.
- Hardened launch readiness so the imported-voices check reports launch-usable voice count and unusable voice reasons before Qwen verification.
- Updated launch readiness next actions so unusable imported voices tell agents to re-record or replace bad samples before importing two clean consented WAV voices.
- Added Qwen generation eligibility diagnostics to `app.cli.launch_artifacts --summary` so handoff agents can see launch-ready vs stale/nonmatching generated clips and the reason each stale clip cannot satisfy launch readiness.
- Added `app.cli.launch_artifacts --tasks ..\TASKS.md` so limit-session handoffs can refresh a concrete Launch Artifact Inventory section with usable voice ids, eligible blend/generation ids, provider/Qwen status, stale reasons, and next commands.
- Added a launch checklist to the generated launch manifest template so agents filling it in see the required real clean WAV files, consent, transcript matching, provider selection, and dry-run validation steps.
- Updated `app.cli.run_launch_sequence` so a real manifest run refreshes both launch readiness and launch artifact inventory in `TASKS.md`.
- Added `/api/launch/artifacts` so the frontend can read the same launch artifact inventory that terminal agents use for handoff.
- Added a Launch Artifact Inventory panel to the browser Launch page, showing voice/blend/generation counts, provider and Qwen status, unusable voice reasons, and the next manifest command.
- Added a backend route-test leak guard and isolated the local blend normalization test so pytest no longer creates throwaway blends in the real launch artifact store.
- Added saved-blend audit details in the Blend Mixer so each preset shows its strategy, source count, and normalized voice weights before Qwen generation.
- Added frontend and backend regression coverage for the Launch artifact inventory route and panel.
- Updated launch artifact next commands so agents reuse an existing launch-eligible blend id in the Qwen generation command instead of a placeholder.
- Hardened launch artifact inventory so metadata-only Qwen generations with missing audio are marked stale instead of launch-eligible.
- Hardened launch artifact inventory so zero-byte Qwen generation audio is marked stale instead of launch-eligible.
- Hardened launch artifact inventory so non-parseable Qwen generation audio is marked stale instead of launch-eligible.
- Hardened launch artifact inventory so silent Qwen generation audio is marked stale instead of launch-eligible.
- Hardened launch artifact inventory so Qwen generations missing metadata are marked stale instead of launch-eligible.
- Hardened launch artifact inventory so invalid or mismatched Qwen generation metadata is marked stale instead of launch-eligible.
- Hardened launch artifact inventory so Qwen generation provider traces must match the passed provider preflight.
- Added structured `voice_diagnostics` to launch manifest dry-run reports for clean samples and clipped/warning-blocked samples.
- Updated `/api/launch/manifest/validate` so browser validation can return a failed dry-run report with per-voice diagnostics instead of only an HTTP error string.
- Rendered manifest voice diagnostics in the Launch Readiness panel so users and other agents can see sample duration, sample rate, channels, warnings, and re-record actions.
- Hardened launch readiness so `docs/research-review.md` must include Source Links for OpenAI Voice Agents, Anthropic Claude, Google Gemini, xAI Grok, Ollama/local, LiveKit, Pipecat, and Qwen3-TTS.
- Updated README launch-readiness docs to describe the stricter all-provider research source gate.
- Added browser microphone recording to the Import Voice panel. The UI captures microphone PCM, encodes a mono 16-bit WAV file, and imports the recorded sample through the same consent, transcript, and `/api/voices` path as uploaded files.
- Added recorded sample duration feedback in the Import Voice panel and disabled importing recordings shorter than 5 seconds or longer than 30 seconds.
- Added browser recorder auto-stop at 30 seconds so overlong microphone captures are capped to a launch-valid WAV before import.
- Added a browser recorder audible-signal guard so silent microphone captures are warned and blocked before upload.
- Added a browser recorder clipping guard so full-scale distorted microphone captures are warned and blocked before upload.
- Added `app.cli.handoff` so Codex can refresh `TASKS.md` with launch artifact inventory, readiness blockers, and a usage-limit handoff stamp before a session/context limit.
- Added `app.cli.prune_launch_artifacts` so stale/nonmatching saved blends can be previewed with a dry-run report before optionally deleting them with `--apply`.
- Updated launch artifact handoff to surface a reviewed stale-blend prune apply command only when the dry-run report matches current stale blends.
- Made the Vite dev proxy configurable with `VITE_BACKEND_URL` so the frontend can smoke-test against the current backend when port `8000` is occupied by a stale server.
- Updated the Launch Artifact Inventory panel to show the reviewed stale-blend prune apply command when the current dry-run report matches the current stale blends.
- Added stale-blend cleanup as a launch artifact next command whenever inventory detects nonmatching blends.
- Added shared reference transcript validation requiring at least 5 words for Qwen voice cloning imports and launch manifests.
- Hardened launch artifact inventory and stale-blend pruning so launch-eligible blends and next commands require at least two distinct usable speaker display names.
- Updated the frontend Launch Artifact Inventory panel to show distinct usable speaker counts and distinct-speaker voice IDs.
- Hardened stale-blend prune reports so dry-runs include each stale blend's name, source voice ids, and stale reasons before any delete is applied.
- Updated the frontend Launch Artifact Inventory panel to render stale blend names and stale reasons from the backend launch artifact report.
- Added stale blend reason counts to the launch artifact report and `TASKS.md` handoff so agents can see why stale blends should be pruned.
- Updated the frontend Launch Artifact Inventory panel to show aggregate stale blend reason counts before detailed stale blend rows.
- Updated the frontend Launch Artifact Inventory panel to show ChatGPT, Claude, Grok, Gemini, API, and local provider preflight commands from the artifact report.
- Updated the generated `TASKS.md` Launch Artifact Inventory handoff to include ChatGPT, Claude, Grok, Gemini, API, and local provider preflight command options.
- Added a reviewed apply command to stale blend prune dry-run reports so agents can inspect the report before deleting stale blends.

## Verification Already Run

- `cd backend; .\.venv\Scripts\python -m pytest tests\test_handoff_cli.py -q` first failed because `app.cli.handoff` was missing, then passed after adding the usage-limit handoff CLI.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_handoff_cli.py -q` caught and verified fixes for Markdown section replacement edge cases in `TASKS.md`.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_cli.py -q -k "real_section_heading"` passed after fixing readiness TASKS section matching.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q -k "real_section_heading"` passed after fixing artifact TASKS section matching.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 283 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.handoff --tasks ..\TASKS.md --no-summary` refreshed usage-limit handoff, launch readiness, and artifact inventory sections without duplicate headings.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_prune_launch_artifacts_cli.py -q` first failed because `app.cli.prune_launch_artifacts` was missing, then passed after adding the dry-run-first cleanup command.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q -k "separates_launch"` first failed because stale-blend cleanup was missing from artifact next commands, then passed after adding it.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_prune_launch_artifacts_cli.py tests\test_launch_artifacts_cli.py -q` passed: 8 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.prune_launch_artifacts --report data\prune-launch-artifacts-report.json` dry-ran stale blend cleanup and reported 268 stale blends would be deleted, with no deletions.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 285 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.handoff --tasks ..\TASKS.md --no-summary` refreshed usage-limit handoff, launch readiness, and artifact inventory with the prune command.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_import_voice_cli.py -q -k "too_short"` first failed because one-word reference transcripts were importable, then passed after adding shared transcript validation.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_routes.py -q -k "too_short"` first failed because the browser/API import accepted one-word transcripts, then passed after adding shared transcript validation.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q -k "short_reference"` first failed because launch manifest dry-run accepted one-word transcripts, then passed after adding shared transcript validation.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 288 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.handoff --tasks ..\TASKS.md --no-summary` refreshed usage-limit handoff, launch readiness, and artifact inventory after transcript validation.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q -k "distinct_usable"` first failed because artifact inventory suggested launch commands for two profiles with the same speaker name, then passed after adding distinct-speaker selection.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py tests\test_prune_launch_artifacts_cli.py -q` passed: 9 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 289 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.handoff --tasks ..\TASKS.md --no-summary` refreshed usage-limit handoff, launch readiness, and artifact inventory with distinct usable speaker counts.
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
- `cd frontend; npm test -- --run -t "renders the mixed voice studio"` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_routes.py tests\test_run_launch_sequence_cli.py -q -k "manifest"` passed: 8 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 267 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_cli.py -q -k "actionable_summary"` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` printed the actionable launch summary, refreshed readiness tasks, and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_cli.py -q` passed: 4 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 268 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m pip install -e ".[qwen]"` installed `qwen-tts==0.1.1`, `torch==2.12.0`, and `torchaudio==2.11.0` into the local backend venv.
- `cd backend; .\.venv\Scripts\python -c "from app.tts.qwen import QwenTtsAdapter; print(QwenTtsAdapter.runtime_status().model_dump())"` reported `available: True` for `Qwen/Qwen3-TTS-12Hz-0.6B-Base`.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` now reports `[x] Qwen runtime`, refreshes readiness tasks, and still exits 1 until the remaining real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_routes.py -q -k "launch_readiness_reports_blockers_when_requirements_are_missing"` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 268 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_routes.py tests\test_run_launch_sequence_cli.py -q -k "manifest_template"` passed: 2 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.run_launch_sequence --write-template data\launch-sequence\launch-manifest.template.json --report data\launch-sequence\template-report.json` passed.
- `cd frontend; npm test -- --run -t "renders the mixed voice studio"` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 266 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q -k "template"` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q` passed: 29 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.run_launch_sequence --write-template data\launch-sequence\launch-manifest.template.json --report data\launch-sequence\template-report.json` passed and wrote the manifest skeleton.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 264 tests.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_core.py -q -k "manifest_template"` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_cli.py tests\test_launch_readiness_core.py -q` passed: 78 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 265 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 269 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --summary` passed and reported 1 voice, 245 blends, 0 generations, and the launch manifest template command as the next step.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks, reported `[x] Qwen runtime`, and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 269 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --summary` passed and printed provider preflight options for ChatGPT, Claude, Grok, Gemini, generic API, and local Ollama. It reported 1 voice, 246 blends, 0 generations, and the launch manifest template command as the next step.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks, reported `[x] Qwen runtime`, and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q` passed: 2 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 270 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --summary` passed and reported 1 voice, 247 blends, 0 launch-eligible blends, 247 stale/nonmatching blends, 0 generations, and the launch manifest template command as the next step.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks, reported `[x] Qwen runtime`, and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q` passed: 3 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 271 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --summary` passed and reported 1 voice, 0 usable voices, 1 unusable voice blocked by audio quality warnings, 248 stale/nonmatching blends, and 0 generations.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks, reported `[x] Qwen runtime`, and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_core.py -q -k "imported_voices_from_same_speaker_before_qwen_verification or launch_usable_voice_count"` passed: 2 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 272 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --summary` passed and reported 1 voice, 0 usable voices, 1 unusable voice blocked by audio quality warnings, 249 stale/nonmatching blends, and 0 generations.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and now reports `[ ] Imported voices: 0 launch-usable imported voices; 1 imported voices; unusable: voice_93dc1ef39402 has audio quality warnings.`
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_core.py -q -k "next_action_calls_out_unusable_imported_voices"` passed: 1 test.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 273 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --summary` passed and reported 1 voice, 0 usable voices, 1 unusable voice blocked by audio quality warnings, 250 stale/nonmatching blends, and 0 generations.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and now prints `Next: Re-record or replace unusable voice samples, then import at least two clean consented WAV voices with matching transcripts.`
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q -k "stale_qwen_generations"` first failed with missing `qwen_generation_count`, then passed after adding generation eligibility diagnostics.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q` passed: 4 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --summary` passed and reported 1 voice, 0 usable voices, 1 unusable voice blocked by audio quality warnings, 250 stale/nonmatching blends, 0 Qwen launch-eligible generations, and 0 stale/nonmatching generations.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 274 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q -k "updates_tasks_handoff"` first failed because `--tasks` was unrecognized, then passed after adding the artifact TASKS handoff writer.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_artifacts_cli.py -q` passed: 5 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 251 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 275 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_routes.py -q -k "launch_artifacts_route"` passed: 1 test.
- `cd frontend; npm test -- --run -t "switches between"` first failed because the Launch Artifact Inventory was not rendered, then passed after adding the API route, frontend fetch, component, and Launch page wiring.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 276 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 255 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q -k "dry_run_validates_manifest_without_side_effects or rejects_clipped_reference_audio"` first failed because `voice_diagnostics` was absent, then passed after adding structured dry-run diagnostics.
- `cd frontend; npm test -- --run -t "renders the mixed voice studio"` first failed because manifest voice diagnostics were not rendered, then passed after adding the Launch Readiness diagnostics UI.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_routes.py -q -k "launch_manifest_validation_route"` passed: 2 tests.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 277 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 256 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- GitHub Actions CI for `feat: require provider research sources` passed: backend tests and frontend tests/build.
- Verified current primary source links in browser: OpenAI Voice Agents, Anthropic Messages, Google Gemini OpenAI compatibility, xAI Chat Completions, Ollama OpenAI compatibility, LiveKit Voice AI quickstart, Pipecat introduction, and Qwen3-TTS.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_core.py -q -k "provider_source_links"` first failed because provider source links were not required, then passed after hardening the gate.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_launch_readiness_core.py -q -k "research_review"` passed: 4 tests.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_routes.py -q -k "ready_after_full_qwen_verification"` passed after updating the launch-ready fixture to include the provider links.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 278 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 258 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd frontend; npm test -- --run -t "record a consented"` first failed because the Import Voice panel had no recorder controls, then passed after adding browser WAV recording.
- `cd frontend; npm test -- --run` passed: 8 tests.
- `cd frontend; npx tsc --noEmit` passed after fixing the mocked `AudioProcessingEvent` cast in the new recorder test helper.
- `cd frontend; npm run build` passed.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 278 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 261 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd frontend; npm test -- --run -t "recorded samples|record a consented"` first failed because recorded sample duration was not shown or gated, then passed after adding the 5-30 second recorder gate.
- `cd frontend; npm test -- --run -t "browser recordings|recorded samples|record a consented"` first failed because browser recordings did not auto-stop at 30 seconds, then passed after capping recorded PCM and finalizing automatically.
- `cd frontend; npm test -- --run -t "silent browser|browser recordings|recorded samples|record a consented"` first failed because silent browser recordings were importable, then passed after adding a recorded peak-amplitude guard.
- `cd frontend; npm test -- --run -t "clipped browser|silent browser|browser recordings|recorded samples|record a consented"` first failed because clipped browser recordings were importable, then passed after adding a recorded max-peak guard.
- `cd frontend; npm test -- --run` passed: 9 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 278 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 262 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd frontend; npm test -- --run` passed: 10 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 278 tests.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 263 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd frontend; npm test -- --run` passed: 11 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 278 tests.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 264 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd frontend; npm test -- --run` passed: 12 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 278 tests.
- `git diff --check` passed with line-ending normalization warnings only.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 265 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q -k "invokes_launch_steps"` first failed because `launch_artifacts_main` was not wired into the sequence, then passed after adding the artifact handoff refresh call.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q` passed: 29 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 253 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 275 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q -k "writes_manifest_template"` first failed because `launch_checklist` was missing, then passed after adding the checklist to `launch_manifest_template()`.
- `cd backend; .\.venv\Scripts\python -m app.cli.run_launch_sequence --write-template data\launch-sequence\launch-manifest.template.json --report data\launch-sequence\template-report.json` passed and regenerated the launch manifest template from source.
- `cd backend; .\.venv\Scripts\python -m pytest tests\test_run_launch_sequence_cli.py -q -k "template or dry_run"` passed: 19 tests.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary` refreshed the Launch Artifact Inventory and reported 1 voice, 0 usable voices, 252 stale/nonmatching blends, 0 generations, and the launch manifest template command.
- `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary` refreshed readiness tasks and still exits 1 until real launch artifacts are present.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 275 tests.
- `cd frontend; npm test -- --run` passed: 7 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.

## Next Tasks

1. Start by checking the current branch and working tree:
   `git status --short --branch`
2. Refresh launch artifact inventory and readiness before further launch work:
   `cd backend; .\.venv\Scripts\python -m app.cli.launch_artifacts --report data\launch-artifacts-report.json --tasks ..\TASKS.md --summary`
   `cd backend; .\.venv\Scripts\python -m app.cli.launch_readiness --report data\launch-readiness-report.json --tasks ..\TASKS.md --summary`
3. Re-run frontend verification after any frontend edits:
   `cd frontend; npm test -- --run`
   `cd frontend; npx tsc --noEmit`
   `cd frontend; npm run build`
4. Re-run backend tests after any backend edits:
   `cd backend; .\.venv\Scripts\python -m pytest -q`
5. Before future commits, audit Git identity:
   `git config user.name`
   `git config user.email`
   `git var GIT_AUTHOR_IDENT`
   `git var GIT_COMMITTER_IDENT`
6. Commit future work as `JunWeiLi233 <mcpejunwei@gmail.com>` and push to `main`.
7. Audit the latest commit identity after commit:
   `git show -s --format="%h %an <%ae> | %cn <%ce> | %s" HEAD`
8. Watch GitHub Actions for any pushed commit until it finishes.
