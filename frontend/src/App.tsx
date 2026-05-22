import { useEffect, useState } from "react";
import { createBlend, generateClip, listVoices, requestAgentReply } from "./api";
import { AgentChat } from "./components/AgentChat";
import { AgentProviderSettings } from "./components/AgentProviderSettings";
import { BlendMixer } from "./components/BlendMixer";
import { GenerationHistory } from "./components/GenerationHistory";
import { ImportVoice } from "./components/ImportVoice";
import { VoiceLibrary } from "./components/VoiceLibrary";
import { VoiceEngineSettings } from "./components/VoiceEngineSettings";
import type { AgentConfig, GenerationResult, TtsBackend, VoiceBlend, VoiceProfile } from "./types";
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
  const [blend, setBlend] = useState<VoiceBlend | null>(null);
  const [generations, setGenerations] = useState<GenerationResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listVoices()
      .then(setVoices)
      .catch(() => {
        setVoices([]);
      });
  }, []);

  async function handleCreateBlend() {
    setError(null);
    try {
      setBlend(await createBlend(voices, ttsBackend));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Blend creation failed");
    }
  }

  function handleImported(profile: VoiceProfile) {
    setVoices((current) => [...current, profile]);
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
        <VoiceEngineSettings value={ttsBackend} onChange={setTtsBackend} />
        <VoiceLibrary voices={voices} />
        <ImportVoice onImported={handleImported} />
        <BlendMixer blend={blend} voices={voices} onCreateBlend={handleCreateBlend} />
        <AgentChat blend={blend} onGenerate={handleGenerate} />
        <GenerationHistory generations={generations} />
      </div>
    </main>
  );
}
