import type { VoiceBlend, VoiceProfile } from "../types";

type Props = {
  blend: VoiceBlend | null;
  voices: VoiceProfile[];
  onCreateBlend: () => void;
};

export function BlendMixer({ blend, voices, onCreateBlend }: Props) {
  const canBlend = voices.length >= 2;

  return (
    <section className="panel">
      <h2>Blend Mixer</h2>
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
