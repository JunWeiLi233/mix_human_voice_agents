from pathlib import Path

import pytest

from app.core.storage import (
    get_generation_audio_path,
    get_generation_metadata_path,
    list_generation_results,
    list_voice_profiles,
)
from app.models.schemas import (
    AudioQuality,
    ConsentRecord,
    GenerationResult,
    VoiceProfile,
)


def test_list_generation_results_skips_metadata_file_that_points_elsewhere(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    generation_root = tmp_path / "data" / "generations"
    generation_root.mkdir(parents=True)
    valid_path = generation_root / "valid.json"
    stale_path = generation_root / "stale.json"

    valid = GenerationResult(
        id="generation_valid",
        audio_path=str(generation_root / "valid.wav"),
        metadata_path=str(valid_path),
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
    )
    stale = valid.model_copy(
        update={
            "id": "generation_stale",
            "metadata_path": str(generation_root / "other.json"),
        }
    )
    valid_path.write_text(valid.model_dump_json(), encoding="utf-8")
    stale_path.write_text(stale.model_dump_json(), encoding="utf-8")

    results = list_generation_results()

    assert [result.id for result in results] == ["generation_valid"]


def test_list_generation_results_skips_invalid_metadata_files(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    generation_root = tmp_path / "data" / "generations"
    generation_root.mkdir(parents=True)
    valid_path = generation_root / "valid.json"
    invalid_path = generation_root / "invalid.json"

    valid = GenerationResult(
        id="generation_valid",
        audio_path=str(generation_root / "valid.wav"),
        metadata_path=str(valid_path),
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
    )
    valid_path.write_text(valid.model_dump_json(), encoding="utf-8")
    invalid_path.write_text("{invalid-json", encoding="utf-8")

    results = list_generation_results()

    assert [result.id for result in results] == ["generation_valid"]


def test_get_generation_audio_path_rejects_metadata_file_that_points_elsewhere(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    generation_root = tmp_path / "data" / "generations"
    generation_root.mkdir(parents=True)
    metadata_path = generation_root / "stale.json"
    audio_path = generation_root / "stale.wav"
    audio_path.write_bytes(b"fake-qwen-wav")
    stale = GenerationResult(
        id="generation_stale",
        audio_path=str(audio_path),
        metadata_path=str(generation_root / "other.json"),
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
    )
    metadata_path.write_text(stale.model_dump_json(), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Generated metadata is stale"):
        get_generation_audio_path("generation_stale")


def test_get_generation_audio_path_skips_invalid_metadata_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    generation_root = tmp_path / "data" / "generations"
    generation_root.mkdir(parents=True)
    invalid_path = generation_root / "invalid.json"
    metadata_path = generation_root / "valid.json"
    audio_path = generation_root / "valid.wav"
    audio_path.write_bytes(b"fake-qwen-wav")
    valid = GenerationResult(
        id="generation_valid",
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
    )
    invalid_path.write_text("{invalid-json", encoding="utf-8")
    metadata_path.write_text(valid.model_dump_json(), encoding="utf-8")

    result = get_generation_audio_path("generation_valid")

    assert result == audio_path.resolve()


def test_get_generation_metadata_path_rejects_metadata_file_that_points_elsewhere(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    generation_root = tmp_path / "data" / "generations"
    generation_root.mkdir(parents=True)
    metadata_path = generation_root / "stale.json"
    stale = GenerationResult(
        id="generation_stale",
        audio_path=str(generation_root / "stale.wav"),
        metadata_path=str(generation_root / "other.json"),
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
    )
    metadata_path.write_text(stale.model_dump_json(), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Generated metadata is stale"):
        get_generation_metadata_path("generation_stale")


def test_get_generation_metadata_path_skips_invalid_metadata_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    generation_root = tmp_path / "data" / "generations"
    generation_root.mkdir(parents=True)
    invalid_path = generation_root / "invalid.json"
    metadata_path = generation_root / "valid.json"
    valid = GenerationResult(
        id="generation_valid",
        audio_path=str(generation_root / "valid.wav"),
        metadata_path=str(metadata_path),
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_a", "voice_b"],
        blend_strategy="multi_reference_prompt",
        tts_backend="qwen3_tts",
    )
    invalid_path.write_text("{invalid-json", encoding="utf-8")
    metadata_path.write_text(valid.model_dump_json(), encoding="utf-8")

    result = get_generation_metadata_path("generation_valid")

    assert result == metadata_path.resolve()


def test_list_voice_profiles_skips_invalid_profile_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    voice_root = tmp_path / "data" / "voices"
    valid_dir = voice_root / "voice_valid"
    invalid_dir = voice_root / "voice_invalid"
    valid_dir.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)
    valid_profile = VoiceProfile(
        id="voice_valid",
        display_name="Alice",
        reference_text="Alice reads a clean reference sentence.",
        consent=ConsentRecord(
            voice_profile_id="voice_valid",
            speaker_display_name="Alice",
            consent_type="self_or_written_permission",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            confirmed_by="local_user",
            synthetic_voice_allowed=True,
        ),
        source_audio_path=str(valid_dir / "sample.wav"),
        cleaned_audio_path=str(valid_dir / "sample.wav"),
        quality=AudioQuality(
            file_name="sample.wav",
            size_bytes=12,
            format="wav",
            duration_seconds=8,
            sample_rate_hz=16000,
            channel_count=1,
            warnings=[],
        ),
    )
    (valid_dir / "profile.json").write_text(valid_profile.model_dump_json(), encoding="utf-8")
    (invalid_dir / "profile.json").write_text("{invalid-json", encoding="utf-8")

    profiles = list_voice_profiles()

    assert [profile.id for profile in profiles] == ["voice_valid"]
