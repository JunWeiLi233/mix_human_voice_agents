export type BlendStrategy = "local_development_wav" | "multi_reference_prompt";
export type TtsBackend = "local_development_wav" | "qwen3_tts";

export type BlendProfile = {
  voice_profile_id: string;
  weight: number;
};

export type BlendDraftProfile = BlendProfile & {
  display_name: string;
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
  tts_backend: TtsBackend;
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

export type TtsRuntimeStatus = {
  backend: TtsBackend;
  available: boolean;
  model_id: string | null;
  message: string;
};

export type VoiceProfile = {
  id: string;
  display_name: string;
  source_audio_path: string;
  cleaned_audio_path: string;
  consent: {
    voice_profile_id: string;
    speaker_display_name: string;
    synthetic_voice_allowed: boolean;
    allowed_uses: string[];
  };
};

export type DeleteVoiceResult = {
  deleted_voice_profile_id: string;
  deleted_blend_ids: string[];
};

export type VoiceConsentInput = {
  confirmed_by: string;
  notes: string;
};
