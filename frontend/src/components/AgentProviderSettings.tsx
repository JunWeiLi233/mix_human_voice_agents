import type { AgentConfig, AgentProviderKind } from "../types";

type Props = {
  value: AgentConfig;
  onChange: (config: AgentConfig) => void;
  testReply: string | null;
  testing: boolean;
  onTestProvider: () => void;
};

export function AgentProviderSettings({ value, onChange, testReply, testing, onTestProvider }: Props) {
  function update(partial: Partial<AgentConfig>) {
    onChange({ ...value, ...partial });
  }

  const presets: Record<AgentProviderKind, Pick<AgentConfig, "base_url" | "model" | "api_key">> = {
    openai: { base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini", api_key: value.api_key },
    anthropic: { base_url: "https://api.anthropic.com", model: "claude-sonnet-4-5", api_key: value.api_key },
    xai: { base_url: "https://api.x.ai/v1", model: "grok-4", api_key: value.api_key },
    openai_compatible: { base_url: "https://llm.example.test/v1", model: "custom-chat-model", api_key: value.api_key },
    ollama: { base_url: "http://127.0.0.1:11434", model: "llama3.1", api_key: "" },
  };

  function switchProvider(provider: AgentProviderKind) {
    update({ provider, ...presets[provider] });
  }

  return (
    <section className="panel">
      <h2>Agent Provider</h2>
      <div className="segmented" role="group" aria-label="Agent provider">
        <button
          type="button"
          className={value.provider === "openai" ? "active" : ""}
          onClick={() => switchProvider("openai")}
        >
          ChatGPT
        </button>
        <button
          type="button"
          className={value.provider === "anthropic" ? "active" : ""}
          onClick={() => switchProvider("anthropic")}
        >
          Claude
        </button>
        <button
          type="button"
          className={value.provider === "xai" ? "active" : ""}
          onClick={() => switchProvider("xai")}
        >
          Grok
        </button>
        <button
          type="button"
          className={value.provider === "openai_compatible" ? "active" : ""}
          onClick={() => switchProvider("openai_compatible")}
        >
          API
        </button>
        <button
          type="button"
          className={value.provider === "ollama" ? "active" : ""}
          onClick={() => switchProvider("ollama")}
        >
          Local
        </button>
      </div>
      <label>
        Base URL
        <input value={value.base_url} onChange={(event) => update({ base_url: event.target.value })} />
      </label>
      <label>
        Model
        <input value={value.model} onChange={(event) => update({ model: event.target.value })} />
      </label>
      {value.provider !== "ollama" ? (
        <label>
          API key
          <input type="password" value={value.api_key} onChange={(event) => update({ api_key: event.target.value })} />
        </label>
      ) : null}
      <button type="button" onClick={onTestProvider} disabled={testing}>
        {testing ? "Testing provider" : "Test provider"}
      </button>
      {testReply ? <p>{testReply}</p> : null}
    </section>
  );
}
