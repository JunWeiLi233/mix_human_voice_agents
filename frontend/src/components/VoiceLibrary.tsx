import type { VoiceProfile } from "../types";

type Props = {
  voices: VoiceProfile[];
};

export function VoiceLibrary({ voices }: Props) {
  return (
    <section className="panel">
      <h2>Voice Library</h2>
      {voices.length === 0 ? (
        <p>No imported voices yet.</p>
      ) : (
        <div className="voice-list">
          {voices.map((voice) => (
            <div key={voice.id}>
              {voice.display_name} <span>{voice.consent.synthetic_voice_allowed ? "Consent ready" : "Consent missing"}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
