import type { LaunchArtifactsReport } from "../types";

type Props = {
  artifacts: LaunchArtifactsReport | null;
};

export function LaunchArtifactInventory({ artifacts }: Props) {
  return (
    <section className="panel launch-artifacts" aria-labelledby="launch-artifacts-heading">
      <h2 id="launch-artifacts-heading">Launch Artifact Inventory</h2>
      {artifacts ? (
        <>
          <dl className="artifact-stats">
            <div>
              <dt>Voices</dt>
              <dd>
                {artifacts.voice_count} total / {artifacts.usable_voice_count} usable /{" "}
                {artifacts.unusable_voice_count} unusable
              </dd>
            </div>
            <div>
              <dt>Blends</dt>
              <dd>
                {artifacts.blend_count} total / {artifacts.launch_eligible_blend_count} eligible /{" "}
                {artifacts.stale_blend_count} stale
              </dd>
            </div>
            <div>
              <dt>Generations</dt>
              <dd>
                {artifacts.generation_count} total / {artifacts.qwen_generation_count} Qwen /{" "}
                {artifacts.launch_eligible_generation_count} eligible
              </dd>
            </div>
            <div>
              <dt>Provider</dt>
              <dd>{artifacts.agent_provider.status}</dd>
            </div>
            <div>
              <dt>Qwen verification</dt>
              <dd>{artifacts.qwen_verification.status}</dd>
            </div>
            <div>
              <dt>Qwen runtime</dt>
              <dd>{artifacts.qwen_runtime.available ? artifacts.qwen_runtime.model_id ?? "available" : "unavailable"}</dd>
            </div>
          </dl>
          {artifacts.voices.some((voice) => !voice.launch_usable) ? (
            <div className="artifact-list">
              <h3>Unusable voices</h3>
              <ul>
                {artifacts.voices
                  .filter((voice) => !voice.launch_usable)
                  .map((voice) => (
                    <li key={voice.id}>
                      <code>{voice.id}</code> {voice.display_name}: {voice.unusable_reasons.join("; ")}
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}
          {artifacts.generations.some((generation) => !generation.launch_eligible) ? (
            <div className="artifact-list">
              <h3>Stale generations</h3>
              <ul>
                {artifacts.generations
                  .filter((generation) => !generation.launch_eligible)
                  .map((generation) => (
                    <li key={generation.id}>
                      <code>{generation.id}</code> {generation.tts_backend}: {generation.stale_reasons.join("; ")}
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}
          {artifacts.next_commands.length > 0 ? (
            <div className="artifact-list">
              <h3>Next artifact commands</h3>
              <ul>
                {artifacts.next_commands.map((command) => (
                  <li key={command}>
                    <code>{command}</code>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : (
        <p>Launch artifact inventory is unavailable.</p>
      )}
    </section>
  );
}
