from pathlib import Path
import wave

from app.models.schemas import AudioQuality


SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def analyze_audio_sample(path: Path) -> AudioQuality:
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    warnings: list[str] = []
    if suffix not in SUPPORTED_EXTENSIONS:
        warnings.append(f"Unsupported extension {suffix}; convert to wav before synthesis.")

    duration_seconds: float | None = None
    if suffix == ".wav":
        try:
            with wave.open(str(path), "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration_seconds = frames / float(rate) if rate else None
        except wave.Error:
            warnings.append("WAV header could not be parsed.")

    size_bytes = path.stat().st_size
    if size_bytes == 0:
        warnings.append("Audio file is empty.")
    if duration_seconds is not None and duration_seconds < 3:
        warnings.append("Reference audio is shorter than 3 seconds.")
    if duration_seconds is not None and duration_seconds > 30:
        warnings.append("Reference audio is longer than 30 seconds.")

    return AudioQuality(
        file_name=path.name,
        size_bytes=size_bytes,
        format=suffix.removeprefix(".") or "unknown",
        duration_seconds=duration_seconds,
        warnings=warnings,
    )

