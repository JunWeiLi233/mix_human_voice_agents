from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.core.agent import AgentProviderError, generate_agent_reply_record
from app.core.generation import generate_agent_clip
from app.core.launch import get_agent_provider_verification_report, get_qwen_verification_report
from app.core.qwen_runtime import resolved_qwen_runtime_config
from app.core.safety import SafetyError
from app.core.storage import GENERATION_ROOT, get_voice_profiles_by_ids, list_blends
from app.models.schemas import AgentConfig, AgentProviderKind, AgentTrace, GenerationResult, VoiceBlend
from app.tts.qwen import QwenTtsAdapter, QwenTtsNotConfigured


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Qwen mixed voice clip from a saved blend.")
    parser.add_argument("--blend-id", required=True, help="Saved blend id to generate from.")
    parser.add_argument("--prompt", required=True, help="Prompt to send to the configured agent provider.")
    parser.add_argument("--provider", required=True, choices=list(AgentProviderKind.__args__))
    parser.add_argument("--model", required=True, help="Agent provider model name.")
    parser.add_argument("--base-url", required=True, help="Agent provider base URL.")
    parser.add_argument("--api-key", default="", help="Agent provider API key.")
    parser.add_argument(
        "--system-prompt",
        default="You are a disclosed synthetic mixed-voice assistant.",
        help="System prompt sent to the agent provider.",
    )
    parser.add_argument("--qwen-model-id", default=None, help="Qwen3-TTS model id or local model directory.")
    parser.add_argument("--qwen-device-map", default=None, help="Qwen device map, such as auto, cuda:0, or cpu.")
    parser.add_argument("--qwen-dtype", default=None, help="Qwen torch dtype, such as bfloat16 or float16.")
    parser.add_argument("--qwen-attn-implementation", default=None, help="Qwen attention implementation.")
    parser.add_argument("--metadata", help="Optional path to write the generated result or failure report.")
    args = parser.parse_args(argv)

    try:
        config = AgentConfig(
            provider=args.provider,
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            system_prompt=args.system_prompt,
        )
        blend = _get_saved_blend(args.blend_id)
        _validate_agent_provider_preflight(config)
        _validate_qwen_verification(blend)
        voice_profiles = get_voice_profiles_by_ids([profile.voice_profile_id for profile in blend.profiles])
        agent_reply = generate_agent_reply_record(prompt=args.prompt, config=config)
        agent_trace = AgentTrace(
            provider=agent_reply.provider,
            model=agent_reply.model,
            base_url=agent_reply.base_url or config.base_url.rstrip("/"),
        )
        adapter = QwenTtsAdapter.from_pretrained(
            model_id=args.qwen_model_id,
            device_map=args.qwen_device_map,
            dtype=args.qwen_dtype,
            attn_implementation=args.qwen_attn_implementation,
            output_root=Path(GENERATION_ROOT),
        )
        qwen_runtime_config = resolved_qwen_runtime_config(
            adapter,
            {
                "model_id": args.qwen_model_id,
                "device_map": args.qwen_device_map,
                "dtype": args.qwen_dtype,
                "attn_implementation": args.qwen_attn_implementation,
            },
        )
        _validate_resolved_qwen_runtime_config(qwen_runtime_config)
        result = generate_agent_clip(
            prompt=args.prompt,
            agent_reply=agent_reply.reply,
            blend=blend,
            adapter=adapter,
            voice_profiles=voice_profiles,
            tts_backend="qwen3_tts",
            agent_trace=agent_trace,
            qwen_runtime_config=qwen_runtime_config,
        )
    except (
        AgentProviderError,
        FileNotFoundError,
        QwenTtsNotConfigured,
        SafetyError,
        ValueError,
    ) as exc:
        _write_metadata(args.metadata, {"status": "failed", "error": str(exc)})
        return 1

    _write_metadata(args.metadata, result.model_dump(mode="json"))
    return 0


def _get_saved_blend(blend_id: str) -> VoiceBlend:
    for blend in list_blends():
        if blend.id == blend_id:
            return blend
    raise FileNotFoundError(f"Saved blend not found: {blend_id}")


def _validate_agent_provider_preflight(config: AgentConfig) -> None:
    report = get_agent_provider_verification_report()
    if report.status != "passed":
        raise ValueError("Agent provider preflight must pass before Qwen generation.")
    if report.provider != config.provider or report.model != config.model:
        raise ValueError("Qwen generation agent trace must match the passed agent provider preflight.")
    if report.base_url and report.base_url.rstrip("/") != config.base_url.rstrip("/"):
        raise ValueError("Qwen generation agent trace must match the passed agent provider preflight.")


def _validate_qwen_verification(blend: VoiceBlend) -> None:
    report = get_qwen_verification_report()
    if report.status != "passed":
        raise ValueError("Qwen runtime verification must pass before Qwen generation.")
    if not report.output_audio_path or not Path(report.output_audio_path).exists():
        raise ValueError("Qwen verification output audio must exist before Qwen generation.")
    requested_voice_ids = sorted(profile.voice_profile_id for profile in blend.profiles)
    if sorted(report.voice_profile_ids) != requested_voice_ids:
        raise ValueError("Qwen generation voices must match the passed Qwen runtime verification.")


def _validate_resolved_qwen_runtime_config(runtime_config: dict[str, str | None]) -> None:
    report = get_qwen_verification_report()
    verified = {
        key: value
        for key, value in {
            "model_id": report.model_id,
            "device_map": report.device_map,
            "dtype": report.dtype,
            "attn_implementation": report.attn_implementation,
        }.items()
        if value is not None
    }
    resolved = {key: value for key, value in runtime_config.items() if value is not None}
    if verified and resolved != verified:
        raise ValueError("Qwen generation runtime config must match the passed Qwen verification.")


def _write_metadata(metadata_path: str | None, payload: dict[str, object]) -> None:
    if not metadata_path:
        return
    path = Path(metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
