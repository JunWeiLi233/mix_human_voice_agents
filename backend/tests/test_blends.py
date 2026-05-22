import pytest

from app.core.blends import BlendError, create_blend
from app.models.schemas import BlendProfileInput


def test_blend_requires_two_profiles():
    with pytest.raises(BlendError, match="at least two"):
        create_blend(
            name="Solo",
            profiles=[BlendProfileInput(voice_profile_id="voice_a", weight=1)],
            strategy="local_development_wav",
        )


def test_blend_normalizes_weights():
    blend = create_blend(
        name="Pair",
        profiles=[
            BlendProfileInput(voice_profile_id="voice_a", weight=2),
            BlendProfileInput(voice_profile_id="voice_b", weight=1),
        ],
        strategy="local_development_wav",
    )

    assert blend.profiles[0].weight == pytest.approx(0.666666, rel=1e-5)
    assert blend.profiles[1].weight == pytest.approx(0.333333, rel=1e-5)
    assert blend.synthetic_label == "synthetic mixed voice"

