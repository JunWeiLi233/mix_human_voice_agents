export type BlendStrategy = "local_development_wav";

export type BlendProfile = {
  voice_profile_id: string;
  weight: number;
};

export type VoiceBlend = {
  id: string;
  name: string;
  profiles: BlendProfile[];
  strategy: BlendStrategy;
  synthetic_label: string;
};

export type GenerationResult = {
  id: string;
  audio_path: string;
  metadata_path: string;
  synthetic_label: string;
  source_profile_ids: string[];
  blend_strategy: BlendStrategy;
};

export type AgentProviderKind = "openai_compatible" | "ollama";

export type AgentConfig = {
  provider: AgentProviderKind;
  model: string;
  base_url: string;
  api_key: string;
  system_prompt: string;
};

export type AgentReply = {
  reply: string;
  provider: AgentProviderKind;
  model: string;
};

