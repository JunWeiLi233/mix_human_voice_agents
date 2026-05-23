import { useEffect, useState } from "react";
import {
  createBlend,
  deleteVoice,
  generateClip,
  getAgentProviderVerification,
  getLaunchReadiness,
  getQwenRuntimeStatus,
  getQwenVerificationReport,
  listBlends,
  listGenerations,
  listVoices,
  requestAgentReply,
  runAgentProviderVerification,
  runQwenVerification,
} from "./api";
import { AgentChat } from "./components/AgentChat";
import { AgentProviderSettings } from "./components/AgentProviderSettings";
import { BlendMixer } from "./components/BlendMixer";
import { GenerationHistory } from "./components/GenerationHistory";
import { ImportVoice } from "./components/ImportVoice";
import { LaunchReadiness } from "./components/LaunchReadiness";
import { VoiceLibrary } from "./components/VoiceLibrary";
import { VoiceEngineSettings } from "./components/VoiceEngineSettings";
import type {
  AgentConfig,
  AgentProviderVerificationReport,
  BlendDraftProfile,
  GenerationResult,
  LaunchReadinessReport,
  QwenRuntimeConfig,
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
  const [launchReadiness, setLaunchReadiness] = useState<LaunchReadinessReport | null>(null);
  const [qwenStatus, setQwenStatus] = useState<TtsRuntimeStatus | null>(null);
  const [qwenVerification, setQwenVerification] = useState<QwenVerificationReport | null>(null);
  const [qwenVerificationText, setQwenVerificationText] = useState(
    "This is a disclosed synthetic mixed voice runtime verification.",
  );
  const [qwenRuntimeConfig, setQwenRuntimeConfig] = useState<QwenRuntimeConfig>({
    model_id: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    device_map: "auto",
    dtype: "",
    attn_implementation: "",
  });
  const [qwenVerificationVoiceIds, setQwenVerificationVoiceIds] = useState<string[]>([]);
  const [qwenVerificationBusy, setQwenVerificationBusy] = useState(false);
  const [agentProviderVerification, setAgentProviderVerification] =
    useState<AgentProviderVerificationReport | null>(null);
  const [agentProviderTestReply, setAgentProviderTestReply] = useState<string | null>(null);
  const [agentProviderTesting, setAgentProviderTesting] = useState(false);
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
      .then((report) => {
        setQwenVerification(report);
        if (report.status === "passed") {
          setQwenVerificationVoiceIds(report.voice_profile_ids);
          setQwenRuntimeConfig((current) => ({
            model_id: report.model_id ?? current.model_id,
            device_map: report.device_map ?? current.device_map,
            dtype: report.dtype ?? current.dtype,
            attn_implementation: report.attn_implementation ?? current.attn_implementation,
          }));
        }
      })
      .catch(() => {
        setQwenVerification({
          status: "missing",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          checked_at: new Date().toISOString(),
          voice_profile_ids: [],
          error: "Qwen runtime verification report is unavailable.",
        });
      });
  }, []);

  useEffect(() => {
    void getAgentProviderVerification()
      .then((report) => {
        setAgentProviderVerification(report);
        if (report.status === "passed" && report.provider && report.model && report.base_url) {
          const provider = report.provider;
          const model = report.model;
          const baseUrl = report.base_url;
          setAgentConfig((current) => ({
            ...current,
            provider,
            model,
            base_url: baseUrl,
            api_key: "",
          }));
        }
      })
      .catch(() => {
        setAgentProviderVerification({
          status: "missing",
          report_path: "data/agent-provider-verification-report.json",
          error: "Agent provider verification report is unavailable.",
        });
      });
  }, []);

  useEffect(() => {
    void refreshLaunchReadiness();
  }, []);

  async function refreshLaunchReadiness() {
    try {
      setLaunchReadiness(await getLaunchReadiness());
    } catch {
      setLaunchReadiness(null);
    }
  }

  async function handleCreateBlend() {
    setError(null);
    try {
      const created = await createBlend(blendProfiles, ttsBackend);
      setBlend(created);
      setSavedBlends((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      void refreshLaunchReadiness();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Blend creation failed");
    }
  }

  function handleImported(profile: VoiceProfile) {
    const next = [...voices, profile];
    setVoices(next);
    setBlendProfiles((currentProfiles) => toBlendDrafts(next, currentProfiles));
    setQwenVerificationVoiceIds((currentIds) => {
      const nextVoiceIds = new Set(next.map((voice) => voice.id));
      return [...currentIds.filter((voiceId) => nextVoiceIds.has(voiceId)), profile.id];
    });
    setBlend(null);
    void refreshLaunchReadiness();
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
      void refreshLaunchReadiness();
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
      const result = await generateClip(blend, agentReply, ttsBackend, prompt, qwenRuntimeConfig);
      setGenerations((current) => [result, ...current]);
      void refreshLaunchReadiness();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    }
  }

  async function handleTestAgentProvider() {
    setError(null);
    setAgentProviderTestReply(null);
    setAgentProviderTesting(true);
    try {
      const report = await runAgentProviderVerification(
        agentConfig,
        "Reply with one short sentence confirming this provider is connected.",
      );
      setAgentProviderVerification(report);
      if (report.status === "passed" && report.reply) {
        setAgentProviderTestReply(report.reply);
        void refreshLaunchReadiness();
      } else {
        throw new Error(report.error ?? "Agent provider test failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent provider test failed");
    } finally {
      setAgentProviderTesting(false);
    }
  }

  async function handleRunQwenVerification() {
    setError(null);
    setQwenVerificationBusy(true);
    try {
      const report = await runQwenVerification(
        qwenVerificationVoiceIds,
        qwenVerificationText,
        qwenRuntimeConfig,
      );
      setQwenVerification(report);
      void refreshLaunchReadiness();
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
        <AgentProviderSettings
          value={agentConfig}
          verification={agentProviderVerification}
          testReply={agentProviderTestReply}
          testing={agentProviderTesting}
          onChange={setAgentConfig}
          onTestProvider={handleTestAgentProvider}
        />
        <VoiceEngineSettings
          value={ttsBackend}
          status={qwenStatus}
          verification={qwenVerification}
          voices={voices}
          selectedVerificationVoiceIds={qwenVerificationVoiceIds}
          verificationText={qwenVerificationText}
          runtimeConfig={qwenRuntimeConfig}
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
          onRuntimeConfigChange={setQwenRuntimeConfig}
          onRunVerification={handleRunQwenVerification}
        />
        <LaunchReadiness readiness={launchReadiness} />
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
