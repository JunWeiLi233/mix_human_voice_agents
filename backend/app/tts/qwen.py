from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from app.models.schemas import TtsRuntimeStatus, VoiceBlend, VoiceProfile


DEFAULT_QWEN_TTS_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"


class QwenTtsNotConfigured(RuntimeError):
    pass


class QwenTtsAdapter:
    name = "qwen3_tts"

    def __init__(
        self,
        model: Any | None = None,
        output_root: Path | None = None,
        language: str = "English",
        x_vector_only_mode: bool = False,
    ):
        self.model = model
        self.output_root = output_root or Path("data/generations")
        self.language = language
        self.x_vector_only_mode = x_vector_only_mode
        self.output_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_pretrained(
        cls,
        model_id: str | None = None,
        device_map: str | None = None,
        dtype: Any | None = None,
        attn_implementation: str | None = None,
        output_root: Path | None = None,
    ) -> "QwenTtsAdapter":
        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:
            raise QwenTtsNotConfigured(
                "qwen-tts is not installed. Install backend with the qwen extra: "
                "python -m pip install -e \".[qwen]\""
            ) from exc

        resolved_model_id = model_id or os.getenv("QWEN_TTS_MODEL_ID") or DEFAULT_QWEN_TTS_MODEL_ID
        resolved_device_map = device_map or os.getenv("QWEN_TTS_DEVICE_MAP") or "auto"
        resolved_dtype = dtype if dtype is not None else os.getenv("QWEN_TTS_DTYPE")
        resolved_attn = attn_implementation or os.getenv("QWEN_TTS_ATTN_IMPLEMENTATION")

        kwargs: dict[str, Any] = {"device_map": resolved_device_map}
        if resolved_dtype is not None:
            kwargs["dtype"] = _resolve_torch_dtype(resolved_dtype)
        if resolved_attn:
            kwargs["attn_implementation"] = resolved_attn
        model = Qwen3TTSModel.from_pretrained(resolved_model_id, **kwargs)
        return cls(model=model, output_root=output_root)

    @staticmethod
    def runtime_status(model_id: str = DEFAULT_QWEN_TTS_MODEL_ID) -> TtsRuntimeStatus:
        if importlib.util.find_spec("qwen_tts") is None:
            return TtsRuntimeStatus(
                backend="qwen3_tts",
                available=False,
                model_id=model_id,
                message='qwen-tts is not installed. Run: python -m pip install -e ".[qwen]"',
            )
        return TtsRuntimeStatus(
            backend="qwen3_tts",
            available=True,
            model_id=model_id,
            message="qwen-tts package is importable. Verify with consented samples before launch.",
        )

    def synthesize(
        self,
        text: str,
        blend: VoiceBlend,
        voice_profiles: dict[str, VoiceProfile] | None = None,
    ) -> Path:
        if self.model is None:
            raise QwenTtsNotConfigured(
                "Qwen3-TTS model is not loaded. Use QwenTtsAdapter.from_pretrained()."
            )
        if not voice_profiles:
            raise QwenTtsNotConfigured("Qwen synthesis requires voice profile artifacts.")

        np, sf = _load_audio_dependencies()
        weighted_wavs: list[np.ndarray] = []
        sample_rate: int | None = None
        for blend_profile in blend.profiles:
            profile = voice_profiles[blend_profile.voice_profile_id]
            reference_text = profile.reference_text.strip()
            if not reference_text and not self.x_vector_only_mode:
                raise QwenTtsNotConfigured(
                    f"Qwen synthesis requires reference text for voice profile {profile.id}."
                )
            prompt = self.model.create_voice_clone_prompt(
                ref_audio=profile.cleaned_audio_path,
                ref_text=reference_text,
                x_vector_only_mode=self.x_vector_only_mode,
            )
            wavs, generated_sample_rate = self.model.generate_voice_clone(
                text=text,
                language=self.language,
                voice_clone_prompt=prompt,
            )
            if sample_rate is None:
                sample_rate = generated_sample_rate
            elif sample_rate != generated_sample_rate:
                raise QwenTtsNotConfigured("Qwen generated mismatched sample rates across source profiles.")
            weighted_wavs.append(np.asarray(wavs[0], dtype=np.float32) * blend_profile.weight)

        mixed = self._mix_weighted_wavs(weighted_wavs)
        output_path = self.output_root / f"{blend.id}_qwen.wav"
        sf.write(output_path, mixed, sample_rate or 16000)
        return output_path

    @staticmethod
    def _mix_weighted_wavs(weighted_wavs: list[np.ndarray]) -> np.ndarray:
        np, _ = _load_audio_dependencies()
        if not weighted_wavs:
            raise QwenTtsNotConfigured("No Qwen waveforms were generated for mixing.")

        max_length = max(wav.shape[0] for wav in weighted_wavs)
        padded = []
        for wav in weighted_wavs:
            if wav.shape[0] < max_length:
                wav = np.pad(wav, (0, max_length - wav.shape[0]))
            padded.append(wav)

        mixed = np.sum(np.vstack(padded), axis=0)
        peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
        if peak > 1.0:
            mixed = mixed / peak
        return mixed.astype(np.float32)

    @staticmethod
    def read_output(path: Path) -> tuple[np.ndarray, int]:
        np, sf = _load_audio_dependencies()
        data, sample_rate = sf.read(path, dtype="float32")
        return np.asarray(data, dtype=np.float32), sample_rate


def _load_audio_dependencies() -> tuple[Any, Any]:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise QwenTtsNotConfigured(
            "Qwen audio mixing dependencies are not installed. Install backend with: "
            'python -m pip install -e ".[qwen]"'
        ) from exc
    return np, sf


def _resolve_torch_dtype(dtype: Any) -> Any:
    if not isinstance(dtype, str):
        return dtype
    normalized = dtype.strip()
    if not normalized:
        return None
    try:
        import torch
    except ImportError as exc:
        raise QwenTtsNotConfigured(
            f"Qwen dtype '{normalized}' requires torch. Install backend with: "
            'python -m pip install -e ".[qwen]"'
        ) from exc
    try:
        return getattr(torch, normalized)
    except AttributeError as exc:
        raise QwenTtsNotConfigured(f"Unsupported torch dtype for Qwen: {normalized}") from exc
