import { Upload } from "lucide-react";
import { useState } from "react";
import { importVoice } from "../api";
import type { VoiceProfile } from "../types";

type Props = {
  onImported?: (profile: VoiceProfile) => void;
};

export function ImportVoice({ onImported }: Props) {
  const [displayName, setDisplayName] = useState("Alice");
  const [busy, setBusy] = useState(false);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    try {
      const profile = await importVoice(file, displayName);
      onImported?.(profile);
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
      <label className="file-button">
        <Upload size={18} />
        <span>{busy ? "Importing" : "Import consented sample"}</span>
        <input
          aria-label="Import consented voice sample"
          type="file"
          accept="audio/*"
          disabled={busy}
          onChange={(event) => void handleFile(event.target.files?.[0])}
        />
      </label>
      <p>Every imported sample requires self or written permission before blending.</p>
    </section>
  );
}
