import type { TtsBackend, TtsRuntimeStatus } from "../types";

type Props = {
  value: TtsBackend;
  status: TtsRuntimeStatus | null;
  onChange: (backend: TtsBackend) => void;
};

export function VoiceEngineSettings({ value, status, onChange }: Props) {
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
      <dl>
        <dt>Qwen runtime</dt>
        <dd>{status ? (status.available ? "Installed" : "Not installed") : "Checking"}</dd>
        {status?.model_id ? (
          <>
            <dt>Model</dt>
            <dd>{status.model_id}</dd>
          </>
        ) : null}
        {status ? (
          <>
            <dt>Status</dt>
            <dd>{status.message}</dd>
          </>
        ) : null}
      </dl>
    </section>
  );
}
