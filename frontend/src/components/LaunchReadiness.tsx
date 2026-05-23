import type { LaunchReadinessReport } from "../types";

type Props = {
  readiness: LaunchReadinessReport | null;
};

const LAUNCH_ACTIONS: Record<string, string> = {
  research_review: "Refresh docs/research-review.md with a current Last checked date.",
  imported_voices:
    "Generate a launch manifest with `python -m app.cli.run_launch_sequence --write-template launch-manifest.template.json`, then fill in two consented WAV voice samples with matching transcripts.",
  saved_blend: "Create and save a multi-reference blend from imported voices.",
  generated_audio: "Generate a Qwen mixed voice clip with imported source details.",
  agent_provider: "Run Test provider and keep the passed provider verification report.",
  qwen_runtime: "Install and load qwen-tts with the selected Qwen model.",
  qwen_verification: "Run Qwen verification with two imported voices and keep the passed report.",
};

function nextLaunchActions(readiness: LaunchReadinessReport) {
  if (readiness.next_actions?.length) {
    return readiness.next_actions.map((action) => action.action);
  }
  return readiness.checks
    .filter((check) => !check.passed)
    .map((check) => LAUNCH_ACTIONS[check.id])
    .filter((action): action is string => Boolean(action));
}

export function LaunchReadiness({ readiness }: Props) {
  const launchActions = readiness ? nextLaunchActions(readiness) : [];

  return (
    <section className="panel launch-readiness" aria-labelledby="launch-readiness-heading">
      <h2 id="launch-readiness-heading">Launch Readiness</h2>
      {readiness ? (
        <>
          <p className={readiness.status === "ready" ? "readiness-ready" : "readiness-blocked"}>
            {readiness.status === "ready" ? "Ready for launch verification" : "Blocked before launch"}
          </p>
          {readiness.checked_at ? (
            <dl>
              <dt>Checked at</dt>
              <dd>{readiness.checked_at}</dd>
            </dl>
          ) : null}
          <a download="launch-readiness-report.json" href="/api/launch/readiness/report">
            Download launch readiness audit
          </a>
          {launchActions.length > 0 ? (
            <div className="launch-actions" aria-labelledby="launch-actions-heading">
              <h3 id="launch-actions-heading">Next launch actions</h3>
              <ol>
                {launchActions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ol>
            </div>
          ) : null}
          {readiness.blocking_reasons.length > 0 ? (
            <ul className="readiness-reasons">
              {readiness.blocking_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : null}
          <ul className="readiness-checks">
            {readiness.checks.map((check) => (
              <li key={check.id}>
                <span>{check.passed ? "Pass" : "Needs work"}</span>
                <div>
                  <strong>{check.label}</strong>
                  <small>{check.detail}</small>
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p>Launch readiness is unavailable.</p>
      )}
    </section>
  );
}
