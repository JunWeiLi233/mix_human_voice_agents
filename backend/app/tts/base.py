from pathlib import Path
import secrets
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


def unique_tts_output_path(output_root: Path, stem: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    while True:
        path = output_root / f"{stem}_{secrets.token_hex(6)}.wav"
        if not path.exists():
            return path
