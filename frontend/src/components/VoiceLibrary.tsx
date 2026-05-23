import type { VoiceProfile } from "../types";

type Props = {
  voices: VoiceProfile[];
  onDeleteVoice: (voiceProfileId: string) => void;
};

export function VoiceLibrary({ voices, onDeleteVoice }: Props) {
  return (
    <section className="panel">
      <h2>Voice Library</h2>
      {voices.length === 0 ? (
        <p>No imported voices yet.</p>
      ) : (
        <div className="voice-list">
          {voices.map((voice) => (
            <div key={voice.id} className="voice-row">
              <div className="voice-details">
                <div>
                  {voice.display_name}{" "}
                  <span>{voice.consent.synthetic_voice_allowed ? "Consent ready" : "Consent missing"}</span>
                </div>
                <div className="voice-quality">{formatQuality(voice)}</div>
                <audio
                  aria-label={`Preview ${voice.display_name} voice sample`}
                  className="voice-preview"
                  controls
                  src={`/api/voices/${voice.id}/audio`}
                />
                <a
                  aria-label={`Download metadata for ${voice.display_name} voice`}
                  download={`${voice.id}.json`}
                  href={`/api/voices/${voice.id}/metadata`}
                >
                  Metadata
                </a>
                {voice.quality.warnings.length > 0 ? (
                  <ul className="voice-warnings">
                    {voice.quality.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
              <button type="button" onClick={() => onDeleteVoice(voice.id)}>
                Delete {voice.display_name} voice
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function formatQuality(voice: VoiceProfile) {
  const duration =
    voice.quality.duration_seconds === null ? "unknown duration" : `${voice.quality.duration_seconds.toFixed(1)}s`;
  const sampleRate =
    voice.quality.sample_rate_hz === null ? "unknown Hz" : `${voice.quality.sample_rate_hz} Hz`;
  const channels =
    voice.quality.channel_count === null
      ? "unknown channels"
      : `${voice.quality.channel_count} ${voice.quality.channel_count === 1 ? "channel" : "channels"}`;

  return `${duration} · ${sampleRate} · ${channels}`;
}
