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

## Verification Already Run

- `cd frontend; npm test -- --run` passed: 6 tests.
- `cd frontend; npx tsc --noEmit` passed.
- `cd frontend; npm run build` passed.
- Chrome headless desktop screenshot was captured from `http://127.0.0.1:5174/`.
- Chrome headless mobile screenshot was captured and mobile clipping was fixed.
- `cd backend; .\.venv\Scripts\python -m pytest -q` passed: 194 tests.

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
- Checked at: `2026-05-23T05:51:59.743741+00:00`

The following tasks are generated from failed launch-readiness checks:
- [ ] imported_voices: Import two consented WAV voice samples with matching transcripts.
  Evidence: 0 imported voices
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
