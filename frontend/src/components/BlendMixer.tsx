import type { VoiceBlend } from "../types";

type Props = {
  blend: VoiceBlend | null;
  onCreateBlend: () => void;
};

export function BlendMixer({ blend, onCreateBlend }: Props) {
  return (
    <section className="panel">
      <h2>Blend Mixer</h2>
      <button type="button" onClick={onCreateBlend}>
        Create 50/50 demo blend
      </button>
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

