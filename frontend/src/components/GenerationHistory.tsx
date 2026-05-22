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
              {item.agent_trace ? (
                <p>
                  Agent: {item.agent_trace.provider} / {item.agent_trace.model}
                </p>
              ) : null}
              {item.prompt ? <p>Prompt: {item.prompt}</p> : null}
              {item.agent_reply ? <p>Reply: {item.agent_reply}</p> : null}
              {item.watermark ? <p className="metadata-watermark">{item.watermark.disclosure}</p> : null}
              <audio controls aria-label={`Play ${item.synthetic_label}`} src={`/api/generations/${item.id}/audio`} />
              <div className="history-actions">
                <a
                  aria-label={`Download audio for ${item.id}`}
                  download={`${item.id}.wav`}
                  href={`/api/generations/${item.id}/audio`}
                >
                  Audio
                </a>
                <a
                  aria-label={`Download metadata for ${item.id}`}
                  download={`${item.id}.json`}
                  href={`/api/generations/${item.id}/metadata`}
                >
                  Metadata
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function formatGenerationSources(item: GenerationResult) {
  if (item.source_profile_details?.length) {
    return item.source_profile_details
      .map((profile) => `${profile.display_name} ${Math.round(profile.weight * 100)}%`)
      .join(" + ");
  }

  if (item.source_profiles?.length) {
    return item.source_profiles
      .map((profile) => `${profile.voice_profile_id} ${Math.round(profile.weight * 100)}%`)
      .join(" + ");
  }

  return item.source_profile_ids.join(" + ");
}
