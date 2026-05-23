from pathlib import Path
import json
import math
import struct
import wave

from app.cli.import_voice import main


def test_import_voice_cli_saves_consented_profile_with_transcript(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sample_path = tmp_path / "Alice Reference.wav"
    write_reference_wav(sample_path)
    metadata_path = tmp_path / "voice.json"

    exit_code = main(
        [
            "--speaker-display-name",
            "Alice",
            "--confirmed-by",
            "Junwei",
            "--notes",
            "Written permission captured for private local mixed voice testing.",
            "--reference-text",
            "Alice reads a clean reference sentence for Qwen cloning.",
            "--audio",
            str(sample_path),
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 0
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["display_name"] == "Alice"
    assert metadata["reference_text"] == "Alice reads a clean reference sentence for Qwen cloning."
    assert metadata["consent"]["confirmed_by"] == "Junwei"
    assert metadata["consent"]["allowed_uses"] == ["private_agent_voice", "local_audio_export"]
    assert metadata["quality"]["duration_seconds"] == 5
    assert Path(metadata["source_audio_path"]).exists()
    assert Path(metadata["cleaned_audio_path"]).exists()
    assert (tmp_path / "data" / "voices" / metadata["id"] / "profile.json").exists()


def test_import_voice_cli_rejects_blank_reference_text(tmp_path: Path):
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    metadata_path = tmp_path / "voice.json"

    exit_code = main(
        [
            "--speaker-display-name",
            "Alice",
            "--confirmed-by",
            "Junwei",
            "--reference-text",
            "   ",
            "--audio",
            str(sample_path),
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 2
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["error"] == "A reference transcript is required for voice import."


def test_import_voice_cli_rejects_public_figure_label(tmp_path: Path):
    sample_path = tmp_path / "sample.wav"
    write_reference_wav(sample_path)
    metadata_path = tmp_path / "voice.json"

    exit_code = main(
        [
            "--speaker-display-name",
            "Famous celebrity voice",
            "--confirmed-by",
            "Junwei",
            "--reference-text",
            "A speaker reads a clean reference sentence for Qwen cloning.",
            "--audio",
            str(sample_path),
            "--metadata",
            str(metadata_path),
        ]
    )

    assert exit_code == 1
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert "public figure" in payload["error"]


def write_reference_wav(path: Path, duration_seconds: int = 5, sample_rate: int = 16000) -> None:
    frames = b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * index / sample_rate)))
        for index in range(sample_rate * duration_seconds)
    )
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
