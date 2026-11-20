"""Unit tests for evaluation batch runner, metrics reporting, and Wilson intervals."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.report import wilson_score_interval


def test_wilson_score_interval_properties():
    """Verify Wilson score confidence interval computation."""
    # Zero cases
    low, high = wilson_score_interval(0, 0)
    assert low == 0.0 and high == 0.0

    # 100% success on small sample
    low, high = wilson_score_interval(10, 10, confidence=0.95)
    assert low > 0.65
    assert high == 1.0

    # 0% success on small sample
    low, high = wilson_score_interval(0, 10, confidence=0.95)
    assert low == 0.0
    assert high < 0.35

    # 50% success on large sample (N=100)
    low, high = wilson_score_interval(50, 100, confidence=0.95)
    assert 0.39 < low < 0.42
    assert 0.58 < high < 0.61

    # Symmetry for 50%
    assert round(0.5 - low, 2) == round(high - 0.5, 2)


def test_persona_mix_structures():
    """Verify persona mix JSON files exist and exclude protected demographic traits."""
    mix_dir = Path("data/eval/persona_mixes")
    assert mix_dir.exists()

    expected_mixes = ["balanced", "rigorous_analytic", "intuitive_holistic"]
    prohibited_keywords = [
        "male",
        "female",
        "caste",
        "brahmin",
        "dalit",
        "muslim",
        "hindu",
        "christian",
        "religion",
    ]

    for name in expected_mixes:
        mix_file = mix_dir / f"{name}.json"
        assert mix_file.exists(), f"Missing mix: {mix_file}"

        import json

        with open(mix_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "personas" in data
            assert len(data["personas"]) == 7

            for p in data["personas"]:
                assert "occupation" in p
                assert "reasoning_style" in p
                assert "traits" in p

                # Strict check for demographic neutrality
                blob = json.dumps(p).lower()
                for keyword in prohibited_keywords:
                    assert keyword not in blob, f"Protected trait '{keyword}' found in persona {p}"
