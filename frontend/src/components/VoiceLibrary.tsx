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
              <div>
                {voice.display_name}{" "}
                <span>{voice.consent.synthetic_voice_allowed ? "Consent ready" : "Consent missing"}</span>
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
