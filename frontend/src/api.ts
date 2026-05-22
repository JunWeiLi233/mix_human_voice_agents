import type {
  AgentConfig,
  AgentProviderVerificationReport,
  AgentReply,
  BlendDraftProfile,
  DeleteVoiceResult,
  GenerationResult,
  LaunchReadinessReport,
  QwenRuntimeConfig,
  QwenVerificationReport,
  TtsBackend,
  TtsRuntimeStatus,
  VoiceConsentInput,
  VoiceBlend,
  VoiceProfile,
} from "./types";

export async function listVoices(): Promise<VoiceProfile[]> {
  const response = await fetch("/api/voices");
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function deleteVoice(voiceProfileId: string): Promise<DeleteVoiceResult> {
  const response = await fetch(`/api/voices/${voiceProfileId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function getQwenRuntimeStatus(): Promise<TtsRuntimeStatus> {
  const response = await fetch("/api/tts/qwen/status");
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function getQwenVerificationReport(): Promise<QwenVerificationReport> {
  const response = await fetch("/api/tts/qwen/verification");
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function runQwenVerification(
  voiceProfileIds: string[],
  text: string,
  runtime: QwenRuntimeConfig,
): Promise<QwenVerificationReport> {
  const response = await fetch("/api/tts/qwen/verification", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      voice_profile_ids: voiceProfileIds,
      text,
      model_id: runtime.model_id || null,
      device_map: runtime.device_map || null,
      dtype: runtime.dtype || null,
      attn_implementation: runtime.attn_implementation || null,
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function listGenerations(): Promise<GenerationResult[]> {
  const response = await fetch("/api/generations");
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function listBlends(): Promise<VoiceBlend[]> {
  const response = await fetch("/api/blends");
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function getLaunchReadiness(): Promise<LaunchReadinessReport> {
  const response = await fetch("/api/launch/readiness");
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function createBlend(profiles: BlendDraftProfile[], ttsBackend: TtsBackend): Promise<VoiceBlend> {
  const selected = profiles.filter((profile) => profile.weight > 0);
  const response = await fetch("/api/blends", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: selected.map((profile) => profile.display_name).join(" + "),
      profiles: selected.map((profile) => ({ voice_profile_id: profile.voice_profile_id, weight: profile.weight })),
      strategy: ttsBackend === "qwen3_tts" ? "multi_reference_prompt" : "local_development_wav",
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function requestAgentReply(config: AgentConfig, prompt: string): Promise<AgentReply> {
  const response = await fetch("/api/agent/reply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config, prompt }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function runAgentProviderVerification(
  config: AgentConfig,
  prompt: string,
): Promise<AgentProviderVerificationReport> {
  const response = await fetch("/api/agent/provider-verification", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config, prompt }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function generateClip(
  blend: VoiceBlend,
  agentReply: AgentReply,
  ttsBackend: TtsBackend,
  prompt: string,
  runtime?: QwenRuntimeConfig,
): Promise<GenerationResult> {
  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      agent_reply: agentReply.reply,
      agent_trace: {
        provider: agentReply.provider,
        model: agentReply.model,
      },
      blend,
      tts_backend: ttsBackend,
      qwen_runtime_config: ttsBackend === "qwen3_tts" ? runtime : undefined,
      model_id: ttsBackend === "qwen3_tts" ? runtime?.model_id || null : undefined,
      device_map: ttsBackend === "qwen3_tts" ? runtime?.device_map || null : undefined,
      dtype: ttsBackend === "qwen3_tts" ? runtime?.dtype || null : undefined,
      attn_implementation: ttsBackend === "qwen3_tts" ? runtime?.attn_implementation || null : undefined,
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function importVoice(
  file: File,
  displayName: string,
  consent: VoiceConsentInput,
): Promise<VoiceProfile> {
  const form = new FormData();
  form.set("speaker_display_name", displayName);
  form.set("consent_type", "self_or_written_permission");
  form.set("allowed_uses", "private_agent_voice,local_audio_export");
  form.set("confirmed_by", consent.confirmed_by);
  form.set("notes", consent.notes);
  form.set("reference_text", consent.reference_text);
  form.set("file", file);

  const response = await fetch("/api/voices", {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
