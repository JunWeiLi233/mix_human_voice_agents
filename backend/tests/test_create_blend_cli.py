from pathlib import Path

from app.cli.create_blend import main
from app.models.schemas import AudioQuality, ConsentRecord, VoiceProfile


def test_create_blend_cli_saves_multi_reference_blend(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_profile("voice_a", "Alice")
    save_profile("voice_b", "Bob")
    metadata_path = tmp_path / "blend-report.json"

    exit_code = main(
        [
            "--name",
            "Launch blend",
            "--profile",
            "voice_a=2",
            "--profile",
            "voice_b=1",
            "--strategy",
            "multi_reference_prompt",
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 0
    report = metadata_path.read_text(encoding="utf-8")
    assert '"name": "Launch blend"' in report
    assert '"strategy": "multi_reference_prompt"' in report
    assert '"voice_profile_id": "voice_a"' in report
    saved_blends = list((tmp_path / "data" / "blends").glob("*.json"))
    assert len(saved_blends) == 1
    saved_payload = saved_blends[0].read_text(encoding="utf-8")
    assert '"weight": 0.6666666666666666' in saved_payload
    assert '"weight": 0.3333333333333333' in saved_payload


def test_create_blend_cli_rejects_missing_imported_voice(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_profile("voice_a", "Alice")
    metadata_path = tmp_path / "blend-failed.json"

    exit_code = main(
        [
            "--name",
            "Missing profile blend",
            "--profile",
            "voice_a=1",
            "--profile",
            "voice_b=1",
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 1
    assert '"status": "failed"' in metadata_path.read_text(encoding="utf-8")
    assert "Missing voice profiles: voice_b" in metadata_path.read_text(encoding="utf-8")
    assert list((tmp_path / "data" / "blends").glob("*.json")) == []


def save_profile(profile_id: str, display_name: str) -> None:
    voice_dir = Path("data") / "voices" / profile_id
    voice_dir.mkdir(parents=True)
    audio_path = voice_dir / "source.wav"
    audio_path.write_bytes(b"fake-wav")
    profile = VoiceProfile(
        id=profile_id,
        display_name=display_name,
        reference_text=f"{display_name} reads a launch reference.",
        consent=ConsentRecord(
            voice_profile_id=profile_id,
            speaker_display_name=display_name,
            consent_type="self_or_written_permission",
            allowed_uses=["private_agent_voice", "local_audio_export"],
            confirmed_by="Junwei",
            notes="Written permission captured.",
            synthetic_voice_allowed=True,
        ),
        source_audio_path=str(audio_path),
        cleaned_audio_path=str(audio_path),
        quality=AudioQuality(
            file_name="source.wav",
            size_bytes=8,
            format="wav",
            duration_seconds=5.0,
            sample_rate_hz=16000,
            channel_count=1,
            warnings=[],
        ),
    )
    (voice_dir / "profile.json").write_text(profile.model_dump_json(), encoding="utf-8")
