import { Upload } from "lucide-react";
import { useState } from "react";
import { importVoice } from "../api";
import type { VoiceProfile } from "../types";

type Props = {
  onImported?: (profile: VoiceProfile) => void;
};

export function ImportVoice({ onImported }: Props) {
  const [displayName, setDisplayName] = useState("Alice");
  const [confirmedBy, setConfirmedBy] = useState("local_user");
  const [notes, setNotes] = useState("Confirmed self or written permission for private synthetic voice use.");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canImport = consentConfirmed && confirmedBy.trim().length > 0;

  async function handleFile(file: File | undefined) {
    if (!file) return;
    if (!canImport) {
      setError("Confirm consent before importing a voice sample.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const profile = await importVoice(file, displayName, {
        confirmed_by: confirmedBy,
        notes,
      });
      onImported?.(profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Import Voice</h2>
      <label>
        Speaker name
        <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
      </label>
      <label>
        Confirmed by
        <input value={confirmedBy} onChange={(event) => setConfirmedBy(event.target.value)} />
      </label>
      <label>
        Consent notes
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
      </label>
      <label className="checkbox-row">
        <input
          aria-label="Confirm voice consent"
          type="checkbox"
          checked={consentConfirmed}
          onChange={(event) => setConsentConfirmed(event.target.checked)}
        />
        <span>I confirm this speaker is me or gave written permission for private synthetic voice use.</span>
      </label>
      <label className="file-button">
        <Upload size={18} />
        <span>{busy ? "Importing" : "Import consented sample"}</span>
        <input
          aria-label="Import consented voice sample"
          type="file"
          accept="audio/*"
          disabled={busy || !canImport}
          onChange={(event) => void handleFile(event.target.files?.[0])}
        />
      </label>
      {error ? (
        <p className="inline-error" role="alert">
          {error}
        </p>
      ) : null}
      <p>Import a 5-30 second WAV sample with self or written permission before blending.</p>
    </section>
  );
}
