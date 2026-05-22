from pathlib import Path

from app.models.schemas import VoiceBlend


class QwenTtsNotConfigured(RuntimeError):
    pass


class QwenTtsAdapter:
    name = "qwen3_tts"

    def __init__(self, model_root: Path | None = None):
        self.model_root = model_root

    def synthesize(self, text: str, blend: VoiceBlend) -> Path:
        raise QwenTtsNotConfigured(
            "Qwen3-TTS adapter is defined but not configured. "
            "Install Qwen3-TTS and set model_root before selecting this adapter."
        )

