import type { TtsBackend } from "../types";

type Props = {
  value: TtsBackend;
  onChange: (backend: TtsBackend) => void;
};

export function VoiceEngineSettings({ value, onChange }: Props) {
  return (
    <section className="panel">
      <h2>Voice Engine</h2>
      <div className="segmented" role="group" aria-label="Voice engine">
        <button
          type="button"
          className={value === "local_development_wav" ? "active" : ""}
          onClick={() => onChange("local_development_wav")}
        >
          Local preview
        </button>
        <button
          type="button"
          className={value === "qwen3_tts" ? "active" : ""}
          onClick={() => onChange("qwen3_tts")}
        >
          Qwen3-TTS
        </button>
      </div>
      <p>Qwen3-TTS uses imported consented voice samples when its local runtime is installed.</p>
    </section>
  );
}

