import type { AgentConfig, AgentReply, GenerationResult, VoiceBlend } from "./types";

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

