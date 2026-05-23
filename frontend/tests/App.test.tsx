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
      if (url === "/api/launch/readiness") {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: [
            "Import at least two consented voice profiles.",
            "Run Qwen runtime verification successfully before launch.",
          ],
          checks: [
            {
              id: "imported_voices",
              label: "Imported voices",
              passed: false,
              detail: "0 imported voices",
            },
            {
              id: "qwen_verification",
              label: "Qwen verification",
              passed: false,
              detail: "No passed Qwen runtime verification report",
            },
          ],
        });
      }
      return new Response("not found", { status: 404 });
    });

    render(<App />);

    expect(screen.getByText("Mixed Voice Agent Studio")).toBeInTheDocument();
    expect(screen.getByText("Voice Library")).toBeInTheDocument();
    expect(await screen.findByText("Launch Readiness")).toBeInTheDocument();
    expect(screen.getByText("Blocked before launch")).toBeInTheDocument();
    expect(screen.getByText("Run Qwen runtime verification successfully before launch.")).toBeInTheDocument();
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

    fireEvent.click(screen.getByLabelText("Confirm voice consent"));
    fireEvent.change(screen.getByLabelText("Confirmed by"), { target: { value: "Junwei" } });
    expect(screen.getByLabelText("Import consented voice sample")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Reference transcript"), {
      target: { value: "Alice reads a clean reference sentence for Qwen cloning." },
    });
    expect(screen.getByLabelText("Import consented voice sample")).toBeEnabled();
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
            prompt: "Summarize launch readiness.",
            agent_reply: "The mixed voice agent still needs Qwen verification.",
            source_profile_ids: ["voice_saved_a", "voice_saved_b"],
            source_profiles: [
              { voice_profile_id: "voice_saved_a", weight: 0.6 },
              { voice_profile_id: "voice_saved_b", weight: 0.4 },
            ],
            source_profile_details: [
              {
                voice_profile_id: "voice_saved_a",
                display_name: "Saved Alice",
                weight: 0.6,
                consent_confirmed_by: "Junwei",
                allowed_uses: ["private_agent_voice", "local_audio_export"],
                reference_text_present: true,
              },
              {
                voice_profile_id: "voice_saved_b",
                display_name: "Saved Bob",
                weight: 0.4,
                consent_confirmed_by: "Junwei",
                allowed_uses: ["private_agent_voice", "local_audio_export"],
                reference_text_present: true,
              },
            ],
            watermark: {
              type: "metadata",
              label: "synthetic mixed voice",
              disclosure: "Generated audio is synthetic and mixed from consented imported voice profiles.",
            },
            agent_trace: { provider: "openai", model: "gpt-4.1-mini" },
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
          source_profile_details: [
            {
              voice_profile_id: "voice_saved_a",
              display_name: "Saved Alice",
              weight: 0.6,
              consent_confirmed_by: "Junwei",
              allowed_uses: ["private_agent_voice", "local_audio_export"],
              reference_text_present: true,
            },
            {
              voice_profile_id: "voice_saved_b",
              display_name: "Saved Bob",
              weight: 0.4,
              consent_confirmed_by: "Junwei",
              allowed_uses: ["private_agent_voice", "local_audio_export"],
              reference_text_present: true,
            },
          ],
          blend_strategy: "multi_reference_prompt",
          output_audio_path: "data/generations/qwen_verify.wav",
          text: "verification text",
        });
      }

      if (url === "/api/launch/readiness" && !init) {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: ["Run Qwen runtime verification successfully before launch."],
          checks: [
            {
              id: "imported_voices",
              label: "Imported voices",
              passed: false,
              detail: "0 imported voices",
            },
            {
              id: "qwen_verification",
              label: "Qwen verification",
              passed: true,
              detail: "Verification passed",
            },
          ],
        });
      }

      if (url === "/api/tts/qwen/verification" && init?.method === "POST") {
        const body = JSON.parse(init.body?.toString() ?? "{}");
        return jsonResponse({
          status: "passed",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          voice_profile_ids: body.voice_profile_ids,
          source_profile_details: [
            {
              voice_profile_id: "voice_alice",
              display_name: "Alice",
              weight: 0.5,
              consent_confirmed_by: "Junwei",
              allowed_uses: ["private_agent_voice", "local_audio_export"],
              reference_text_present: true,
            },
            {
              voice_profile_id: "voice_bob",
              display_name: "Bob",
              weight: 0.5,
              consent_confirmed_by: "Junwei",
              allowed_uses: ["private_agent_voice", "local_audio_export"],
              reference_text_present: true,
            },
          ],
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
        const totalWeight = body.profiles.reduce((sum: number, profile: { weight: number }) => sum + profile.weight, 0);
        return jsonResponse({
          id: "blend_1",
          name: body.name,
          strategy: body.strategy,
          profiles: body.profiles.map((profile: { voice_profile_id: string; weight: number }) => ({
            ...profile,
            weight: profile.weight / totalWeight,
          })),
          synthetic_label: "synthetic mixed voice",
        });
      }

      if (url === "/api/agent/reply") {
        const body = JSON.parse(init?.body?.toString() ?? "{}");
        return jsonResponse({
          reply: `API reply to ${body.prompt}`,
          provider: body.config.provider,
          model: body.config.model,
          base_url: body.config.base_url,
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
          source_profiles: body.blend.profiles,
          source_profile_details: [
            {
              voice_profile_id: "voice_alice",
              display_name: "Alice",
              weight: 0.35,
              consent_confirmed_by: "Junwei",
              allowed_uses: ["private_agent_voice", "local_audio_export"],
              reference_text_present: true,
            },
            {
              voice_profile_id: "voice_bob",
              display_name: "Bob",
              weight: 0.15,
              consent_confirmed_by: "Junwei",
              allowed_uses: ["private_agent_voice", "local_audio_export"],
              reference_text_present: true,
            },
            {
              voice_profile_id: "voice_cara",
              display_name: "Cara",
              weight: 0.5,
              consent_confirmed_by: "Junwei",
              allowed_uses: ["private_agent_voice", "local_audio_export"],
              reference_text_present: true,
            },
          ],
          watermark: {
            type: "metadata",
            label: body.blend.synthetic_label,
            disclosure: "Generated audio is synthetic and mixed from consented imported voice profiles.",
          },
          qwen_runtime_config: body.qwen_runtime_config,
          agent_trace: body.agent_trace,
          synthetic_label: body.blend.synthetic_label,
          tts_backend: body.tts_backend,
        });
      }

      return new Response("not found", { status: 404 });
    });

    render(<App />);
    await waitFor(() => expect(screen.getByText("No imported voices yet.")).toBeInTheDocument());
    await screen.findByText("Installed");
    expect((await screen.findAllByText("Verification passed")).length).toBeGreaterThan(0);
    expect(screen.getByText("data/generations/qwen_verify.wav")).toBeInTheDocument();
    expect(screen.getByText("Saved Alice 60% + Saved Bob 40%")).toBeInTheDocument();
    await screen.findByRole("button", { name: "Saved Alice + Bob" });
    expect(screen.getByRole("button", { name: "Generate AI Voice" })).toBeEnabled();
    await screen.findByText("synthetic mixed voice using Saved Alice 60% + Saved Bob 40%");
    expect(screen.getByText("Prompt: Summarize launch readiness.")).toBeInTheDocument();
    expect(screen.getByText("Reply: The mixed voice agent still needs Qwen verification.")).toBeInTheDocument();
    expect(
      screen.getByText("Generated audio is synthetic and mixed from consented imported voice profiles."),
    ).toBeInTheDocument();
    expect(screen.getByText("Agent: openai / gpt-4.1-mini")).toBeInTheDocument();
    expect(screen.getByLabelText("Play synthetic mixed voice")).toHaveAttribute(
      "src",
      "/api/generations/generation_existing/audio",
    );
    expect(screen.getByRole("link", { name: "Download audio for generation_existing" })).toHaveAttribute(
      "href",
      "/api/generations/generation_existing/audio",
    );
    expect(screen.getByRole("link", { name: "Download metadata for generation_existing" })).toHaveAttribute(
      "href",
      "/api/generations/generation_existing/metadata",
    );

    fireEvent.click(screen.getByRole("button", { name: "API" }));
    fireEvent.click(screen.getByRole("button", { name: "Claude" }));
    expect(screen.getByLabelText("Base URL")).toHaveValue("https://api.anthropic.com");
    expect(screen.getByLabelText("Model")).toHaveValue("claude-sonnet-4-5");
    fireEvent.click(screen.getByRole("button", { name: "Grok" }));
    expect(screen.getByLabelText("Base URL")).toHaveValue("https://api.x.ai/v1");
    expect(screen.getByLabelText("Model")).toHaveValue("grok-4");
    fireEvent.click(screen.getByRole("button", { name: "Gemini" }));
    expect(screen.getByLabelText("Base URL")).toHaveValue("https://generativelanguage.googleapis.com/v1beta");
    expect(screen.getByLabelText("Model")).toHaveValue("gemini-2.5-flash");
    fireEvent.click(screen.getByRole("button", { name: "ChatGPT" }));
    expect(screen.getByLabelText("Base URL")).toHaveValue("https://api.openai.com/v1");
    expect(screen.getByLabelText("Model")).toHaveValue("gpt-4.1-mini");
    fireEvent.change(screen.getByLabelText("Base URL"), { target: { value: "https://llm.example.test/v1" } });
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "custom-voice-agent-model" } });
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-test" } });
    fireEvent.click(screen.getByRole("button", { name: "Qwen3-TTS" }));
    fireEvent.change(screen.getByLabelText("Qwen model id"), {
      target: { value: "Qwen/Qwen3-TTS-12Hz-1.7B-Base" },
    });
    fireEvent.change(screen.getByLabelText("Qwen device map"), { target: { value: "cuda:0" } });
    fireEvent.change(screen.getByLabelText("Qwen dtype"), { target: { value: "bfloat16" } });
    fireEvent.change(screen.getByLabelText("Qwen attention implementation"), {
      target: { value: "flash_attention_2" },
    });
    fireEvent.change(screen.getByLabelText("Confirmed by"), { target: { value: "Junwei" } });
    fireEvent.change(screen.getByLabelText("Consent notes"), {
      target: { value: "Written consent captured for local private mixed voice testing." },
    });
    fireEvent.change(screen.getByLabelText("Reference transcript"), {
      target: { value: "Alice reads a clean reference sentence for Qwen cloning." },
    });
    fireEvent.click(screen.getByLabelText("Confirm voice consent"));

    await importNamedVoice("Alice");
    expect(await screen.findByText("8.0s · 24000 Hz · 1 channel")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Reference transcript"), {
      target: { value: "Bob reads a clean reference sentence for Qwen cloning." },
    });
    await importNamedVoice("Bob");
    fireEvent.change(screen.getByLabelText("Reference transcript"), {
      target: { value: "Cara reads a clean reference sentence for Qwen cloning." },
    });
    await importNamedVoice("Cara");
    fireEvent.click(screen.getByLabelText("Include Cara in Qwen verification"));
    fireEvent.change(screen.getByLabelText("Alice blend weight"), { target: { value: "0.7" } });
    fireEvent.change(screen.getByLabelText("Bob blend weight"), { target: { value: "0.3" } });
    fireEvent.change(screen.getByLabelText("Qwen verification text"), {
      target: { value: "Studio verification with imported Alice and Bob." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run Qwen verification" }));

    await screen.findByText("data/generations/studio_qwen_verify.wav");
    expect(screen.getByText("Alice 50% + Bob 50%")).toBeInTheDocument();
    const verificationCall = requestJson(fetchMock, "/api/tts/qwen/verification");
    expect(verificationCall).toMatchObject({
      voice_profile_ids: ["voice_alice", "voice_bob"],
      text: "Studio verification with imported Alice and Bob.",
      model_id: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
      device_map: "cuda:0",
      dtype: "bfloat16",
      attn_implementation: "flash_attention_2",
    });

    fireEvent.click(screen.getByRole("button", { name: "Create blend from imported voices" }));
    await screen.findByRole("button", { name: "Alice + Bob + Cara" });

    const prompt = "Tell me the launch status using the mixed voice.";
    fireEvent.change(screen.getByLabelText("Agent prompt text"), { target: { value: prompt } });
    fireEvent.click(screen.getByRole("button", { name: "Generate AI Voice" }));

    await screen.findByText("synthetic mixed voice using Alice 35% + Bob 15% + Cara 50%");
    expect(screen.getAllByLabelText("Play synthetic mixed voice")[0]).toHaveAttribute(
      "src",
      "/api/generations/generation_1/audio",
    );
    expect(screen.getByRole("link", { name: "Download metadata for generation_1" })).toHaveAttribute(
      "href",
      "/api/generations/generation_1/metadata",
    );

    const agentCall = requestJson(fetchMock, "/api/agent/reply");
    expect(agentCall).toMatchObject({
      prompt,
      config: {
        provider: "openai",
        base_url: "https://llm.example.test/v1",
        model: "custom-voice-agent-model",
        api_key: "sk-test",
      },
    });

    const blendCall = requestJson(fetchMock, "/api/blends");
    expect(blendCall).toMatchObject({
      name: "Alice + Bob + Cara",
      strategy: "multi_reference_prompt",
      profiles: [
        { voice_profile_id: "voice_alice", weight: 0.7 },
        { voice_profile_id: "voice_bob", weight: 0.3 },
        { voice_profile_id: "voice_cara", weight: 1 },
      ],
    });

    const generationCall = requestJson(fetchMock, "/api/generate");
    expect(generationCall).toMatchObject({
      prompt,
      agent_reply: `API reply to ${prompt}`,
      agent_trace: {
        provider: "openai",
        model: "custom-voice-agent-model",
        base_url: "https://llm.example.test/v1",
      },
      tts_backend: "qwen3_tts",
      qwen_runtime_config: {
        model_id: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map: "cuda:0",
        dtype: "bfloat16",
        attn_implementation: "flash_attention_2",
      },
    });
  });

  it("lets the user test the selected agent provider before generating voice", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = input.toString();
      if (url === "/api/voices" && !init) {
        return jsonResponse([]);
      }
      if (url === "/api/generations" && !init) {
        return jsonResponse([]);
      }
      if (url === "/api/blends" && !init) {
        return jsonResponse([]);
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
          status: "missing",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          voice_profile_ids: [],
        });
      }
      if (url === "/api/launch/readiness" && !init) {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: [],
          checks: [],
        });
      }
      if (url === "/api/agent/provider-verification" && init?.method === "POST") {
        const body = JSON.parse(init.body?.toString() ?? "{}");
        return jsonResponse({
          status: "passed",
          reply: "Provider test reply",
          provider: body.config.provider,
          model: body.config.model,
          report_path: "data/agent-provider-verification-report.json",
        });
      }
      return new Response("not found", { status: 404 });
    });

    render(<App />);
    await screen.findByText("No imported voices yet.");

    fireEvent.click(screen.getByRole("button", { name: "Claude" }));
    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "sk-test" } });
    fireEvent.click(screen.getByRole("button", { name: "Test provider" }));

    expect(await screen.findByText("Provider test reply")).toBeInTheDocument();
    expect(requestJson(fetchMock, "/api/agent/provider-verification")).toMatchObject({
      prompt: "Reply with one short sentence confirming this provider is connected.",
      config: {
        provider: "anthropic",
        base_url: "https://api.anthropic.com",
        model: "claude-sonnet-4-5",
        api_key: "sk-test",
      },
    });
  });

  it("shows the persisted agent provider verification report on load", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = input.toString();
      if (url === "/api/voices" && !init) {
        return jsonResponse([]);
      }
      if (url === "/api/generations" && !init) {
        return jsonResponse([]);
      }
      if (url === "/api/blends" && !init) {
        return jsonResponse([]);
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
          status: "missing",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          checked_at: "2026-05-23T00:00:00+00:00",
          voice_profile_ids: [],
        });
      }
      if (url === "/api/agent/provider-verification" && !init) {
        return jsonResponse({
          status: "passed",
          report_path: "data/agent-provider-verification-report.json",
          checked_at: "2026-05-23T00:00:00+00:00",
          provider: "openai_compatible",
          model: "local-qwen-agent",
          base_url: "http://127.0.0.1:1234/v1",
          reply: "Provider ready.",
        });
      }
      if (url === "/api/launch/readiness" && !init) {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: [],
          checks: [],
        });
      }
      return new Response("not found", { status: 404 });
    });

    render(<App />);

    expect(await screen.findByText("Provider verified")).toBeInTheDocument();
    expect(screen.getByText("openai_compatible / local-qwen-agent")).toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:1234/v1")).toBeInTheDocument();
    expect(screen.getByLabelText("Base URL")).toHaveValue("http://127.0.0.1:1234/v1");
    expect(screen.getByLabelText("Model")).toHaveValue("local-qwen-agent");
    expect(screen.getByLabelText("API key (optional)")).toHaveValue("");
  });

  it("lets the user delete an imported voice and removes dependent blends", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = input.toString();

      if (url === "/api/voices" && !init) {
        return jsonResponse([
          voiceProfile("voice_alice", "Alice"),
          voiceProfile("voice_bob", "Bob", ["Reference audio appears clipped; record a cleaner sample."]),
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

      if (url === "/api/launch/readiness" && !init) {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: ["Run Qwen runtime verification successfully before launch."],
          checks: [
            {
              id: "imported_voices",
              label: "Imported voices",
              passed: true,
              detail: "3 imported voices",
            },
            {
              id: "qwen_verification",
              label: "Qwen verification",
              passed: false,
              detail: "Verification failed",
            },
          ],
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
    expect(await screen.findByText("Reference audio appears clipped; record a cleaner sample.")).toBeInTheDocument();
    expect(screen.getByLabelText("Preview Bob voice sample")).toHaveAttribute("src", "/api/voices/voice_bob/audio");
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

function voiceProfile(id: string, displayName: string, warnings: string[] = []) {
  return {
    id,
    display_name: displayName,
    source_audio_path: `data/voices/${id}/sample.wav`,
    cleaned_audio_path: `data/voices/${id}/sample.wav`,
    reference_text: `${displayName} reads a clean reference sentence for Qwen cloning.`,
    quality: {
      file_name: "sample.wav",
      size_bytes: 160044,
      format: "wav",
      duration_seconds: 5,
      sample_rate_hz: 16000,
      channel_count: 1,
      warnings,
    },
    consent: {
      voice_profile_id: id,
      speaker_display_name: displayName,
      synthetic_voice_allowed: true,
      allowed_uses: ["private_agent_voice", "local_audio_export"],
    },
  };
}

type FetchMock = {
  mock: {
    calls: Array<[RequestInfo | URL, RequestInit?]>;
  };
};

function requestJson(fetchMock: FetchMock, path: string) {
  const call = fetchMock.mock.calls.find(([input, init]) => input.toString() === path && init?.method === "POST");
  if (!call) {
    throw new Error(`Missing ${path} request`);
  }
  return JSON.parse(call[1]?.body?.toString() ?? "{}");
}
