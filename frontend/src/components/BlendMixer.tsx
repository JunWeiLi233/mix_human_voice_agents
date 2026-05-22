import type { BlendDraftProfile, VoiceBlend } from "../types";

type Props = {
  blend: VoiceBlend | null;
  profiles: BlendDraftProfile[];
  onCreateBlend: () => void;
  onWeightChange: (voiceProfileId: string, weight: number) => void;
};

export function BlendMixer({ blend, profiles, onCreateBlend, onWeightChange }: Props) {
  const canBlend = profiles.length >= 2;

  return (
    <section className="panel">
      <h2>Blend Mixer</h2>
      {profiles.length > 0 ? (
        <div className="blend-weights">
          {profiles.map((profile) => (
            <label key={profile.voice_profile_id}>
              {profile.display_name}
              <input
                aria-label={`${profile.display_name} blend weight`}
                type="number"
                min="0.1"
                step="0.1"
                value={profile.weight}
                onChange={(event) => onWeightChange(profile.voice_profile_id, Number(event.target.value))}
              />
            </label>
          ))}
        </div>
      ) : null}
      <button type="button" disabled={!canBlend} onClick={onCreateBlend}>
        Create blend from imported voices
      </button>
      {!canBlend ? <p>Import at least two consented voices to create a mix.</p> : null}
      {blend ? (
        <dl>
          <dt>Name</dt>
          <dd>{blend.name}</dd>
          <dt>Label</dt>
          <dd>{blend.synthetic_label}</dd>
        </dl>
      ) : null}
    </section>
  );
}
