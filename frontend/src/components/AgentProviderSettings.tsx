import type { AgentConfig, AgentProviderKind, AgentProviderVerificationReport } from "../types";

type Props = {
  value: AgentConfig;
  verification: AgentProviderVerificationReport | null;
  onChange: (config: AgentConfig) => void;
  testReply: string | null;
  testing: boolean;
  onTestProvider: () => void;
};

export function AgentProviderSettings({
  value,
  verification,
  onChange,
  testReply,
  testing,
  onTestProvider,
}: Props) {
  function update(partial: Partial<AgentConfig>) {
    onChange({ ...value, ...partial });
  }

  const presets: Record<AgentProviderKind, Pick<AgentConfig, "base_url" | "model" | "api_key">> = {
    openai: { base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini", api_key: value.api_key },
    anthropic: { base_url: "https://api.anthropic.com", model: "claude-sonnet-4-5", api_key: value.api_key },
    google: { base_url: "https://generativelanguage.googleapis.com/v1beta", model: "gemini-2.5-flash", api_key: value.api_key },
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
          className={value.provider === "google" ? "active" : ""}
          onClick={() => switchProvider("google")}
        >
          Gemini
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
          API key{value.provider === "openai_compatible" ? " (optional)" : ""}
          <input type="password" value={value.api_key} onChange={(event) => update({ api_key: event.target.value })} />
        </label>
      ) : null}
      <dl>
        <dt>Provider verification</dt>
        <dd>{verification ? providerVerificationLabel(verification.status) : "Checking"}</dd>
        {verification?.checked_at ? (
          <>
            <dt>Verified at</dt>
            <dd>{verification.checked_at}</dd>
          </>
        ) : null}
        {verification?.provider && verification.model ? (
          <>
            <dt>Verified model</dt>
            <dd>
              {verification.provider} / {verification.model}
            </dd>
          </>
        ) : null}
        {verification?.base_url ? (
          <>
            <dt>Verified endpoint</dt>
            <dd>{verification.base_url}</dd>
          </>
        ) : null}
        {verification?.error ? (
          <>
            <dt>Verification note</dt>
            <dd>{verification.error}</dd>
          </>
        ) : null}
      </dl>
      <button type="button" onClick={onTestProvider} disabled={testing}>
        {testing ? "Testing provider" : "Test provider"}
      </button>
      {testReply ? <p>{testReply}</p> : null}
    </section>
  );
}

function providerVerificationLabel(status: AgentProviderVerificationReport["status"]) {
  if (status === "passed") return "Provider verified";
  if (status === "failed") return "Provider failed";
  return "Provider missing";
}
