import type { VoiceBlend } from "../types";

type Props = {
  blend: VoiceBlend | null;
  onGenerate: (prompt: string) => void;
};

export function AgentChat({ blend, onGenerate }: Props) {
  const prompt = "Introduce yourself as a disclosed synthetic mixed voice assistant.";

  return (
    <section className="panel chat-panel">
      <h2>Agent Chat</h2>
      <textarea aria-label="Agent prompt text" defaultValue={prompt} />
      <button type="button" disabled={!blend} onClick={() => onGenerate(prompt)}>
        Generate AI Voice
      </button>
    </section>
  );
}

