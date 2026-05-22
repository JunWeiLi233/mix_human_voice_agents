from pathlib import Path
import wave

from app.models.schemas import AudioQuality


MIN_REFERENCE_SECONDS = 5
MAX_REFERENCE_SECONDS = 30
CLIPPING_WARNING = "Reference audio appears clipped; record a cleaner sample."


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
    peak_amplitude = 0
    try:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            duration_seconds = frames / float(rate) if rate else None
            pcm = wav_file.readframes(frames)
            peak_amplitude = _peak_pcm_amplitude(pcm, sample_width)
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
    if peak_amplitude <= 1:
        raise AudioQualityError("Reference audio appears to contain only silence.")
    if peak_amplitude >= _max_pcm_amplitude(sample_width):
        warnings.append(CLIPPING_WARNING)

    return AudioQuality(
        file_name=path.name,
        size_bytes=size_bytes,
        format=suffix.removeprefix(".") or "unknown",
        duration_seconds=duration_seconds,
        warnings=warnings,
    )


def _peak_pcm_amplitude(pcm: bytes, sample_width: int) -> int:
    if not pcm or sample_width <= 0:
        return 0

    peak = 0
    for index in range(0, len(pcm) - sample_width + 1, sample_width):
        sample = int.from_bytes(pcm[index : index + sample_width], byteorder="little", signed=True)
        peak = max(peak, abs(sample))
    return peak


def _max_pcm_amplitude(sample_width: int) -> int:
    if sample_width <= 0:
        return 0
    return (1 << (sample_width * 8 - 1)) - 1
