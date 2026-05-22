from pathlib import Path
from typing import Protocol

from app.models.schemas import VoiceBlend


class TtsAdapter(Protocol):
    name: str

    def synthesize(self, text: str, blend: VoiceBlend) -> Path:
        raise NotImplementedError

