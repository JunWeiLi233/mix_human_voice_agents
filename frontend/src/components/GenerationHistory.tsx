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
              {item.synthetic_label} using {item.source_profile_ids.join(" + ")}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

