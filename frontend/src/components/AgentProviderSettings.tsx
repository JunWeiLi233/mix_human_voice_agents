import type { AgentConfig, AgentProviderKind } from "../types";

type Props = {
  value: AgentConfig;
  onChange: (config: AgentConfig) => void;
};

export function AgentProviderSettings({ value, onChange }: Props) {
  function update(partial: Partial<AgentConfig>) {
    onChange({ ...value, ...partial });
  }

  function switchProvider(provider: AgentProviderKind) {
    if (provider === "ollama") {
      update({ provider, base_url: "http://127.0.0.1:11434", api_key: "", model: "llama3.1" });
    } else {
      update({ provider, base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini" });
    }
  }

  return (
    <section className="panel">
      <h2>Agent Provider</h2>
      <div className="segmented" role="group" aria-label="Agent provider">
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
      {value.provider === "openai_compatible" ? (
        <label>
          API key
          <input type="password" value={value.api_key} onChange={(event) => update({ api_key: event.target.value })} />
        </label>
      ) : null}
    </section>
  );
}

