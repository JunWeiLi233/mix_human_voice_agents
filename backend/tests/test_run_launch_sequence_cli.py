import json
import math
from pathlib import Path
import struct
import wave

from app.cli.run_launch_sequence import main


def test_run_launch_sequence_dry_run_validates_manifest_without_side_effects(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(argv):
        raise AssertionError("dry run should not call launch subcommands")

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.create_blend_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_agent_provider_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_qwen_runtime_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.generate_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.launch_readiness_main", fail_if_called)

    exit_code = main(
        ["--manifest", str(manifest_path), "--dry-run", "--report", "sequence-report.json"]
    )

    assert exit_code == 0
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "passed",
        "mode": "dry_run",
        "voice_count": 2,
        "speaker_display_names": ["Alice", "Bob"],
    }


def test_run_launch_sequence_dry_run_rejects_unsupported_agent_provider(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "unsupported_ai",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(argv):
        raise AssertionError("unsupported providers should validate before launch subcommands")

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_agent_provider_main", fail_if_called)

    exit_code = main(
        ["--manifest", str(manifest_path), "--dry-run", "--report", "sequence-report.json"]
    )

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": (
            "agent_provider.provider must be one of: "
            "openai, anthropic, google, xai, openai_compatible, ollama."
        ),
    }


def test_run_launch_sequence_dry_run_rejects_nonpositive_voice_weight(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                        "weight": 0,
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                        "weight": 1,
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(argv):
        raise AssertionError("invalid weights should validate before launch subcommands")

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.create_blend_main", fail_if_called)

    exit_code = main(
        ["--manifest", str(manifest_path), "--dry-run", "--report", "sequence-report.json"]
    )

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "voices[1].weight must be a positive number.",
    }


def test_run_launch_sequence_dry_run_rejects_non_qwen_blend_strategy(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "blend": {"name": "Launch blend", "strategy": "local_development_wav"},
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(argv):
        raise AssertionError("invalid blend strategy should validate before launch subcommands")

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.create_blend_main", fail_if_called)

    exit_code = main(
        ["--manifest", str(manifest_path), "--dry-run", "--report", "sequence-report.json"]
    )

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "blend.strategy must be multi_reference_prompt for Qwen launch generation.",
    }


def test_run_launch_sequence_dry_run_rejects_blank_blend_name(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "blend": {"name": "   "},
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(argv):
        raise AssertionError("blank blend names should validate before launch subcommands")

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.create_blend_main", fail_if_called)

    exit_code = main(
        ["--manifest", str(manifest_path), "--dry-run", "--report", "sequence-report.json"]
    )

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "blend.name must not be blank when provided.",
    }


def test_run_launch_sequence_dry_run_rejects_blank_qwen_verification_text(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "qwen": {"text": "   "},
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(argv):
        raise AssertionError("blank Qwen text should validate before launch subcommands")

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_qwen_runtime_main", fail_if_called)

    exit_code = main(
        ["--manifest", str(manifest_path), "--dry-run", "--report", "sequence-report.json"]
    )

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "qwen.text must not be blank when provided.",
    }


def test_run_launch_sequence_dry_run_rejects_blank_qwen_runtime_option(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "qwen": {"model_id": "   "},
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(argv):
        raise AssertionError("blank Qwen runtime options should validate before launch subcommands")

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_qwen_runtime_main", fail_if_called)

    exit_code = main(
        ["--manifest", str(manifest_path), "--dry-run", "--report", "sequence-report.json"]
    )

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "qwen.model_id must not be blank when provided.",
    }


def test_run_launch_sequence_dry_run_rejects_blank_agent_provider_prompt(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                    "prompt": "   ",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(argv):
        raise AssertionError("blank provider prompt should validate before launch subcommands")

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fail_if_called)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_agent_provider_main", fail_if_called)

    exit_code = main(
        ["--manifest", str(manifest_path), "--dry-run", "--report", "sequence-report.json"]
    )

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "agent_provider.prompt must not be blank when provided.",
    }


def test_run_launch_sequence_invokes_launch_steps_from_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "notes": "Written permission captured.",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                        "weight": 2,
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "notes": "Written permission captured.",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                        "weight": 1,
                    },
                ],
                "blend": {"name": "Launch blend"},
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                    "api_key": "",
                },
                "qwen": {
                    "text": "This is a Qwen launch verification.",
                    "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                    "device_map": "auto",
                },
                "generation": {
                    "prompt": "Greet the user as a disclosed synthetic assistant.",
                },
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_import_voice(argv):
        calls.append(("import_voice", argv))
        metadata_path = Path(argv[argv.index("--metadata") + 1])
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        speaker = argv[argv.index("--speaker-display-name") + 1]
        profile_id = "voice_a" if speaker == "Alice" else "voice_b"
        metadata_path.write_text(json.dumps({"id": profile_id}), encoding="utf-8")
        return 0

    def fake_create_blend(argv):
        calls.append(("create_blend", argv))
        metadata_path = Path(argv[argv.index("--metadata") + 1])
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps({"id": "blend_launch"}), encoding="utf-8")
        return 0

    def fake_success(name):
        def fake(argv):
            calls.append((name, argv))
            return 0

        return fake

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fake_import_voice)
    monkeypatch.setattr("app.cli.run_launch_sequence.create_blend_main", fake_create_blend)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_agent_provider_main", fake_success("verify_agent"))
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_qwen_runtime_main", fake_success("verify_qwen"))
    monkeypatch.setattr("app.cli.run_launch_sequence.generate_voice_main", fake_success("generate_voice"))
    monkeypatch.setattr("app.cli.run_launch_sequence.launch_readiness_main", fake_success("launch_readiness"))

    exit_code = main(["--manifest", str(manifest_path), "--tasks", "TASKS.md"])

    assert exit_code == 0
    assert [name for name, _ in calls] == [
        "import_voice",
        "import_voice",
        "create_blend",
        "verify_agent",
        "verify_qwen",
        "generate_voice",
        "launch_readiness",
    ]
    create_blend_args = calls[2][1]
    assert "--profile" in create_blend_args
    assert "voice_a=2" in create_blend_args
    assert "voice_b=1" in create_blend_args
    generate_args = calls[5][1]
    assert generate_args[generate_args.index("--blend-id") + 1] == "blend_launch"
    assert generate_args[generate_args.index("--provider") + 1] == "openai_compatible"
    assert generate_args[generate_args.index("--model") + 1] == "local-qwen-agent"
    assert generate_args[generate_args.index("--base-url") + 1] == "http://127.0.0.1:1234/v1"


def test_run_launch_sequence_rejects_manifest_with_fewer_than_two_voices(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(tmp_path / "alice.wav"),
                    }
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Hello."},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.cli.run_launch_sequence.import_voice_main",
        lambda argv: (_ for _ in ()).throw(AssertionError("voices should validate before imports")),
    )

    exit_code = main(["--manifest", str(manifest_path), "--report", "sequence-report.json"])

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "Launch sequence manifest requires at least two voices.",
    }


def test_run_launch_sequence_rejects_missing_audio_file_before_import(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    bob_audio = tmp_path / "bob.wav"
    bob_audio.write_bytes(b"fake-audio-b")
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(tmp_path / "missing-alice.wav"),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(bob_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.cli.run_launch_sequence.import_voice_main",
        lambda argv: (_ for _ in ()).throw(AssertionError("missing audio should validate before imports")),
    )

    exit_code = main(["--manifest", str(manifest_path), "--report", "sequence-report.json"])

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": f"voices[1].audio does not exist: {tmp_path / 'missing-alice.wav'}",
    }


def test_run_launch_sequence_rejects_duplicate_speaker_names_before_import(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice-a.wav"
    voice_b_audio = tmp_path / "alice-b.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads the first launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": " alice ",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads the second launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.cli.run_launch_sequence.import_voice_main",
        lambda argv: (_ for _ in ()).throw(AssertionError("duplicate speakers should validate before imports")),
    )

    exit_code = main(["--manifest", str(manifest_path), "--report", "sequence-report.json"])

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "Launch sequence manifest requires at least two distinct speaker display names.",
    }


def test_run_launch_sequence_rejects_invalid_wav_before_import(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    invalid_audio = tmp_path / "alice.wav"
    bob_audio = tmp_path / "bob.wav"
    invalid_audio.write_bytes(b"not-a-wav")
    bob_audio.write_bytes(b"also-not-used")
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(invalid_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(bob_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.cli.run_launch_sequence.import_voice_main",
        lambda argv: (_ for _ in ()).throw(AssertionError("invalid wav should validate before imports")),
    )

    exit_code = main(["--manifest", str(manifest_path), "--report", "sequence-report.json"])

    assert exit_code == 2
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": f"voices[1].audio must be a parseable WAV file: {invalid_audio}",
    }


def test_run_launch_sequence_fails_when_final_readiness_is_blocked(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "launch-manifest.json"
    voice_a_audio = tmp_path / "alice.wav"
    voice_b_audio = tmp_path / "bob.wav"
    write_reference_wav(voice_a_audio)
    write_reference_wav(voice_b_audio)
    manifest_path.write_text(
        json.dumps(
            {
                "voices": [
                    {
                        "speaker_display_name": "Alice",
                        "confirmed_by": "Junwei",
                        "reference_text": "Alice reads a launch reference.",
                        "audio": str(voice_a_audio),
                    },
                    {
                        "speaker_display_name": "Bob",
                        "confirmed_by": "Junwei",
                        "reference_text": "Bob reads a launch reference.",
                        "audio": str(voice_b_audio),
                    },
                ],
                "agent_provider": {
                    "provider": "openai_compatible",
                    "model": "local-qwen-agent",
                    "base_url": "http://127.0.0.1:1234/v1",
                },
                "generation": {"prompt": "Greet the user as a disclosed synthetic assistant."},
            }
        ),
        encoding="utf-8",
    )

    def fake_import_voice(argv):
        metadata_path = Path(argv[argv.index("--metadata") + 1])
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        speaker = argv[argv.index("--speaker-display-name") + 1]
        profile_id = "voice_a" if speaker == "Alice" else "voice_b"
        metadata_path.write_text(json.dumps({"id": profile_id}), encoding="utf-8")
        return 0

    def fake_create_blend(argv):
        metadata_path = Path(argv[argv.index("--metadata") + 1])
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps({"id": "blend_launch"}), encoding="utf-8")
        return 0

    monkeypatch.setattr("app.cli.run_launch_sequence.import_voice_main", fake_import_voice)
    monkeypatch.setattr("app.cli.run_launch_sequence.create_blend_main", fake_create_blend)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_agent_provider_main", lambda argv: 0)
    monkeypatch.setattr("app.cli.run_launch_sequence.verify_qwen_runtime_main", lambda argv: 0)
    monkeypatch.setattr("app.cli.run_launch_sequence.generate_voice_main", lambda argv: 0)
    monkeypatch.setattr("app.cli.run_launch_sequence.launch_readiness_main", lambda argv: 1)

    exit_code = main(["--manifest", str(manifest_path), "--report", "sequence-report.json"])

    assert exit_code == 1
    report = json.loads(Path("sequence-report.json").read_text(encoding="utf-8"))
    assert report == {
        "status": "failed",
        "error": "Launch readiness remained blocked after the sequence.",
    }


def write_reference_wav(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    duration_seconds = 5
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate)))
            for index in range(sample_rate * duration_seconds)
        )
        wav_file.writeframes(frames)
    return path
