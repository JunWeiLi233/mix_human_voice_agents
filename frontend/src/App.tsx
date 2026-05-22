import { useEffect, useState } from "react";
import {
  createBlend,
  deleteVoice,
  generateClip,
  getQwenRuntimeStatus,
  getQwenVerificationReport,
  listBlends,
  listGenerations,
  listVoices,
  requestAgentReply,
  runQwenVerification,
} from "./api";
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
  QwenVerificationReport,
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
  const [savedBlends, setSavedBlends] = useState<VoiceBlend[]>([]);
  const [blend, setBlend] = useState<VoiceBlend | null>(null);
  const [generations, setGenerations] = useState<GenerationResult[]>([]);
  const [qwenStatus, setQwenStatus] = useState<TtsRuntimeStatus | null>(null);
  const [qwenVerification, setQwenVerification] = useState<QwenVerificationReport | null>(null);
  const [qwenVerificationText, setQwenVerificationText] = useState(
    "This is a disclosed synthetic mixed voice runtime verification.",
  );
  const [qwenVerificationVoiceIds, setQwenVerificationVoiceIds] = useState<string[]>([]);
  const [qwenVerificationBusy, setQwenVerificationBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listVoices()
      .then((profiles) => {
        setVoices(profiles);
        setBlendProfiles(toBlendDrafts(profiles, []));
        setQwenVerificationVoiceIds(profiles.map((profile) => profile.id));
      })
      .catch(() => {
        setVoices([]);
        setBlendProfiles([]);
        setQwenVerificationVoiceIds([]);
      });
  }, []);

  useEffect(() => {
    void listBlends()
      .then((blends) => {
        setSavedBlends(blends);
        setBlend((current) => current ?? blends[0] ?? null);
      })
      .catch(() => {
        setSavedBlends([]);
      });
  }, []);

  useEffect(() => {
    void listGenerations()
      .then(setGenerations)
      .catch(() => {
        setGenerations([]);
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

  useEffect(() => {
    void getQwenVerificationReport()
      .then(setQwenVerification)
      .catch(() => {
        setQwenVerification({
          status: "missing",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          voice_profile_ids: [],
          error: "Qwen runtime verification report is unavailable.",
        });
      });
  }, []);

  async function handleCreateBlend() {
    setError(null);
    try {
      const created = await createBlend(blendProfiles, ttsBackend);
      setBlend(created);
      setSavedBlends((current) => [created, ...current.filter((item) => item.id !== created.id)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Blend creation failed");
    }
  }

  function handleImported(profile: VoiceProfile) {
    const next = [...voices, profile];
    setVoices(next);
    setBlendProfiles((currentProfiles) => toBlendDrafts(next, currentProfiles));
    setQwenVerificationVoiceIds((currentIds) => [...currentIds, profile.id]);
    setBlend(null);
  }

  async function handleDeleteVoice(voiceProfileId: string) {
    setError(null);
    try {
      const result = await deleteVoice(voiceProfileId);
      setVoices((current) => current.filter((voice) => voice.id !== result.deleted_voice_profile_id));
      setBlendProfiles((current) =>
        current.filter((profile) => profile.voice_profile_id !== result.deleted_voice_profile_id),
      );
      setQwenVerificationVoiceIds((current) =>
        current.filter((voiceProfileId) => voiceProfileId !== result.deleted_voice_profile_id),
      );
      setSavedBlends((current) => current.filter((savedBlend) => !result.deleted_blend_ids.includes(savedBlend.id)));
      setGenerations((current) =>
        current.filter((generation) => !result.deleted_generation_ids.includes(generation.id)),
      );
      setBlend((current) => {
        if (!current) return null;
        const deletedActiveBlend = result.deleted_blend_ids.includes(current.id);
        const referencesDeletedVoice = current.profiles.some(
          (profile) => profile.voice_profile_id === result.deleted_voice_profile_id,
        );
        return deletedActiveBlend || referencesDeletedVoice ? null : current;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice deletion failed");
    }
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

  async function handleRunQwenVerification() {
    setError(null);
    setQwenVerificationBusy(true);
    try {
      const report = await runQwenVerification(
        qwenVerificationVoiceIds,
        qwenVerificationText,
      );
      setQwenVerification(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Qwen verification failed");
    } finally {
      setQwenVerificationBusy(false);
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
        <VoiceEngineSettings
          value={ttsBackend}
          status={qwenStatus}
          verification={qwenVerification}
          voices={voices}
          selectedVerificationVoiceIds={qwenVerificationVoiceIds}
          verificationText={qwenVerificationText}
          verificationBusy={qwenVerificationBusy}
          onChange={setTtsBackend}
          onToggleVerificationVoice={(voiceProfileId) => {
            setQwenVerificationVoiceIds((currentIds) =>
              currentIds.includes(voiceProfileId)
                ? currentIds.filter((id) => id !== voiceProfileId)
                : [...currentIds, voiceProfileId],
            );
          }}
          onVerificationTextChange={setQwenVerificationText}
          onRunVerification={handleRunQwenVerification}
        />
        <VoiceLibrary voices={voices} onDeleteVoice={handleDeleteVoice} />
        <ImportVoice onImported={handleImported} />
        <BlendMixer
          blend={blend}
          profiles={blendProfiles}
          savedBlends={savedBlends}
          onCreateBlend={handleCreateBlend}
          onSelectBlend={setBlend}
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
