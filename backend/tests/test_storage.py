from pathlib import Path

from app.core.storage import list_generation_results
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
