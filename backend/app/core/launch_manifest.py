from __future__ import annotations

from typing import Any


LAUNCH_BLEND_STRATEGY = "multi_reference_prompt"


def launch_manifest_template() -> dict[str, Any]:
    return {
        "launch_checklist": [
            "Replace every audio path with a real clean WAV file that is 5-30 seconds long.",
            "Use at least two distinct speakers with self or written permission for private_agent_voice synthesis.",
            "Keep each reference_text matched to the spoken words in that speaker's WAV.",
            (
                "Choose an agent_provider for ChatGPT/OpenAI, Claude, Grok/xAI, Gemini, "
                "any OpenAI-compatible API, or local Ollama."
            ),
            "Run this manifest with --dry-run before importing voices or calling providers.",
        ],
        "voices": [
            {
                "speaker_display_name": "Alice",
                "confirmed_by": "Junwei",
                "notes": "Self or written permission captured for private local mixed voice testing.",
                "reference_text": "Alice reads a clean five to thirty second reference for Qwen cloning.",
                "audio": "C:\\path\\to\\alice.wav",
                "weight": 1,
            },
            {
                "speaker_display_name": "Bob",
                "confirmed_by": "Junwei",
                "notes": "Self or written permission captured for private local mixed voice testing.",
                "reference_text": "Bob reads a clean five to thirty second reference for Qwen cloning.",
                "audio": "C:\\path\\to\\bob.wav",
                "weight": 1,
            },
        ],
        "blend": {
            "name": "Launch mixed voice",
            "strategy": LAUNCH_BLEND_STRATEGY,
        },
        "agent_provider": {
            "provider": "openai_compatible",
            "model": "local-qwen-agent",
            "base_url": "http://127.0.0.1:1234/v1",
            "api_key": "",
            "system_prompt": "You are a disclosed synthetic mixed-voice assistant.",
            "prompt": "Reply with one short disclosed synthetic assistant sentence.",
        },
        "qwen": {
            "text": "This is a disclosed synthetic mixed voice runtime verification.",
            "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "device_map": "auto",
            "dtype": "auto",
        },
        "generation": {
            "prompt": "Greet the user as a disclosed synthetic assistant.",
        },
    }
