# Mixed Voice Agent Design

Date: 2026-05-22
Status: Approved design direction, pending user review of this written spec

## Objective

Design an AI agent that lets a user import voice samples from multiple people, create a controlled mixed voice from those imported voices, and use that mixed voice as the speaking voice for an agent. The design is based on current voice-agent practice, recent open-source voice cloning work, and launch-time safety requirements.

## Research Summary

Current voice-agent systems usually use one of two architectures:

1. Realtime speech-to-speech agents. OpenAI Realtime API and the OpenAI Agents SDK use `RealtimeAgent` and `RealtimeSession` for low-latency browser voice agents. Browser clients typically connect over WebRTC with a short-lived ephemeral token created by a backend. This is best for live conversation, interruptions, and natural turn-taking.
2. Chained voice pipelines. LiveKit, Pipecat, Vocode, and similar frameworks compose speech-to-text, LLM reasoning, text-to-speech, turn detection, tool calls, traces, and handoffs. This is more controllable, easier to debug, and better suited to custom voice generation.

For imported and mixed voices, open-source voice tools are converging around local voice profile workflows. Projects and models such as Qwen3-TTS, F5-TTS, Dia, Fish Speech, VibeVoice, Voicebox, and Qwen voice studios commonly import short reference clips, extract or reuse voice prompts, and synthesize speech from those profiles. Some systems support multi-speaker dialogue directly; fewer expose reliable arbitrary speaker blending. Because true speaker-embedding interpolation differs by backend, this product should treat voice mixing as a first-class product workflow with backend-specific adapters instead of assuming every TTS model blends voices the same way.

Key sources reviewed:

- OpenAI voice agents: https://platform.openai.com/docs/guides/voice-agents
- OpenAI Agents SDK voice guide: https://openai.github.io/openai-agents-js/guides/voice-agents/
- OpenAI Realtime Agents examples: https://github.com/openai/openai-realtime-agents
- LiveKit Agents: https://docs.livekit.io/agents/
- Pipecat: https://docs.pipecat.ai/
- Vocode: https://docs.vocode.dev/
- Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS
- F5-TTS: https://github.com/SWivid/F5-TTS
- Dia: https://github.com/nari-labs/dia
- Fish Speech: https://github.com/fishaudio/fish-speech
- Voicebox: https://voicebox.sh/

## Product Scope

The first launch is a local-first mixed-voice agent studio. It should prove the imported voice profile and blend workflow before optimizing for live low-latency calls.

In scope for MVP:

- Import two or more voice samples.
- Create a reusable voice profile for each imported person.
- Record consent metadata for every imported voice.
- Analyze sample quality before allowing a profile to be used.
- Create a weighted voice blend, for example 50% Voice A, 30% Voice B, 20% Voice C.
- Generate agent replies using the selected blend.
- Preview and export generated audio.
- Store voice profiles, blends, generation history, and consent metadata locally.
- Label generated output as synthetic.

Out of scope for MVP:

- Phone calls.
- Public voice marketplace.
- Celebrity or public-figure cloning.
- Real-time WebRTC conversation with the custom mixed voice.
- Guaranteed exact acoustic identity preservation across every TTS backend.
- Training a new foundation TTS model.

## Recommended Architecture

Use a chained local-first architecture for the MVP:

```text
User audio import
  -> consent gate
  -> audio preprocessing
  -> voice profile extraction
  -> voice blend editor
  -> agent text response
  -> mixed voice synthesis
  -> playback/export/history
```

This architecture is recommended because mixed voice synthesis needs control over preprocessing, profile storage, TTS adapter behavior, consent state, quality checks, and export labeling. A pure Realtime API speech-to-speech app would be faster for live conversation but would not solve imported multi-person voice blending cleanly.

## Components

### Desktop/Web UI

The UI is a studio-style application with these views:

- Voice Library: imported people, consent status, quality status, sample previews.
- Import Wizard: upload/record sample, confirm consent, run quality analysis, name the profile.
- Blend Mixer: choose profiles, adjust weights, save blend presets, preview sample text.
- Agent Chat: text or microphone input, transcript, generated reply, voice playback.
- History: generated clips, source blend, model/backend used, export controls.
- Settings: user-selected agent provider, API key or local endpoint, local model path, storage location, safety settings.

### Agent Core

The agent core owns conversation state and response generation. MVP can start with text input plus optional STT. The agent returns text that is passed to the mixed voice synthesis engine.

The agent should be designed so a future realtime transport can replace the input/output shell without changing voice profile storage or blend logic.

The agent backend must be user-configurable. Users should be able to choose between an API-hosted LLM and a local LLM endpoint. The MVP should support an OpenAI-compatible chat API configuration and an Ollama-compatible local configuration, with a provider-neutral interface so more providers can be added without changing the voice profile or TTS pipeline.

### Voice Profile Service

The voice profile service owns:

- Imported source audio.
- Cleaned reference audio.
- Transcription of reference audio when required by the TTS backend.
- Speaker embedding or backend-specific voice prompt artifacts.
- Consent metadata.
- Quality metadata.

Voice profiles should be immutable by default after extraction. If the user imports better samples, the app creates a new profile version.

### Blend Engine

The blend engine owns the product-level mixed voice abstraction:

```json
{
  "id": "blend_001",
  "name": "Warm Trio",
  "profiles": [
    { "voiceProfileId": "voice_a", "weight": 0.5 },
    { "voiceProfileId": "voice_b", "weight": 0.3 },
    { "voiceProfileId": "voice_c", "weight": 0.2 }
  ],
  "strategy": "adapter_embedding_mix",
  "createdAt": "2026-05-22T00:00:00Z"
}
```

The blend engine should support multiple strategies:

- `adapter_embedding_mix`: use a backend that exposes speaker embeddings or x-vectors and interpolate normalized embeddings.
- `multi_reference_prompt`: pass multiple references to a backend that supports multi-reference cloning.
- `segment_ensemble`: synthesize multiple versions, then blend or choose stable segments. This is slower but useful as a fallback.
- `designed_voice_proxy`: generate a synthetic voice description from the imported voices and create a new designed voice. This is less faithful and must be clearly labeled.

Each generated clip must record which strategy was used.

### TTS Adapter Layer

Create a backend-neutral interface so the product does not depend on one model:

```text
prepareVoiceProfile(sourceAudio, options) -> VoiceProfileArtifact
synthesize(text, voiceProfileOrBlend, options) -> AudioClip
estimateCapabilities() -> BackendCapabilities
```

Candidate adapters:

- Qwen3-TTS adapter for local voice cloning and future streaming experiments.
- F5-TTS adapter for reference-audio cloning with transcript support.
- Dia or VibeVoice adapter for multi-speaker dialogue generation.
- OpenAI TTS or Realtime adapter for non-cloned fallback agent voices only.

The MVP should start with one local adapter and keep the interface ready for more.

### Audio Processing

Preprocessing should include:

- Convert to a standard WAV format.
- Trim silence.
- Normalize loudness.
- Detect clipping.
- Detect long silence or music/background noise.
- Estimate duration.
- Optionally transcribe reference audio.

Quality checks should guide the user toward clean 5-30 second samples with one speaker, minimal background noise, and no overlapping speech.

### Storage

Use local storage for launch:

```text
data/
  voices/
    <voiceProfileId>/
      source.wav
      cleaned.wav
      consent.json
      profile.json
      artifacts/
  blends/
    <blendId>.json
  generations/
    <generationId>/
      output.wav
      metadata.json
```

The app should not upload imported voice samples unless the user explicitly chooses a cloud backend and sees the privacy impact.

## Safety And Consent

Voice cloning and mixing can enable impersonation. The product must include launch-time controls instead of treating safety as a later feature.

Required MVP safeguards:

- Each imported voice requires an explicit consent confirmation.
- Store who confirmed consent, when, and the allowed use scope.
- Block or warn against public figures, celebrities, politicians, and non-consenting third parties.
- Label output metadata as synthetic.
- Include an audible or metadata watermark option where supported by the backend.
- Prevent generation requests that claim to be the real person speaking live, authorizing payments, giving legal/medical/financial instructions as that person, or impersonating a person without disclosure.
- Keep imported voice data local by default.
- Provide delete controls that remove source audio, cleaned audio, profile artifacts, blends referencing the profile, and generated clips if requested.

Consent schema:

```json
{
  "voiceProfileId": "voice_a",
  "speakerDisplayName": "Alice",
  "consentType": "self_or_written_permission",
  "allowedUses": ["private_agent_voice", "local_audio_export"],
  "confirmedAt": "2026-05-22T00:00:00Z",
  "confirmedBy": "local_user",
  "notes": ""
}
```

## Data Flow

### Import Flow

1. User uploads or records a clip.
2. User confirms consent and allowed usage.
3. App converts, trims, normalizes, and analyzes the clip.
4. App rejects or warns on poor sample quality.
5. TTS adapter extracts the backend-specific profile artifact.
6. App stores profile metadata and preview.

### Blend Flow

1. User chooses at least two consent-approved profiles.
2. User sets weights that sum to 100%.
3. App selects the best available strategy from the active TTS adapter.
4. User previews a standard phrase.
5. App saves the blend preset.

### Agent Flow

1. User types or speaks.
2. STT converts speech to text if needed.
3. Agent core generates a reply.
4. Safety filter checks the reply and requested voice use.
5. TTS adapter synthesizes speech using the selected blend.
6. App plays audio and stores output metadata.

## Error Handling

- Missing consent: block profile use and show the missing consent state.
- Poor audio sample: allow re-upload or manual override only for private local experiments.
- Unsupported blend strategy: fall back to a clearly labeled non-blended or designed synthetic voice.
- TTS failure: preserve the text response, log backend error, and allow retry with another backend.
- Long generation: show progress and allow cancellation.
- Profile deletion: prevent dangling blend references by archiving affected blends.

## Testing Strategy

MVP test coverage should include:

- Consent gate blocks voice profile creation without confirmation.
- Audio import rejects unsupported files and records quality metadata.
- Blend weights normalize and validate correctly.
- Blend cannot use fewer than two profiles.
- TTS adapter capability selection chooses supported strategies only.
- Generated clip metadata records source profiles, weights, strategy, backend, and synthetic label.
- Delete flow removes voice artifacts and dependent blend references.
- Safety filter blocks obvious impersonation and fraud-like requests.

Manual verification should include:

- Import two clean voice samples.
- Create a 50/50 blend.
- Generate a short agent reply.
- Confirm audio file is produced.
- Confirm metadata identifies the generated voice as synthetic and lists both source profiles.

## Launch Milestones

### Milestone 1: Design And Prototype Foundation

- Create project scaffold.
- Implement local data model.
- Build import wizard skeleton.
- Add consent metadata.
- Add audio preprocessing shell.

### Milestone 2: First TTS Adapter

- Integrate one local TTS backend.
- Extract reusable profile artifact.
- Generate single-profile preview audio.
- Store generation metadata.

### Milestone 3: Blend MVP

- Add blend editor.
- Implement the first supported blend strategy.
- Generate blended preview.
- Add fallback strategy labeling.

### Milestone 4: Agent Integration

- Add agent chat surface.
- Connect LLM text response generation.
- Synthesize agent replies using selected blend.
- Add history and export.

### Milestone 5: Safety And Launch QA

- Finish delete/export flows.
- Add misuse-blocking prompts and checks.
- Run manual verification.
- Document limitations and supported use cases.

## Initial Implementation Decisions

Use these defaults for the first implementation plan:

- App shell: local web app with a React frontend and Python service.
- TTS backend: Qwen3-TTS first, behind a backend-neutral adapter interface.
- Agent backend: user-configurable provider with OpenAI-compatible API and Ollama-compatible local LLM options behind a provider-neutral agent interface.
- MVP input mode: typed chat plus generated audio output.
- Microphone input: deferred until voice profiles, blend generation, and export metadata work.
- Realtime API / LiveKit / Pipecat integration: deferred until the custom mixed-voice path is proven.

These choices keep the first build focused on the hardest product requirement: importing multiple people, building consented voice profiles, and generating a usable mixed voice. The interfaces should still leave room for F5-TTS, Dia, VibeVoice, LiveKit, Pipecat, or OpenAI Realtime adapters later.

## Acceptance Criteria

The design is ready for implementation planning when:

- The user approves this spec.
- The user accepts the initial implementation decisions above or requests a specific change.
- The implementation plan covers each milestone and test requirement in this spec.
