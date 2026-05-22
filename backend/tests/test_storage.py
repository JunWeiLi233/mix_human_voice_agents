from pathlib import Path

import pytest

from app.core.storage import get_generation_audio_path, get_generation_metadata_path, list_generation_results
from app.models.schemas import GenerationResult


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
