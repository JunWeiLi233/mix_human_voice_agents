import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";

describe("App", () => {
  afterEach(() => {
    cleanup();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders the mixed voice studio", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
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
          checked_at: "2026-05-23T00:20:00+00:00",
          blocking_reasons: [
            "Import at least two consented voice profiles.",
            "Run Qwen runtime verification successfully before launch.",
          ],
          next_actions: [
            {
              check_id: "imported_voices",
              label: "Imported voices",
              action: "Backend action: import two consented source voices.",
              evidence: "0 imported voices",
            },
            {
              check_id: "qwen_verification",
              label: "Qwen verification",
              action: "Backend action: run Qwen verification with two profiles.",
              evidence: "No passed Qwen runtime verification report",
            },
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
      if (url === "/api/launch/manifest/validate" && init?.method === "POST") {
        return jsonResponse({
          status: "passed",
          mode: "dry_run",
          voice_count: 2,
          speaker_display_names: ["Alice", "Bob"],
          voice_diagnostics: [
            {
              index: 1,
              speaker_display_name: "Alice",
              audio: "samples/alice.wav",
              status: "passed",
              duration_seconds: 5,
              sample_rate_hz: 16000,
              channel_count: 1,
              warnings: [],
            },
            {
              index: 2,
              speaker_display_name: "Bob",
              audio: "samples/bob.wav",
              status: "failed",
              duration_seconds: 5,
              sample_rate_hz: 16000,
              channel_count: 1,
              warnings: ["Reference audio appears clipped; record a cleaner sample."],
              next_action: "Re-record this speaker as a clean 5-30 second WAV sample with no clipping.",
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
    expect(screen.getByText("2026-05-23T00:20:00+00:00")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download launch readiness audit" })).toHaveAttribute(
      "href",
      "/api/launch/readiness/report",
    );
    expect(screen.getByRole("link", { name: "Download launch manifest template" })).toHaveAttribute(
      "href",
      "/api/launch/manifest-template",
    );
    fireEvent.change(screen.getByLabelText("Validate launch manifest file"), {
      target: {
        files: [
          new File(
            [
              JSON.stringify({
                voices: [
                  { speaker_display_name: "Alice" },
                  { speaker_display_name: "Bob" },
                ],
              }),
            ],
            "launch-manifest.json",
            { type: "application/json" },
          ),
        ],
      },
    });
    expect(await screen.findByText("Manifest dry run passed for 2 voices: Alice, Bob")).toBeInTheDocument();
    expect(screen.getByText("Manifest voice diagnostics")).toBeInTheDocument();
    expect(screen.getByText("Alice: passed, 5s, 16000Hz, 1 channel")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Bob: failed, 5s, 16000Hz, 1 channel. Reference audio appears clipped; record a cleaner sample. Next: Re-record this speaker as a clean 5-30 second WAV sample with no clipping.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Next launch actions")).toBeInTheDocument();
    expect(screen.getByText("Backend action: import two consented source voices.")).toBeInTheDocument();
    expect(screen.getByText("Backend action: run Qwen verification with two profiles.")).toBeInTheDocument();
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

  it("switches between the studio, evidence, and launch interface pages", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
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
          message: "qwen-tts is not installed.",
        });
      }
      if (url === "/api/tts/qwen/verification") {
        return jsonResponse({
          status: "missing",
          tts_backend: "qwen3_tts",
          report_path: "data/qwen-runtime-verification-report.json",
          voice_profile_ids: [],
        });
      }
      if (url === "/api/launch/readiness") {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: ["Import at least two consented voice profiles."],
          checks: [],
        });
      }
      if (url === "/api/launch/artifacts") {
        return jsonResponse({
          voice_count: 1,
          usable_voice_count: 0,
          unusable_voice_count: 1,
          blend_count: 4,
          launch_eligible_blend_count: 0,
          stale_blend_count: 4,
          generation_count: 0,
          qwen_generation_count: 0,
          launch_eligible_generation_count: 0,
          stale_generation_count: 0,
          usable_voice_ids: [],
          launch_eligible_blend_ids: [],
          launch_eligible_generation_ids: [],
          agent_provider: { status: "missing" },
          qwen_verification: { status: "missing" },
          qwen_runtime: { available: true, model_id: "Qwen/Qwen3-TTS-12Hz-0.6B-Base" },
          voices: [
            {
              id: "voice_alice",
              display_name: "Alice",
              launch_usable: false,
              unusable_reasons: ["Audio quality warnings must be resolved before launch."],
            },
          ],
          blends: [],
          generations: [],
          next_commands: [
            "python -m app.cli.run_launch_sequence --write-template data/launch-sequence/launch-manifest.template.json",
          ],
        });
      }
      return new Response("not found", { status: 404 });
    });

    render(<App />);
    await screen.findByText("No imported voices yet.");

    expect(screen.getByRole("button", { name: "Studio page" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Import Voice")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Evidence page" }));

    expect(screen.getByRole("button", { name: "Evidence page" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Evidence Page")).toBeInTheDocument();
    expect(screen.getByText("Voice evidence and exports")).toBeInTheDocument();
    expect(screen.queryByText("Import Voice")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Launch page" }));

    expect(screen.getByRole("button", { name: "Launch page" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Launch Control Page")).toBeInTheDocument();
    expect(screen.getByText("Launch Readiness")).toBeInTheDocument();
    expect(await screen.findByText("Launch Artifact Inventory")).toBeInTheDocument();
    expect(screen.getByText("1 total / 0 usable / 1 unusable")).toBeInTheDocument();
    expect(screen.getByText("4 total / 0 eligible / 4 stale")).toBeInTheDocument();
    expect(
      screen.getByText((_content, element) =>
        element?.tagName.toLowerCase() === "li" &&
        element.textContent === "voice_alice Alice: Audio quality warnings must be resolved before launch.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "python -m app.cli.run_launch_sequence --write-template data/launch-sequence/launch-manifest.template.json",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Agent Provider")).toBeInTheDocument();
    expect(screen.queryByText("Voice evidence and exports")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Studio page" }));

    expect(screen.getByRole("button", { name: "Studio page" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Import Voice")).toBeInTheDocument();
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
            blend_id: "blend_saved",
            blend_name: "Saved Alice + Bob",
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
          checked_at: "2026-05-23T00:15:00+00:00",
          model_id: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
          device_map: "cuda:0",
          dtype: "bfloat16",
          attn_implementation: "flash_attention_2",
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
    expect(screen.getByText("2026-05-23T00:15:00+00:00")).toBeInTheDocument();
    expect(screen.getByText("data/generations/qwen_verify.wav")).toBeInTheDocument();
    expect(screen.getByLabelText("Qwen model id")).toHaveValue("Qwen/Qwen3-TTS-12Hz-1.7B-Base");
    expect(screen.getByLabelText("Qwen device map")).toHaveValue("cuda:0");
    expect(screen.getByLabelText("Qwen dtype")).toHaveValue("bfloat16");
    expect(screen.getByLabelText("Qwen attention implementation")).toHaveValue("flash_attention_2");
    expect(screen.getByText("Saved Alice 60% + Saved Bob 40%")).toBeInTheDocument();
    await screen.findByRole("button", { name: "Saved Alice + Bob" });
    expect(screen.getByRole("button", { name: "Generate AI Voice" })).toBeEnabled();
    await screen.findByText("synthetic mixed voice using Saved Alice 60% + Saved Bob 40%");
    expect(screen.getByText("Blend: Saved Alice + Bob")).toBeInTheDocument();
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

  it("lets the user record a consented WAV sample before importing", async () => {
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
          blocking_reasons: ["Import at least two consented voice profiles."],
          checks: [],
        });
      }
      if (url === "/api/voices" && init?.method === "POST") {
        const form = init.body as FormData;
        const file = form.get("file") as File;
        if (file.type !== "audio/wav") {
          return new Response("recording was not encoded as WAV", { status: 400 });
        }
        if (!file.name.endsWith(".wav")) {
          return new Response("recording did not use a WAV filename", { status: 400 });
        }
        return jsonResponse(voiceProfile("voice_recorded", form.get("speaker_display_name")?.toString() ?? "Recorded"));
      }
      return new Response("not found", { status: 404 });
    });
    const restoreRecorder = installAudioRecorderMock();

    try {
      render(<App />);
      await screen.findByText("No imported voices yet.");

      fireEvent.change(screen.getByLabelText("Speaker name"), { target: { value: "Recorded Alice" } });
      fireEvent.change(screen.getByLabelText("Confirmed by"), { target: { value: "Junwei" } });
      fireEvent.change(screen.getByLabelText("Reference transcript"), {
        target: { value: "Recorded Alice reads a clean reference sentence for Qwen cloning." },
      });
      fireEvent.click(screen.getByLabelText("Confirm voice consent"));

      fireEvent.click(screen.getByRole("button", { name: "Start microphone recording" }));
      await screen.findByRole("button", { name: "Stop microphone recording" });
      emitRecordingSeconds(5);
      fireEvent.click(screen.getByRole("button", { name: "Stop microphone recording" }));

      expect(await screen.findByText("Recorded Alice-recording.wav")).toBeInTheDocument();
      expect(screen.getByText("5.0s recorded")).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Import recorded sample" }));

      expect(await screen.findByLabelText("Recorded Alice blend weight")).toBeInTheDocument();
      const importCall = fetchMock.mock.calls.find(
        ([input, init]) => input.toString() === "/api/voices" && init?.method === "POST",
      );
      expect(importCall).toBeTruthy();
      const form = importCall?.[1]?.body as FormData;
      expect((form.get("file") as File).type).toBe("audio/wav");
      expect((form.get("file") as File).name).toBe("Recorded Alice-recording.wav");
      expect(form.get("reference_text")).toBe("Recorded Alice reads a clean reference sentence for Qwen cloning.");
    } finally {
      restoreRecorder();
    }
  });

  it("blocks recorded samples shorter than the launch voice minimum", async () => {
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
          voice_profile_ids: [],
        });
      }
      if (url === "/api/launch/readiness" && !init) {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: ["Import at least two consented voice profiles."],
          checks: [],
        });
      }
      if (url === "/api/voices" && init?.method === "POST") {
        throw new Error("Short recordings should not be imported");
      }
      return new Response("not found", { status: 404 });
    });
    const restoreRecorder = installAudioRecorderMock();

    try {
      render(<App />);
      await screen.findByText("No imported voices yet.");

      fireEvent.change(screen.getByLabelText("Reference transcript"), {
        target: { value: "Alice reads a clean reference sentence for Qwen cloning." },
      });
      fireEvent.click(screen.getByLabelText("Confirm voice consent"));

      fireEvent.click(screen.getByRole("button", { name: "Start microphone recording" }));
      await screen.findByRole("button", { name: "Stop microphone recording" });
      emitRecordingSeconds(4);
      fireEvent.click(screen.getByRole("button", { name: "Stop microphone recording" }));

      expect(await screen.findByText("4.0s recorded")).toBeInTheDocument();
      expect(screen.getByText("Record at least 5 seconds before importing.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Import recorded sample" })).toBeDisabled();
    } finally {
      restoreRecorder();
    }
  });

  it("automatically stops browser recordings at the launch voice maximum", async () => {
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
          voice_profile_ids: [],
        });
      }
      if (url === "/api/launch/readiness" && !init) {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: ["Import at least two consented voice profiles."],
          checks: [],
        });
      }
      if (url === "/api/voices" && init?.method === "POST") {
        throw new Error("Auto-stopped recordings should not import during this test");
      }
      return new Response("not found", { status: 404 });
    });
    const restoreRecorder = installAudioRecorderMock();

    try {
      render(<App />);
      await screen.findByText("No imported voices yet.");

      fireEvent.change(screen.getByLabelText("Reference transcript"), {
        target: { value: "Alice reads a clean reference sentence for Qwen cloning." },
      });
      fireEvent.click(screen.getByLabelText("Confirm voice consent"));

      fireEvent.click(screen.getByRole("button", { name: "Start microphone recording" }));
      await screen.findByRole("button", { name: "Stop microphone recording" });
      emitRecordingSeconds(31);

      expect(await screen.findByText("30.0s recorded")).toBeInTheDocument();
      expect(screen.queryByText("Record 30 seconds or less before importing.")).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Stop microphone recording" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Import recorded sample" })).toBeEnabled();
    } finally {
      restoreRecorder();
    }
  });

  it("blocks silent browser recordings before voice import", async () => {
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
          voice_profile_ids: [],
        });
      }
      if (url === "/api/launch/readiness" && !init) {
        return jsonResponse({
          status: "blocked",
          blocking_reasons: ["Import at least two consented voice profiles."],
          checks: [],
        });
      }
      if (url === "/api/voices" && init?.method === "POST") {
        throw new Error("Silent recordings should not be imported");
      }
      return new Response("not found", { status: 404 });
    });
    const restoreRecorder = installAudioRecorderMock();

    try {
      render(<App />);
      await screen.findByText("No imported voices yet.");

      fireEvent.change(screen.getByLabelText("Reference transcript"), {
        target: { value: "Alice reads a clean reference sentence for Qwen cloning." },
      });
      fireEvent.click(screen.getByLabelText("Confirm voice consent"));

      fireEvent.click(screen.getByRole("button", { name: "Start microphone recording" }));
      await screen.findByRole("button", { name: "Stop microphone recording" });
      emitSilentRecordingSeconds(5);
      fireEvent.click(screen.getByRole("button", { name: "Stop microphone recording" }));

      expect(await screen.findByText("5.0s recorded")).toBeInTheDocument();
      expect(screen.getByText("Recording must contain audible speech before importing.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Import recorded sample" })).toBeDisabled();
    } finally {
      restoreRecorder();
    }
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
          checked_at: "2026-05-23T00:05:00+00:00",
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
    expect(screen.getByText("2026-05-23T00:00:00+00:00")).toBeInTheDocument();
    expect(screen.getByLabelText("Base URL")).toHaveValue("http://127.0.0.1:1234/v1");
    expect(screen.getByLabelText("Model")).toHaveValue("local-qwen-agent");
    expect(screen.getByLabelText("API key (optional)")).toHaveValue("");
  });

  it("keeps non-secret API and local LLM settings across reloads", async () => {
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
          voice_profile_ids: [],
        });
      }
      if (url === "/api/agent/provider-verification" && !init) {
        return jsonResponse({
          status: "missing",
          report_path: "data/agent-provider-verification-report.json",
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

    const firstRender = render(<App />);
    await screen.findByText("No imported voices yet.");

    fireEvent.click(screen.getByRole("button", { name: "Local" }));
    fireEvent.change(screen.getByLabelText("Base URL"), { target: { value: "http://127.0.0.1:1234" } });
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "qwen2.5:14b" } });
    firstRender.unmount();

    render(<App />);

    expect(await screen.findByLabelText("Base URL")).toHaveValue("http://127.0.0.1:1234");
    expect(screen.getByLabelText("Model")).toHaveValue("qwen2.5:14b");
    expect(screen.queryByLabelText("API key")).not.toBeInTheDocument();
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
    expect(screen.getByRole("link", { name: "Download metadata for Bob voice" })).toHaveAttribute(
      "href",
      "/api/voices/voice_bob/metadata",
    );
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

let activeProcessor: { onaudioprocess: ((event: AudioProcessingEvent) => void) | null } | null = null;

function installAudioRecorderMock() {
  const originalMediaDevices = navigator.mediaDevices;
  const originalAudioContext = globalThis.AudioContext;
  const tracks = [{ stop: vi.fn() }];
  const stream = { getTracks: () => tracks } as unknown as MediaStream;
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue(stream),
    },
  });

  class FakeAudioContext {
    sampleRate = 16000;
    destination = {};

    createMediaStreamSource() {
      return {
        connect: vi.fn(),
        disconnect: vi.fn(),
      };
    }

    createScriptProcessor() {
      activeProcessor = {
        onaudioprocess: null,
      };
      return {
        get onaudioprocess() {
          return activeProcessor?.onaudioprocess ?? null;
        },
        set onaudioprocess(handler: ((event: AudioProcessingEvent) => void) | null) {
          if (activeProcessor) {
            activeProcessor.onaudioprocess = handler;
          }
        },
        connect: vi.fn(),
        disconnect: vi.fn(),
      };
    }

    close() {
      return Promise.resolve();
    }
  }

  Object.defineProperty(globalThis, "AudioContext", {
    configurable: true,
    value: FakeAudioContext,
  });

  return () => {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: originalMediaDevices,
    });
    Object.defineProperty(globalThis, "AudioContext", {
      configurable: true,
      value: originalAudioContext,
    });
    activeProcessor = null;
  };
}

function emitRecordingSamples(samples: number[]) {
  activeProcessor?.onaudioprocess?.({
    inputBuffer: {
      getChannelData: () => Float32Array.from(samples),
    },
  } as unknown as AudioProcessingEvent);
}

function emitRecordingSeconds(seconds: number) {
  emitRecordingSamples(Array.from({ length: 16000 * seconds }, (_, index) => (index % 2 === 0 ? 0.1 : -0.1)));
}

function emitSilentRecordingSeconds(seconds: number) {
  emitRecordingSamples(Array.from({ length: 16000 * seconds }, () => 0));
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
