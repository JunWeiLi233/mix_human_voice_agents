import type { QwenVerificationReport, TtsBackend, TtsRuntimeStatus, VoiceProfile } from "../types";

type Props = {
  value: TtsBackend;
  status: TtsRuntimeStatus | null;
  verification: QwenVerificationReport | null;
  voices: VoiceProfile[];
  selectedVerificationVoiceIds: string[];
  verificationText: string;
  verificationBusy: boolean;
  onChange: (backend: TtsBackend) => void;
  onToggleVerificationVoice: (voiceProfileId: string) => void;
  onVerificationTextChange: (text: string) => void;
  onRunVerification: () => void;
};

export function VoiceEngineSettings({
  value,
  status,
  verification,
  voices,
  selectedVerificationVoiceIds,
  verificationText,
  verificationBusy,
  onChange,
  onToggleVerificationVoice,
  onVerificationTextChange,
  onRunVerification,
}: Props) {
  const verificationDisabled = selectedVerificationVoiceIds.length < 2 || verificationBusy;

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
        <dt>Verification</dt>
        <dd>{verification ? verificationLabel(verification.status) : "Checking"}</dd>
        {verification?.output_audio_path ? (
          <>
            <dt>Verified output</dt>
            <dd>{verification.output_audio_path}</dd>
          </>
        ) : null}
        {verification?.source_profile_details?.length ? (
          <>
            <dt>Verified sources</dt>
            <dd>{formatVerifiedSources(verification.source_profile_details)}</dd>
          </>
        ) : null}
        {verification?.error ? (
          <>
            <dt>Verification note</dt>
            <dd>{verification.error}</dd>
          </>
        ) : null}
      </dl>
      <label>
        Qwen verification text
        <textarea
          aria-label="Qwen verification text"
          value={verificationText}
          onChange={(event) => onVerificationTextChange(event.target.value)}
        />
      </label>
      {voices.length ? (
        <div className="verification-voices">
          {voices.map((voice) => (
            <label className="checkbox-row" key={voice.id}>
              <input
                aria-label={`Include ${voice.display_name} in Qwen verification`}
                type="checkbox"
                checked={selectedVerificationVoiceIds.includes(voice.id)}
                onChange={() => onToggleVerificationVoice(voice.id)}
              />
              <span>{voice.display_name}</span>
            </label>
          ))}
        </div>
      ) : null}
      <button type="button" disabled={verificationDisabled} onClick={onRunVerification}>
        {verificationBusy ? "Running Qwen verification" : "Run Qwen verification"}
      </button>
    </section>
  );
}

function verificationLabel(status: QwenVerificationReport["status"]) {
  if (status === "passed") return "Verification passed";
  if (status === "failed") return "Verification failed";
  return "Verification missing";
}

function formatVerifiedSources(details: NonNullable<QwenVerificationReport["source_profile_details"]>) {
  return details.map((source) => `${source.display_name} ${Math.round(source.weight * 100)}%`).join(" + ");
}
