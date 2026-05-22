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
      if (url === "/api/generations") {
        return jsonResponse([]);
      }
      if (url === "/api/blends") {
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
      if (url === "/api/tts/qwen/verification") {
        return jsonResponse({
          status: "missing",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          voice_profile_ids: [],
          error: "Run python -m app.cli.verify_qwen_runtime with two consented voice profile ids.",
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
    expect(await screen.findByText("Verification missing")).toBeInTheDocument();
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

      if (url === "/api/generations" && !init) {
        return jsonResponse([
          {
            id: "generation_existing",
            audio_path: "data/generations/generation_existing.wav",
            metadata_path: "data/generations/generation_existing.json",
            source_profile_ids: ["voice_saved_a", "voice_saved_b"],
            synthetic_label: "synthetic mixed voice",
            blend_strategy: "local_development_wav",
            tts_backend: "local_development_wav",
          },
        ]);
      }

      if (url === "/api/blends" && !init) {
        return jsonResponse([
          {
            id: "blend_saved",
            name: "Saved Alice + Bob",
            strategy: "multi_reference_prompt",
            synthetic_label: "synthetic mixed voice",
            profiles: [
              { voice_profile_id: "voice_saved_a", weight: 0.6 },
              { voice_profile_id: "voice_saved_b", weight: 0.4 },
            ],
          },
        ]);
      }

      if (url === "/api/tts/qwen/status" && !init) {
        return jsonResponse({
          backend: "qwen3_tts",
          available: true,
          model_id: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
          message: "qwen-tts package is importable. Verify with consented samples before launch.",
        });
      }

      if (url === "/api/tts/qwen/verification" && !init) {
        return jsonResponse({
          status: "passed",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          voice_profile_ids: ["voice_saved_a", "voice_saved_b"],
          blend_strategy: "multi_reference_prompt",
          output_audio_path: "data/generations/qwen_verify.wav",
          text: "verification text",
        });
      }

      if (url === "/api/tts/qwen/verification" && init?.method === "POST") {
        const body = JSON.parse(init.body?.toString() ?? "{}");
        return jsonResponse({
          status: "passed",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          voice_profile_ids: body.voice_profile_ids,
          blend_strategy: "multi_reference_prompt",
          output_audio_path: "data/generations/studio_qwen_verify.wav",
          text: body.text,
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
        if (form.get("reference_text") !== `${displayName} reads a clean reference sentence for Qwen cloning.`) {
          return new Response("missing reference text", { status: 400 });
        }
        return jsonResponse({
          id: `voice_${displayName.toLowerCase()}`,
          display_name: displayName,
          reference_text: `${displayName} reads a clean reference sentence for Qwen cloning.`,
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
    await screen.findByText("Verification passed");
    expect(screen.getByText("data/generations/qwen_verify.wav")).toBeInTheDocument();
    await screen.findByRole("button", { name: "Saved Alice + Bob" });
    expect(screen.getByRole("button", { name: "Generate AI Voice" })).toBeEnabled();
    await screen.findByText("synthetic mixed voice using voice_saved_a + voice_saved_b");
    expect(screen.getByLabelText("Play synthetic mixed voice")).toHaveAttribute(
      "src",
      "/api/generations/generation_existing/audio",
    );

    fireEvent.click(screen.getByRole("button", { name: "API" }));
    fireEvent.change(screen.getByLabelText("Base URL"), { target: { value: "https://llm.example.test/v1" } });
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "custom-voice-agent-model" } });
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-test" } });
    fireEvent.click(screen.getByRole("button", { name: "Qwen3-TTS" }));
    fireEvent.change(screen.getByLabelText("Confirmed by"), { target: { value: "Junwei" } });
    fireEvent.change(screen.getByLabelText("Consent notes"), {
      target: { value: "Written consent captured for local private mixed voice testing." },
    });
    fireEvent.change(screen.getByLabelText("Reference transcript"), {
      target: { value: "Alice reads a clean reference sentence for Qwen cloning." },
    });
    fireEvent.click(screen.getByLabelText("Confirm voice consent"));

    await importNamedVoice("Alice");
    fireEvent.change(screen.getByLabelText("Reference transcript"), {
      target: { value: "Bob reads a clean reference sentence for Qwen cloning." },
    });
    await importNamedVoice("Bob");
    fireEvent.change(screen.getByLabelText("Alice blend weight"), { target: { value: "0.7" } });
    fireEvent.change(screen.getByLabelText("Bob blend weight"), { target: { value: "0.3" } });
    fireEvent.change(screen.getByLabelText("Qwen verification text"), {
      target: { value: "Studio verification with imported Alice and Bob." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run Qwen verification" }));

    await screen.findByText("data/generations/studio_qwen_verify.wav");
    const verificationCall = requestJson(fetchMock, "/api/tts/qwen/verification");
    expect(verificationCall).toMatchObject({
      voice_profile_ids: ["voice_alice", "voice_bob"],
      text: "Studio verification with imported Alice and Bob.",
    });

    fireEvent.click(screen.getByRole("button", { name: "Create blend from imported voices" }));
    await screen.findByRole("button", { name: "Alice + Bob" });

    const prompt = "Tell me the launch status using the mixed voice.";
    fireEvent.change(screen.getByLabelText("Agent prompt text"), { target: { value: prompt } });
    fireEvent.click(screen.getByRole("button", { name: "Generate AI Voice" }));

    await screen.findByText("synthetic mixed voice using voice_alice + voice_bob");
    expect(screen.getAllByLabelText("Play synthetic mixed voice")[0]).toHaveAttribute(
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

  it("lets the user delete an imported voice and removes dependent blends", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = input.toString();

      if (url === "/api/voices" && !init) {
        return jsonResponse([
          voiceProfile("voice_alice", "Alice"),
          voiceProfile("voice_bob", "Bob"),
          voiceProfile("voice_cara", "Cara"),
        ]);
      }

      if (url === "/api/blends" && !init) {
        return jsonResponse([
          {
            id: "blend_alice_bob",
            name: "Alice + Bob",
            strategy: "local_development_wav",
            synthetic_label: "synthetic mixed voice",
            profiles: [
              { voice_profile_id: "voice_alice", weight: 0.5 },
              { voice_profile_id: "voice_bob", weight: 0.5 },
            ],
          },
          {
            id: "blend_bob_cara",
            name: "Bob + Cara",
            strategy: "local_development_wav",
            synthetic_label: "synthetic mixed voice",
            profiles: [
              { voice_profile_id: "voice_bob", weight: 0.5 },
              { voice_profile_id: "voice_cara", weight: 0.5 },
            ],
          },
        ]);
      }

      if (url === "/api/generations" && !init) {
        return jsonResponse([
          {
            id: "generation_alice_bob",
            audio_path: "data/generations/generation_alice_bob.wav",
            metadata_path: "data/generations/generation_alice_bob.json",
            source_profile_ids: ["voice_alice", "voice_bob"],
            synthetic_label: "synthetic mixed voice",
            blend_strategy: "local_development_wav",
            tts_backend: "local_development_wav",
          },
          {
            id: "generation_bob_cara",
            audio_path: "data/generations/generation_bob_cara.wav",
            metadata_path: "data/generations/generation_bob_cara.json",
            source_profile_ids: ["voice_bob", "voice_cara"],
            synthetic_label: "synthetic mixed voice",
            blend_strategy: "local_development_wav",
            tts_backend: "local_development_wav",
          },
        ]);
      }

      if (url === "/api/tts/qwen/status" && !init) {
        return jsonResponse({
          backend: "qwen3_tts",
          available: false,
          model_id: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
          message: "qwen-tts is not installed.",
        });
      }

      if (url === "/api/tts/qwen/verification" && !init) {
        return jsonResponse({
          status: "failed",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          voice_profile_ids: ["voice_alice", "voice_bob"],
          error: "Qwen runtime failed.",
        });
      }

      if (url === "/api/voices/voice_alice" && init?.method === "DELETE") {
        return jsonResponse({
          deleted_voice_profile_id: "voice_alice",
          deleted_blend_ids: ["blend_alice_bob"],
          deleted_generation_ids: ["generation_alice_bob"],
        });
      }

      return new Response("not found", { status: 404 });
    });

    render(<App />);

    await screen.findByRole("button", { name: "Alice + Bob" });
    await screen.findByText("synthetic mixed voice using voice_alice + voice_bob");
    await screen.findByText("synthetic mixed voice using voice_bob + voice_cara");
    expect(screen.getByRole("button", { name: "Generate AI Voice" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Delete Alice voice" }));

    await waitFor(() => expect(screen.queryByText("Alice")).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Alice + Bob" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bob + Cara" })).toBeInTheDocument();
    expect(screen.queryByText("synthetic mixed voice using voice_alice + voice_bob")).not.toBeInTheDocument();
    expect(screen.getByText("synthetic mixed voice using voice_bob + voice_cara")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate AI Voice" })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledWith("/api/voices/voice_alice", { method: "DELETE" });
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

function voiceProfile(id: string, displayName: string) {
  return {
    id,
    display_name: displayName,
    source_audio_path: `data/voices/${id}/sample.wav`,
    cleaned_audio_path: `data/voices/${id}/sample.wav`,
    reference_text: `${displayName} reads a clean reference sentence for Qwen cloning.`,
    consent: {
      voice_profile_id: id,
      speaker_display_name: displayName,
      synthetic_voice_allowed: true,
      allowed_uses: ["private_agent_voice", "local_audio_export"],
    },
  };
}

function requestJson(fetchMock: ReturnType<typeof vi.spyOn>, path: string) {
  const call = fetchMock.mock.calls.find(([input, init]) => input.toString() === path && init?.method === "POST");
  if (!call) {
    throw new Error(`Missing ${path} request`);
  }
  return JSON.parse(call[1]?.body?.toString() ?? "{}");
}
