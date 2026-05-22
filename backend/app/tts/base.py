from pathlib import Path
from typing import Protocol

from app.models.schemas import VoiceBlend, VoiceProfile


class TtsAdapter(Protocol):
    name: str

    def synthesize(
        self,
        text: str,
        blend: VoiceBlend,
        voice_profiles: dict[str, VoiceProfile] | None = None,
    ) -> Path:
        raise NotImplementedError
