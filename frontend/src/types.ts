export type BlendStrategy = "local_development_wav" | "multi_reference_prompt";
export type TtsBackend = "local_development_wav" | "qwen3_tts";

export type BlendProfile = {
  voice_profile_id: string;
  weight: number;
};

export type BlendDraftProfile = BlendProfile & {
  display_name: string;
};

export type SourceProfileDetail = BlendProfile & {
  display_name: string;
  consent_confirmed_by: string;
  allowed_uses: string[];
  reference_text_present: boolean;
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
  source_profiles?: BlendProfile[];
  source_profile_details?: SourceProfileDetail[];
  watermark?: {
    type: "metadata";
    label: string;
    disclosure: string;
  };
  blend_strategy: BlendStrategy;
  tts_backend: TtsBackend;
  agent_trace?: {
    provider: AgentProviderKind;
    model: string;
  } | null;
};

export type AgentProviderKind = "openai" | "anthropic" | "xai" | "openai_compatible" | "ollama";

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

export type AgentProviderVerificationReport = {
  status: "missing" | "passed" | "failed";
  report_path: string;
  provider?: AgentProviderKind | null;
  model?: string | null;
  reply?: string | null;
  error?: string | null;
};

export type TtsRuntimeStatus = {
  backend: TtsBackend;
  available: boolean;
  model_id: string | null;
  message: string;
};

export type QwenVerificationReport = {
  status: "missing" | "passed" | "failed";
  tts_backend: "qwen3_tts";
  report_path: string;
  voice_profile_ids: string[];
  blend_id?: string | null;
  blend_strategy?: BlendStrategy | null;
  output_audio_path?: string | null;
  text?: string | null;
  error?: string | null;
};

export type LaunchReadinessCheck = {
  id: string;
  label: string;
  passed: boolean;
  detail: string;
};

export type LaunchReadinessReport = {
  status: "ready" | "blocked";
  checks: LaunchReadinessCheck[];
  blocking_reasons: string[];
};

export type VoiceProfile = {
  id: string;
  display_name: string;
  reference_text: string;
  source_audio_path: string;
  cleaned_audio_path: string;
  quality: {
    file_name: string;
    size_bytes: number;
    format: string;
    duration_seconds: number | null;
    sample_rate_hz: number | null;
    channel_count: number | null;
    warnings: string[];
  };
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
  deleted_generation_ids: string[];
};

export type VoiceConsentInput = {
  confirmed_by: string;
  notes: string;
  reference_text: string;
};
