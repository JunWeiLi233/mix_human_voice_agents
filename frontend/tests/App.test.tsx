import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";

describe("App", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the mixed voice studio", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = input.toString();
      if (url === "/api/voices") {
        return jsonResponse([]);
      }
      if (url === "/api/tts/qwen/status") {
        return jsonResponse({
          backend: "qwen3_tts",
          available: false,
          model_id: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
          message: 'qwen-tts is not installed. Run: python -m pip install -e ".[qwen]"',
        });
      }
      return new Response("not found", { status: 404 });
    });

    render(<App />);

    expect(screen.getByText("Mixed Voice Agent Studio")).toBeInTheDocument();
    expect(screen.getByText("Voice Library")).toBeInTheDocument();
    expect(screen.getByText("Blend Mixer")).toBeInTheDocument();
    expect(screen.getByText("Agent Provider")).toBeInTheDocument();
    expect(screen.getByText("Voice Engine")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Qwen3-TTS" })).toBeInTheDocument();
    expect(await screen.findByText("Qwen/Qwen3-TTS-12Hz-0.6B-Base")).toBeInTheDocument();
    expect(screen.getByText("Not installed")).toBeInTheDocument();
    expect(screen.getByText("No imported voices yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create blend from imported voices" })).toBeDisabled();
    expect(screen.getByLabelText("Import consented voice sample")).toBeDisabled();
  });

  it("lets the user configure an API model, import voices, blend them, and generate with Qwen", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = input.toString();

      if (url === "/api/voices" && !init) {
        return jsonResponse([]);
      }

      if (url === "/api/tts/qwen/status" && !init) {
        return jsonResponse({
          backend: "qwen3_tts",
          available: true,
          model_id: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
          message: "qwen-tts package is importable. Verify with consented samples before launch.",
        });
      }

      if (url === "/api/voices" && init?.method === "POST") {
        const form = init.body as FormData;
        const displayName = form.get("speaker_display_name")?.toString() ?? "Imported";
        if (form.get("confirmed_by") !== "Junwei") {
          return new Response("missing confirmed_by", { status: 400 });
        }
        if (form.get("notes") !== "Written consent captured for local private mixed voice testing.") {
          return new Response("missing consent notes", { status: 400 });
        }
        return jsonResponse({
          id: `voice_${displayName.toLowerCase()}`,
          display_name: displayName,
          consent: {
            speaker_display_name: displayName,
            consent_type: "self_or_written_permission",
            allowed_uses: ["private_agent_voice", "local_audio_export"],
            confirmed_by: "local_user",
            synthetic_voice_allowed: true,
            notes: "Confirmed in local prototype UI.",
          },
          source_audio_path: `data/voices/${displayName}/source.wav`,
          cleaned_audio_path: `data/voices/${displayName}/source.wav`,
          quality: { duration_seconds: 8, sample_rate_hz: 24000, channel_count: 1, warnings: [] },
        });
      }

      if (url === "/api/blends") {
        const body = JSON.parse(init?.body?.toString() ?? "{}");
        return jsonResponse({
          id: "blend_1",
          name: body.name,
          strategy: body.strategy,
          profiles: body.profiles,
          synthetic_label: "synthetic mixed voice",
        });
      }

      if (url === "/api/agent/reply") {
        const body = JSON.parse(init?.body?.toString() ?? "{}");
        return jsonResponse({
          reply: `API reply to ${body.prompt}`,
          provider: body.config.provider,
          model: body.config.model,
        });
      }

      if (url === "/api/generate") {
        const body = JSON.parse(init?.body?.toString() ?? "{}");
        return jsonResponse({
          id: "generation_1",
          prompt: body.prompt,
          agent_reply: body.agent_reply,
          blend_id: body.blend.id,
          audio_path: "data/generations/generation_1.wav",
          metadata_path: "data/generations/generation_1.json",
          source_profile_ids: body.blend.profiles.map((profile: { voice_profile_id: string }) => profile.voice_profile_id),
          synthetic_label: body.blend.synthetic_label,
          tts_backend: body.tts_backend,
        });
      }

      return new Response("not found", { status: 404 });
    });

    render(<App />);
    await waitFor(() => expect(screen.getByText("No imported voices yet.")).toBeInTheDocument());
    await screen.findByText("Installed");

    fireEvent.click(screen.getByRole("button", { name: "API" }));
    fireEvent.change(screen.getByLabelText("Base URL"), { target: { value: "https://llm.example.test/v1" } });
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "custom-voice-agent-model" } });
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-test" } });
    fireEvent.click(screen.getByRole("button", { name: "Qwen3-TTS" }));
    fireEvent.change(screen.getByLabelText("Confirmed by"), { target: { value: "Junwei" } });
    fireEvent.change(screen.getByLabelText("Consent notes"), {
      target: { value: "Written consent captured for local private mixed voice testing." },
    });
    fireEvent.click(screen.getByLabelText("Confirm voice consent"));

    await importNamedVoice("Alice");
    await importNamedVoice("Bob");
    fireEvent.change(screen.getByLabelText("Alice blend weight"), { target: { value: "0.7" } });
    fireEvent.change(screen.getByLabelText("Bob blend weight"), { target: { value: "0.3" } });

    fireEvent.click(screen.getByRole("button", { name: "Create blend from imported voices" }));
    await screen.findByText("Alice + Bob");

    const prompt = "Tell me the launch status using the mixed voice.";
    fireEvent.change(screen.getByLabelText("Agent prompt text"), { target: { value: prompt } });
    fireEvent.click(screen.getByRole("button", { name: "Generate AI Voice" }));

    await screen.findByText("synthetic mixed voice using voice_alice + voice_bob");
    expect(screen.getByLabelText("Play synthetic mixed voice")).toHaveAttribute(
      "src",
      "/api/generations/generation_1/audio",
    );

    const agentCall = requestJson(fetchMock, "/api/agent/reply");
    expect(agentCall).toMatchObject({
      prompt,
      config: {
        provider: "openai_compatible",
        base_url: "https://llm.example.test/v1",
        model: "custom-voice-agent-model",
        api_key: "sk-test",
      },
    });

    const blendCall = requestJson(fetchMock, "/api/blends");
    expect(blendCall).toMatchObject({
      name: "Alice + Bob",
      strategy: "multi_reference_prompt",
      profiles: [
        { voice_profile_id: "voice_alice", weight: 0.7 },
        { voice_profile_id: "voice_bob", weight: 0.3 },
      ],
    });

    const generationCall = requestJson(fetchMock, "/api/generate");
    expect(generationCall).toMatchObject({
      prompt,
      agent_reply: `API reply to ${prompt}`,
      tts_backend: "qwen3_tts",
    });
  });
});

async function importNamedVoice(name: string) {
  fireEvent.change(screen.getByLabelText("Speaker name"), { target: { value: name } });
  fireEvent.change(screen.getByLabelText("Import consented voice sample"), {
    target: { files: [new File(["voice"], `${name}.wav`, { type: "audio/wav" })] },
  });
  await screen.findByLabelText(`${name} blend weight`);
}

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function requestJson(fetchMock: ReturnType<typeof vi.spyOn>, path: string) {
  const call = fetchMock.mock.calls.find(([input, init]) => input.toString() === path && init?.method === "POST");
  if (!call) {
    throw new Error(`Missing ${path} request`);
  }
  return JSON.parse(call[1]?.body?.toString() ?? "{}");
}
