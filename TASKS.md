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
