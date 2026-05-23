# Mixed Voice Agent Research Review

Date: 2026-05-22
Status: Launch prerequisite

## Research Question

How are current programmers building voice agents and voice-cloning tools, and what should this app borrow or avoid when turning that practice into a multiple-person mixed voice agent?

## Sources Reviewed

| Source | Current pattern | Impact on this app |
| --- | --- | --- |
| OpenAI Voice Agents docs | Splits voice-agent architecture into live speech-to-speech sessions and chained speech-to-text, agent reasoning, and text-to-speech pipelines. Realtime sessions fit low-latency barge-in; chained pipelines fit explicit control, durable transcripts, and guardrails. | Keep this MVP as a chained pipeline so imported profiles, consent, blend metadata, safety checks, and TTS adapter behavior stay inspectable. Realtime transport can be a later shell around the same voice-profile and blend services. |
| LiveKit Agents docs | Supports both STT-LLM-TTS pipelines and realtime speech-to-speech models. Starter projects emphasize complete agent servers, testing, model selection, and production startup modes. | Preserve provider-neutral boundaries: the selected LLM and selected TTS backend should be swappable without changing voice profile storage or blend logic. |
| Pipecat docs | Models production voice apps as a client plus server-side pipeline that processes audio, runs LLMs, and generates speech in real time. | Treat the studio as the same pipeline shape, but with typed text input first. The later microphone/realtime path should reuse orchestration rather than bypass it. |
| Qwen3-TTS docs and technical report | Voice cloning takes reference audio plus transcript, can reuse clone prompts, and supports short-reference cloning and description-based voice design. | Store reference transcripts with every imported profile, require at least two selected profiles for Qwen verification, and keep Qwen behind an adapter that can build per-profile clone prompts. |
| F5-TTS repository | Local voice cloning workflows pass reference audio and reference text, with ASR as a helper when reference text is missing. | Keep the profile schema model-neutral: source audio plus transcript should be usable by future Qwen, F5, Fish, or other adapter implementations. |
| Fish Audio voice-cloning docs | Separates direct reference-audio cloning from persistent reusable voice models, recommends clean 10-30 second references, matching transcript text, and audio normalization. | Keep local voice profiles as reusable artifacts, reject low-quality imports, preserve exact reference text, and document 5-30 second WAV requirements. |
| Dia repository docs | Builds dialogue with speaker tags and audio prompts; it is useful for multi-speaker dialogue, but not a guaranteed arbitrary weighted speaker-blend engine. | Do not equate multi-speaker dialogue with one blended speaker identity. Future Dia-style adapters should be labeled as dialogue or segment strategies unless they prove weighted blending. |

## Practices To Adopt

- Use a chained local-first architecture for launch: import, consent, quality analysis, profile storage, blend creation, LLM reply, safety check, TTS synthesis, metadata, playback/history.
- Keep LLM provider selection independent from TTS. The app should work with ChatGPT/OpenAI, Claude/Anthropic, Gemini/Google, Grok/xAI, OpenAI-compatible APIs, and Ollama-compatible local endpoints through one agent interface.
- Keep TTS model integration behind adapters. Each adapter must declare or encode the blend strategy it actually implements instead of pretending all models can interpolate speakers identically.
- Persist reference transcripts with profiles because Qwen3-TTS, Fish-style cloning, F5-style cloning, and Dia-style prompting all depend on prompt text or benefit from it.
- Treat reusable profile artifacts as first-class local data. Direct references are useful for tests and one-off synthesis, but saved profiles are better for a repeatable mixed-voice agent.
- Require launch-time evidence: automated tests, provider preflight, real TTS runtime report, generated audio metadata, and source-profile traceability.

## Practices To Avoid

- Do not build the MVP as a pure realtime speech-to-speech app. It would hide too much of the consent, transcript, profile, blend, and metadata workflow.
- Do not claim a true acoustic mixed identity from a backend until that backend has produced and verified audio from at least two consented imported profiles.
- Do not treat multi-speaker dialogue as weighted voice blending. Dialogue engines can alternate speakers; this product needs one synthetic mixed voice label and source weights.
- Do not send imported voices to a cloud provider by default. Voice samples should remain local unless the user explicitly chooses a cloud backend and understands the privacy impact.
- Do not launch with only a UI preflight. Readiness must check persisted provider verification and persisted TTS runtime verification.

## Architecture Decision

The launch architecture remains a local-first chained pipeline:

```text
consented WAV import
  -> audio quality validation
  -> local voice profile + transcript storage
  -> weighted blend preset
  -> provider-neutral LLM reply
  -> safety gate
  -> adapter-selected mixed voice synthesis
  -> synthetic metadata + playback/history
```

This matches current production voice-agent practice while preserving the specific controls required for a multiple-person mixed voice.

## Launch Requirements From Research

- Each imported voice must have self or written-permission consent, a matching transcript, and quality metadata.
- Blends must require at least two distinct imported profiles and persist normalized source weights.
- Generated metadata must include `synthetic_label`, `source_profile_ids`, normalized `source_profiles`, `blend_strategy`, `agent_trace`, and synthetic disclosure.
- Launch readiness must stay blocked until the selected agent provider preflight and Qwen runtime verification have both produced persisted passed reports.
- Real acoustic cloning/mixing remains unverified until `docs/qwen-runtime-verification.md` is completed on a machine with the Qwen runtime and consented samples installed.

## Source Links

- OpenAI Voice Agents: https://platform.openai.com/docs/guides/voice-agents
- LiveKit Voice AI quickstart: https://docs.livekit.io/agents/start/voice-ai/
- Pipecat introduction: https://docs.pipecat.ai/overview/introduction
- Qwen3-TTS repository: https://github.com/QwenLM/Qwen3-TTS
- Qwen3-TTS technical report: https://arxiv.org/abs/2601.15621
- F5-TTS repository: https://github.com/SWivid/F5-TTS
- Fish Audio voice cloning: https://docs.fish.audio/developer-guide/sdk-guide/javascript/voice-cloning
- Dia repository: https://github.com/nari-labs/dia
