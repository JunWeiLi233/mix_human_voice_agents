import type { GenerationResult } from "../types";

type Props = {
  generations: GenerationResult[];
};

export function GenerationHistory({ generations }: Props) {
  return (
    <section className="panel">
      <h2>History</h2>
      {generations.length === 0 ? (
        <p>No generated clips yet.</p>
      ) : (
        <ul>
          {generations.map((item) => (
            <li key={item.id}>
              <div>
                {item.synthetic_label} using {formatGenerationSources(item)}
              </div>
              <audio controls aria-label={`Play ${item.synthetic_label}`} src={`/api/generations/${item.id}/audio`} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function formatGenerationSources(item: GenerationResult) {
  if (item.source_profiles?.length) {
    return item.source_profiles
      .map((profile) => `${profile.voice_profile_id} ${Math.round(profile.weight * 100)}%`)
      .join(" + ");
  }

  return item.source_profile_ids.join(" + ");
}
