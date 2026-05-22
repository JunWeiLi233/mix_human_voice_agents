from pathlib import Path
import wave

from app.models.schemas import AudioQuality


MIN_REFERENCE_SECONDS = 5
MAX_REFERENCE_SECONDS = 30


class AudioQualityError(ValueError):
    pass


def analyze_audio_sample(path: Path) -> AudioQuality:
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    warnings: list[str] = []
    if suffix != ".wav":
        raise AudioQualityError("Reference audio must be a WAV file.")

    duration_seconds: float | None = None
    try:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration_seconds = frames / float(rate) if rate else None
    except wave.Error as exc:
        raise AudioQualityError("WAV header could not be parsed.") from exc

    size_bytes = path.stat().st_size
    if size_bytes == 0:
        raise AudioQualityError("Audio file is empty.")
    if duration_seconds is None:
        raise AudioQualityError("WAV sample rate could not be read.")
    if duration_seconds < MIN_REFERENCE_SECONDS:
        raise AudioQualityError(f"Reference audio must be at least {MIN_REFERENCE_SECONDS} seconds.")
    if duration_seconds > MAX_REFERENCE_SECONDS:
        raise AudioQualityError(f"Reference audio must be {MAX_REFERENCE_SECONDS} seconds or shorter.")

    return AudioQuality(
        file_name=path.name,
        size_bytes=size_bytes,
        format=suffix.removeprefix(".") or "unknown",
        duration_seconds=duration_seconds,
        warnings=warnings,
    )
