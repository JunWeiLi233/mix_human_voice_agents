import { useState } from "react";
import { validateLaunchManifest } from "../api";
import type { LaunchManifestValidationReport, LaunchReadinessReport } from "../types";

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

function readManifestFile(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      resolve(typeof reader.result === "string" ? reader.result : "");
    });
    reader.addEventListener("error", () => {
      reject(reader.error ?? new Error("Launch manifest could not be read."));
    });
    reader.readAsText(file);
  });
}

export function LaunchReadiness({ readiness }: Props) {
  const launchActions = readiness ? nextLaunchActions(readiness) : [];
  const [manifestValidation, setManifestValidation] = useState<LaunchManifestValidationReport | null>(null);
  const [isValidatingManifest, setIsValidatingManifest] = useState(false);

  async function handleManifestFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setIsValidatingManifest(true);
    try {
      const manifest = JSON.parse(await readManifestFile(file));
      setManifestValidation(await validateLaunchManifest(manifest));
    } catch (error) {
      setManifestValidation({
        status: "failed",
        error: error instanceof Error ? error.message : "Launch manifest could not be read.",
      });
    } finally {
      setIsValidatingManifest(false);
    }
  }

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
          <div className="launch-downloads">
            <a download="launch-readiness-report.json" href="/api/launch/readiness/report">
              Download launch readiness audit
            </a>
            <a download="launch-manifest.template.json" href="/api/launch/manifest-template">
              Download launch manifest template
            </a>
          </div>
          <div className="manifest-validator">
            <label className="file-button">
              <span>{isValidatingManifest ? "Validating manifest" : "Validate launch manifest"}</span>
              <input
                accept="application/json,.json"
                aria-label="Validate launch manifest file"
                type="file"
                onChange={(event) => {
                  void handleManifestFile(event.currentTarget.files?.[0]);
                }}
              />
            </label>
            {manifestValidation ? (
              <p className={manifestValidation.status === "passed" ? "manifest-pass" : "manifest-fail"}>
                {manifestValidation.status === "passed"
                  ? `Manifest dry run passed for ${manifestValidation.voice_count ?? 0} voices: ${(manifestValidation.speaker_display_names ?? []).join(", ")}`
                  : `Manifest dry run failed: ${manifestValidation.error ?? "Validation failed."}`}
              </p>
            ) : null}
          </div>
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
