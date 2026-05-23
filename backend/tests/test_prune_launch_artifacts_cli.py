from pathlib import Path
import json

from app.cli.prune_launch_artifacts import main
from app.models.schemas import (
    AudioQuality,
    BlendProfile,
    ConsentRecord,
    GenerationResult,
    VoiceBlend,
    VoiceProfile,
)


def test_prune_launch_artifacts_dry_run_reports_stale_blends_without_deleting(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    voice = voice_profile("voice_alice", "Alice")
    stale = blend("blend_stale", ["voice_missing", "voice_alice"])
    launch_ready = blend("blend_ready", ["voice_alice", "voice_bob"])
    bob = voice_profile("voice_bob", "Bob")
    write_voice(voice)
    write_voice(bob)
    write_blend(stale)
    write_blend(launch_ready)
    report_path = tmp_path / "prune-report.json"

    exit_code = main(["--report", str(report_path)])

    assert exit_code == 0
    assert (tmp_path / "data" / "blends" / "blend_stale.json").exists()
    assert (tmp_path / "data" / "blends" / "blend_ready.json").exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload == {
        "mode": "dry_run",
        "stale_blend_ids": ["blend_stale"],
        "stale_blends": [
            {
                "id": "blend_stale",
                "name": "blend_stale",
                "voice_profile_ids": ["voice_missing", "voice_alice"],
                "stale_reasons": [
                    "Blend must reference at least two distinct speaker display names.",
                    "Blend references voices that are missing or not launch-usable: voice_missing.",
                ],
            }
        ],
        "deleted_blend_ids": [],
        "kept_blend_ids": ["blend_ready"],
        "stale_generation_ids": [],
        "stale_generations": [],
        "deleted_generation_ids": [],
        "kept_generation_ids": [],
        "reviewed_apply_command": f"python -m app.cli.prune_launch_artifacts --apply --report {report_path}",
    }
    output = capsys.readouterr().out
    assert "Dry run: 1 stale blends would be deleted; 0 stale generations would be deleted." in output
    assert f"Review {report_path}, then run: python -m app.cli.prune_launch_artifacts --apply --report {report_path}" in output
    assert "blend_stale" in output


def test_prune_launch_artifacts_apply_deletes_only_stale_blends(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_voice(voice_profile("voice_alice", "Alice"))
    write_voice(voice_profile("voice_bob", "Bob"))
    write_blend(blend("blend_stale", ["voice_alice", "voice_missing"]))
    write_blend(blend("blend_ready", ["voice_alice", "voice_bob"]))
    report_path = tmp_path / "prune-report.json"

    exit_code = main(["--apply", "--report", str(report_path)])

    assert exit_code == 0
    assert not (tmp_path / "data" / "blends" / "blend_stale.json").exists()
    assert (tmp_path / "data" / "blends" / "blend_ready.json").exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "apply"
    assert payload["deleted_blend_ids"] == ["blend_stale"]
    assert payload["kept_blend_ids"] == ["blend_ready"]
    output = capsys.readouterr().out
    assert "Deleted 1 stale blends." in output


def test_prune_launch_artifacts_dry_run_reports_stale_generations_without_deleting(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_voice(voice_profile("voice_alice", "Alice"))
    write_voice(voice_profile("voice_bob", "Bob"))
    write_generation(local_generation("generation_local"))
    report_path = tmp_path / "prune-report.json"

    exit_code = main(["--report", str(report_path)])

    assert exit_code == 0
    assert (tmp_path / "data" / "generations" / "generation_local.json").exists()
    assert (tmp_path / "data" / "generations" / "generation_local.wav").exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "dry_run"
    assert payload["stale_generation_ids"] == ["generation_local"]
    assert payload["stale_generations"] == [
        {
            "id": "generation_local",
            "tts_backend": "local_development_wav",
            "audio_path": str(Path("data") / "generations" / "generation_local.wav"),
            "metadata_path": str(Path("data") / "generations" / "generation_local.json"),
            "stale_reasons": ["Generation was not created with Qwen3-TTS."],
        }
    ]
    assert payload["deleted_generation_ids"] == []
    assert payload["kept_generation_ids"] == []
    output = capsys.readouterr().out
    assert "Dry run:" in output
    assert "1 stale generations would be deleted" in output
    assert "generation_local" in output


def test_prune_launch_artifacts_apply_deletes_stale_generation_metadata_and_audio(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    write_voice(voice_profile("voice_alice", "Alice"))
    write_voice(voice_profile("voice_bob", "Bob"))
    write_generation(local_generation("generation_local"))
    report_path = tmp_path / "prune-report.json"

    exit_code = main(["--apply", "--report", str(report_path)])

    assert exit_code == 0
    assert not (tmp_path / "data" / "generations" / "generation_local.json").exists()
    assert not (tmp_path / "data" / "generations" / "generation_local.wav").exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "apply"
    assert payload["deleted_generation_ids"] == ["generation_local"]
    assert payload["kept_generation_ids"] == []
    output = capsys.readouterr().out
    assert "Deleted 0 stale blends." in output
    assert "Deleted 1 stale generations." in output


def write_generation(result: GenerationResult) -> None:
    generation_root = Path("data") / "generations"
    generation_root.mkdir(parents=True, exist_ok=True)
    (generation_root / f"{result.id}.json").write_text(result.model_dump_json(), encoding="utf-8")
    Path(result.audio_path).write_bytes(b"fake-wav")


def local_generation(generation_id: str) -> GenerationResult:
    audio_path = Path("data") / "generations" / f"{generation_id}.wav"
    metadata_path = Path("data") / "generations" / f"{generation_id}.json"
    return GenerationResult(
        id=generation_id,
        audio_path=str(audio_path),
        metadata_path=str(metadata_path),
        synthetic_label="synthetic mixed voice",
        source_profile_ids=["voice_alice", "voice_bob"],
        blend_strategy="multi_reference_prompt",
        tts_backend="local_development_wav",
    )


def write_voice(profile: VoiceProfile) -> None:
    voice_dir = Path("data") / "voices" / profile.id
    voice_dir.mkdir(parents=True, exist_ok=True)
    (voice_dir / "sample.wav").write_bytes(b"fake-wav")
    (voice_dir / "profile.json").write_text(profile.model_dump_json(), encoding="utf-8")


def write_blend(voice_blend: VoiceBlend) -> None:
    blend_root = Path("data") / "blends"
    blend_root.mkdir(parents=True, exist_ok=True)
    (blend_root / f"{voice_blend.id}.json").write_text(voice_blend.model_dump_json(), encoding="utf-8")


def voice_profile(profile_id: str, display_name: str) -> VoiceProfile:
    return VoiceProfile(
        id=profile_id,
        display_name=display_name,
        reference_text=f"{display_name} reads a clean reference sentence.",
        consent=ConsentRecord(
            voice_profile_id=profile_id,
            speaker_display_name=display_name,
            consent_type="self_or_written_permission",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            confirmed_by="Junwei",
            synthetic_voice_allowed=True,
        ),
        source_audio_path=str(Path("data") / "voices" / profile_id / "sample.wav"),
        cleaned_audio_path=str(Path("data") / "voices" / profile_id / "sample.wav"),
        quality=AudioQuality(
            file_name="sample.wav",
            size_bytes=160044,
            format="wav",
            duration_seconds=8.0,
            sample_rate_hz=24000,
            channel_count=1,
            warnings=[],
        ),
    )


def blend(blend_id: str, voice_ids: list[str]) -> VoiceBlend:
    return VoiceBlend(
        id=blend_id,
        name=blend_id,
        strategy="multi_reference_prompt",
        profiles=[BlendProfile(voice_profile_id=voice_id, weight=0.5) for voice_id in voice_ids],
    )
