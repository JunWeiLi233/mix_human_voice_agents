import type { VoiceBlend } from "../types";
import { useState } from "react";

type Props = {
  blend: VoiceBlend | null;
  onGenerate: (prompt: string) => void;
};

export function AgentChat({ blend, onGenerate }: Props) {
  const [prompt, setPrompt] = useState("Introduce yourself as a disclosed synthetic mixed voice assistant.");

  return (
    <section className="panel chat-panel">
      <h2>Agent Chat</h2>
      <textarea aria-label="Agent prompt text" value={prompt} onChange={(event) => setPrompt(event.target.value)} />
      <button type="button" disabled={!blend} onClick={() => onGenerate(prompt)}>
        Generate AI Voice
      </button>
    </section>
  );
}
