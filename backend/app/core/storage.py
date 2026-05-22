from pathlib import Path

DATA_ROOT = Path("data")
VOICE_ROOT = DATA_ROOT / "voices"
BLEND_ROOT = DATA_ROOT / "blends"
GENERATION_ROOT = DATA_ROOT / "generations"


def ensure_storage() -> None:
    for path in (VOICE_ROOT, BLEND_ROOT, GENERATION_ROOT):
        path.mkdir(parents=True, exist_ok=True)

