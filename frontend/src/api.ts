import type { AgentConfig, AgentReply, GenerationResult, VoiceBlend, VoiceProfile } from "./types";

export async function createBlend(): Promise<VoiceBlend> {
  const response = await fetch("/api/blends", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "Demo Pair",
      profiles: [
        { voice_profile_id: "voice_a", weight: 1 },
        { voice_profile_id: "voice_b", weight: 1 },
      ],
      strategy: "local_development_wav",
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

export async function generateClip(blend: VoiceBlend, agentReply: string): Promise<GenerationResult> {
  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: "Generate a disclosed synthetic assistant reply.",
      agent_reply: agentReply,
      blend,
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function importVoice(file: File, displayName: string): Promise<VoiceProfile> {
  const form = new FormData();
  form.set("speaker_display_name", displayName);
  form.set("consent_type", "self_or_written_permission");
  form.set("allowed_uses", "private_agent_voice,local_audio_export");
  form.set("confirmed_by", "local_user");
  form.set("notes", "Confirmed in local prototype UI.");
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
