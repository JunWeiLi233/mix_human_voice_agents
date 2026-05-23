import { useEffect, useState } from "react";
import {
  createBlend,
  deleteVoice,
  generateClip,
  getAgentProviderVerification,
  getLaunchArtifacts,
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
import { LaunchArtifactInventory } from "./components/LaunchArtifactInventory";
import { LaunchReadiness } from "./components/LaunchReadiness";
import { VoiceLibrary } from "./components/VoiceLibrary";
import { VoiceEngineSettings } from "./components/VoiceEngineSettings";
import type {
  AgentConfig,
  AgentProviderVerificationReport,
  BlendDraftProfile,
  GenerationResult,
  LaunchArtifactsReport,
  LaunchReadinessReport,
  QwenRuntimeConfig,
  QwenVerificationReport,
  TtsBackend,
  TtsRuntimeStatus,
  VoiceBlend,
  VoiceProfile,
} from "./types";
import "./styles.css";

type WorkspacePage = "studio" | "evidence" | "launch";

const defaultAgentConfig: AgentConfig = {
  provider: "ollama",
  model: "llama3.1",
  base_url: "http://127.0.0.1:11434",
  api_key: "",
  system_prompt: "You are a disclosed synthetic mixed-voice assistant.",
};

const agentConfigStorageKey = "mixedVoiceAgent.providerSettings";

export default function App() {
  const [activePage, setActivePage] = useState<WorkspacePage>("studio");
  const [agentConfig, setAgentConfig] = useState<AgentConfig>(() => loadStoredAgentConfig());
  const [ttsBackend, setTtsBackend] = useState<TtsBackend>("local_development_wav");
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [blendProfiles, setBlendProfiles] = useState<BlendDraftProfile[]>([]);
  const [savedBlends, setSavedBlends] = useState<VoiceBlend[]>([]);
  const [blend, setBlend] = useState<VoiceBlend | null>(null);
  const [generations, setGenerations] = useState<GenerationResult[]>([]);
  const [launchArtifacts, setLaunchArtifacts] = useState<LaunchArtifactsReport | null>(null);
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
    storeAgentConfig(agentConfig);
  }, [agentConfig]);

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
    void refreshLaunchArtifacts();
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
      void refreshLaunchArtifacts();
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
    void refreshLaunchArtifacts();
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
      void refreshLaunchArtifacts();
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
      void refreshLaunchArtifacts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    }
  }

  async function refreshLaunchArtifacts() {
    try {
      setLaunchArtifacts(await getLaunchArtifacts());
    } catch {
      setLaunchArtifacts(null);
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
        void refreshLaunchArtifacts();
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
      void refreshLaunchArtifacts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Qwen verification failed");
    } finally {
      setQwenVerificationBusy(false);
    }
  }

  const pageNav: Array<{ id: WorkspacePage; label: string; description: string }> = [
    { id: "studio", label: "Studio", description: "Import, blend, and generate" },
    { id: "evidence", label: "Evidence", description: "Voice records and exports" },
    { id: "launch", label: "Launch", description: "Provider and runtime checks" },
  ];
  const readinessLabel =
    launchReadiness?.status === "ready" ? "Ready" : launchReadiness?.status === "blocked" ? "Blocked" : "Checking";

  return (
    <main className="app-shell">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Local-first mixed voice agent</p>
          <h1>Mixed Voice Agent Studio</h1>
          <p className="hero-text">
            Build a consent-gated multi-speaker voice blend, connect any API or local LLM, then verify the Qwen
            runtime before launch.
          </p>
        </div>
        <div className="hero-status" aria-label="Workspace status summary">
          <span>{readinessLabel}</span>
          <strong>{voices.length}</strong>
          <small>imported voices</small>
          <strong>{generations.length}</strong>
          <small>generated clips</small>
        </div>
      </header>
      <nav className="page-nav" aria-label="Workspace pages">
        {pageNav.map((page) => (
          <button
            key={page.id}
            type="button"
            aria-label={`${page.label} page`}
            aria-current={activePage === page.id ? "page" : undefined}
            className={activePage === page.id ? "active" : ""}
            onClick={() => setActivePage(page.id)}
          >
            <span>{page.label}</span>
            <small>{page.description}</small>
          </button>
        ))}
      </nav>
      {error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : null}
      {activePage === "studio" ? (
        <>
          <section className="page-intro" aria-labelledby="studio-page-heading">
            <p className="eyebrow">Studio Page</p>
            <h2 id="studio-page-heading">Build the mixed voice workflow</h2>
          </section>
          <div className="layout studio-layout">
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
        </>
      ) : null}
      {activePage === "evidence" ? (
        <>
          <section className="page-intro" aria-labelledby="evidence-page-heading">
            <p className="eyebrow">Evidence Page</p>
            <h2 id="evidence-page-heading">Voice evidence and exports</h2>
          </section>
          <div className="layout evidence-layout">
            <VoiceLibrary voices={voices} onDeleteVoice={handleDeleteVoice} />
            <GenerationHistory generations={generations} />
          </div>
        </>
      ) : null}
      {activePage === "launch" ? (
        <>
          <section className="page-intro" aria-labelledby="launch-page-heading">
            <p className="eyebrow">Launch Control Page</p>
            <h2 id="launch-page-heading">Verify provider, runtime, and release gates</h2>
          </section>
          <div className="layout launch-layout">
            <LaunchReadiness readiness={launchReadiness} />
            <LaunchArtifactInventory
              artifacts={launchArtifacts}
              onPruned={() => {
                void refreshLaunchArtifacts();
                void refreshLaunchReadiness();
              }}
            />
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
          </div>
        </>
      ) : null}
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

function loadStoredAgentConfig(): AgentConfig {
  try {
    const stored = localStorage.getItem(agentConfigStorageKey);
    if (!stored) return defaultAgentConfig;
    const parsed = JSON.parse(stored) as Partial<AgentConfig>;
    if (!isAgentProvider(parsed.provider)) return defaultAgentConfig;
    return {
      ...defaultAgentConfig,
      provider: parsed.provider,
      model: typeof parsed.model === "string" && parsed.model.trim() ? parsed.model : defaultAgentConfig.model,
      base_url:
        typeof parsed.base_url === "string" && parsed.base_url.trim()
          ? parsed.base_url
          : defaultAgentConfig.base_url,
      system_prompt:
        typeof parsed.system_prompt === "string" && parsed.system_prompt.trim()
          ? parsed.system_prompt
          : defaultAgentConfig.system_prompt,
      api_key: "",
    };
  } catch {
    return defaultAgentConfig;
  }
}

function storeAgentConfig(config: AgentConfig) {
  try {
    localStorage.setItem(
      agentConfigStorageKey,
      JSON.stringify({
        provider: config.provider,
        model: config.model,
        base_url: config.base_url,
        system_prompt: config.system_prompt,
      }),
    );
  } catch {
    return;
  }
}

function isAgentProvider(provider: unknown): provider is AgentConfig["provider"] {
  return (
    provider === "openai" ||
    provider === "anthropic" ||
    provider === "google" ||
    provider === "xai" ||
    provider === "openai_compatible" ||
    provider === "ollama"
  );
}
