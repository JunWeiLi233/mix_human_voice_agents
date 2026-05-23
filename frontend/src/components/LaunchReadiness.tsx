import type { LaunchReadinessReport } from "../types";

type Props = {
  readiness: LaunchReadinessReport | null;
};

export function LaunchReadiness({ readiness }: Props) {
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
