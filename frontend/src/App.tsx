import { useEffect, useState } from "react";
import { createBlend, generateClip, getQwenRuntimeStatus, listVoices, requestAgentReply } from "./api";
import { AgentChat } from "./components/AgentChat";
import { AgentProviderSettings } from "./components/AgentProviderSettings";
import { BlendMixer } from "./components/BlendMixer";
import { GenerationHistory } from "./components/GenerationHistory";
import { ImportVoice } from "./components/ImportVoice";
import { VoiceLibrary } from "./components/VoiceLibrary";
import { VoiceEngineSettings } from "./components/VoiceEngineSettings";
import type {
  AgentConfig,
  BlendDraftProfile,
  GenerationResult,
  TtsBackend,
  TtsRuntimeStatus,
  VoiceBlend,
  VoiceProfile,
} from "./types";
import "./styles.css";

export default function App() {
  const [agentConfig, setAgentConfig] = useState<AgentConfig>({
    provider: "ollama",
    model: "llama3.1",
    base_url: "http://127.0.0.1:11434",
    api_key: "",
    system_prompt: "You are a disclosed synthetic mixed-voice assistant.",
  });
  const [ttsBackend, setTtsBackend] = useState<TtsBackend>("local_development_wav");
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [blendProfiles, setBlendProfiles] = useState<BlendDraftProfile[]>([]);
  const [blend, setBlend] = useState<VoiceBlend | null>(null);
  const [generations, setGenerations] = useState<GenerationResult[]>([]);
  const [qwenStatus, setQwenStatus] = useState<TtsRuntimeStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listVoices()
      .then((profiles) => {
        setVoices(profiles);
        setBlendProfiles(toBlendDrafts(profiles, []));
      })
      .catch(() => {
        setVoices([]);
        setBlendProfiles([]);
      });
  }, []);

  useEffect(() => {
    void getQwenRuntimeStatus()
      .then(setQwenStatus)
      .catch(() => {
        setQwenStatus({
          backend: "qwen3_tts",
          available: false,
          model_id: null,
          message: "Qwen3-TTS runtime status is unavailable.",
        });
      });
  }, []);

  async function handleCreateBlend() {
    setError(null);
    try {
      setBlend(await createBlend(blendProfiles, ttsBackend));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Blend creation failed");
    }
  }

  function handleImported(profile: VoiceProfile) {
    const next = [...voices, profile];
    setVoices(next);
    setBlendProfiles((currentProfiles) => toBlendDrafts(next, currentProfiles));
    setBlend(null);
  }

  function handleBlendWeightChange(voiceProfileId: string, weight: number) {
    setBlendProfiles((current) =>
      current.map((profile) =>
        profile.voice_profile_id === voiceProfileId ? { ...profile, weight: Math.max(0.1, weight) } : profile,
      ),
    );
    setBlend(null);
  }

  async function handleGenerate(prompt: string) {
    if (!blend) return;
    setError(null);
    try {
      const agentReply = await requestAgentReply(agentConfig, prompt);
      const result = await generateClip(blend, agentReply.reply, ttsBackend, prompt);
      setGenerations((current) => [result, ...current]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    }
  }

  return (
    <main>
      <header>
        <p>Local-first prototype</p>
        <h1>Mixed Voice Agent Studio</h1>
      </header>
      {error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="layout">
        <AgentProviderSettings value={agentConfig} onChange={setAgentConfig} />
        <VoiceEngineSettings value={ttsBackend} status={qwenStatus} onChange={setTtsBackend} />
        <VoiceLibrary voices={voices} />
        <ImportVoice onImported={handleImported} />
        <BlendMixer
          blend={blend}
          profiles={blendProfiles}
          onCreateBlend={handleCreateBlend}
          onWeightChange={handleBlendWeightChange}
        />
        <AgentChat blend={blend} onGenerate={handleGenerate} />
        <GenerationHistory generations={generations} />
      </div>
    </main>
  );
}

function toBlendDrafts(voices: VoiceProfile[], current: BlendDraftProfile[]): BlendDraftProfile[] {
  return voices.map((voice) => {
    const existing = current.find((profile) => profile.voice_profile_id === voice.id);
    return {
      voice_profile_id: voice.id,
      display_name: voice.display_name,
      weight: existing?.weight ?? 1,
    };
  });
}
