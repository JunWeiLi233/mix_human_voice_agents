from pathlib import Path
import math
import struct
import wave

from app.models.schemas import VoiceBlend


class LocalWavTtsAdapter:
    name = "local_development_wav"

    def __init__(self, output_root: Path):
        self.output_root = output_root
        self.output_root.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str, blend: VoiceBlend) -> Path:
        output_path = self.output_root / f"{blend.id}.wav"
        sample_rate = 16000
        duration_seconds = max(1.0, min(4.0, len(text) / 35.0))
        frames = int(sample_rate * duration_seconds)
        frequency = 330 + int(sum(item.weight for item in blend.profiles) * 110)

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for index in range(frames):
                value = int(12000 * math.sin(2 * math.pi * frequency * index / sample_rate))
                wav_file.writeframes(struct.pack("<h", value))

        return output_path

