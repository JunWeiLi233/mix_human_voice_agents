from pathlib import Path
from typing import Any

import soundfile as sf

from app.models.schemas import VoiceBlend, VoiceProfile


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
        model_id: str = "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        device_map: str = "auto",
        dtype: Any | None = None,
        output_root: Path | None = None,
    ) -> "QwenTtsAdapter":
        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:
            raise QwenTtsNotConfigured(
                "qwen-tts is not installed. Install backend with the qwen extra: "
                "python -m pip install -e \".[qwen]\""
            ) from exc

        kwargs: dict[str, Any] = {"device_map": device_map}
        if dtype is not None:
            kwargs["dtype"] = dtype
        model = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
        return cls(model=model, output_root=output_root)

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

        prompts = []
        for blend_profile in blend.profiles:
            profile = voice_profiles[blend_profile.voice_profile_id]
            prompts.append(
                self.model.create_voice_clone_prompt(
                    ref_audio=profile.cleaned_audio_path,
                    ref_text=profile.display_name,
                    x_vector_only_mode=self.x_vector_only_mode,
                )
            )

        wavs, sample_rate = self.model.generate_voice_clone(
            text=text,
            language=self.language,
            voice_clone_prompt=prompts,
        )
        output_path = self.output_root / f"{blend.id}_qwen.wav"
        sf.write(output_path, wavs[0], sample_rate)
        return output_path
