import { Upload } from "lucide-react";

export function ImportVoice() {
  return (
    <section className="panel">
      <h2>Import Voice</h2>
      <button type="button" className="icon-button" aria-label="Import consented voice sample">
        <Upload size={18} />
      </button>
      <p>Every imported sample requires self or written permission before blending.</p>
    </section>
  );
}

