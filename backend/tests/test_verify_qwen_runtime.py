from pathlib import Path

from app.cli.verify_qwen_runtime import main


def test_verify_qwen_runtime_generates_report_with_selected_profiles(tmp_path: Path, monkeypatch):
    seen: dict[str, object] = {}

    def fake_get_profiles(profile_ids):
        seen["profile_ids"] = profile_ids
        return {profile_id: {"id": profile_id} for profile_id in profile_ids}

    class FakeQwenAdapter:
        @classmethod
        def from_pretrained(cls, output_root=None):
            seen["output_root"] = output_root
            return cls()

        def synthesize(self, text, blend, voice_profiles=None):
            seen["text"] = text
            seen["blend"] = blend
            seen["voice_profiles"] = voice_profiles
            output = tmp_path / "qwen_verify.wav"
            output.write_bytes(b"RIFFfake")
            return output

    monkeypatch.setattr("app.cli.verify_qwen_runtime.get_voice_profiles_by_ids", fake_get_profiles)
    monkeypatch.setattr("app.cli.verify_qwen_runtime.QwenTtsAdapter", FakeQwenAdapter)

    report_path = tmp_path / "report.json"
    exit_code = main(
        [
            "--voice-profile-id",
            "voice_a",
            "--voice-profile-id",
            "voice_b",
            "--text",
            "This is a Qwen runtime verification.",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert seen["profile_ids"] == ["voice_a", "voice_b"]
    assert seen["text"] == "This is a Qwen runtime verification."
    assert seen["blend"].strategy == "multi_reference_prompt"
    assert seen["voice_profiles"] == {"voice_a": {"id": "voice_a"}, "voice_b": {"id": "voice_b"}}
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert '"status": "passed"' in report
    assert '"tts_backend": "qwen3_tts"' in report
    assert '"voice_a"' in report
    assert '"voice_b"' in report


def test_verify_qwen_runtime_requires_two_profiles(tmp_path: Path):
    exit_code = main(
        [
            "--voice-profile-id",
            "voice_a",
            "--report",
            str(tmp_path / "report.json"),
        ]
    )

    assert exit_code == 2
