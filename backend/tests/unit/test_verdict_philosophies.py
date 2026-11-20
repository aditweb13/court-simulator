"""Unit tests for Verdict Judge philosophies, ethical canons, and context collections."""

from app.context.verdict_judge import build_verdict_judge_prompt
from app.verdict.philosophies import (
    GLOBAL_JUDICIAL_ETHICAL_CANONS,
    PhilosophyDoctrine,
    format_ethical_canons,
    format_philosophy_prompt_guidance,
    get_philosophy_doctrine,
    list_philosophies,
)


def test_list_philosophies() -> None:
    philosophies = list_philosophies()
    assert "textualist" in philosophies
    assert "precedent" in philosophies
    assert "fairness" in philosophies
    assert len(philosophies) >= 3


def test_philosophy_doctrines_structure() -> None:
    for phil in ["textualist", "precedent", "fairness"]:
        doc = get_philosophy_doctrine(phil)
        assert isinstance(doc, PhilosophyDoctrine)
        assert doc.philosophy == phil
        assert len(doc.core_maxim) > 5
        assert len(doc.canonical_authorities) >= 3
        assert len(doc.statutory_approach) > 20
        assert len(doc.evidentiary_standard) > 20
        assert len(doc.ethical_canons) >= 2
        assert len(doc.deliberation_instructions) > 20


def test_get_philosophy_doctrine_fallback() -> None:
    doc = get_philosophy_doctrine("non_existent_philosophy")
    # Should fall back to textualist
    assert doc.philosophy == "textualist"
    assert "Textualist" in doc.name


def test_format_philosophy_prompt_guidance() -> None:
    textualist_guidance = format_philosophy_prompt_guidance("textualist")
    assert "TEXTUALIST" in textualist_guidance
    assert "Bharatiya Nyaya Sanhita, 2023" in textualist_guidance
    assert "Judicis est jus dicere" in textualist_guidance

    precedent_guidance = format_philosophy_prompt_guidance("precedent")
    assert "PRECEDENT" in precedent_guidance
    assert "Panchsheel" in precedent_guidance
    assert "Article 141" in precedent_guidance

    fairness_guidance = format_philosophy_prompt_guidance("fairness")
    assert "FAIRNESS" in fairness_guidance
    assert "Article 21" in fairness_guidance
    assert "Maneka Gandhi" in fairness_guidance


def test_format_ethical_canons() -> None:
    canons_text = format_ethical_canons()
    for canon in GLOBAL_JUDICIAL_ETHICAL_CANONS:
        assert canon in canons_text
    assert "Presumption of Innocence" in canons_text
    assert "Impartiality" in canons_text


def test_build_verdict_judge_prompt_integration() -> None:
    ctx = {
        "case_title": "State v. Ramesh",
        "charge": "BNS 103(1) Murder",
        "jurisdiction": "Sessions Court, New Delhi",
        "judge": {"philosophy": "fairness", "orientation": "Constitutional Due Process"},
        "evidence": [{"exhibit_no": "P-1", "type": "Weapon", "description": "Recovered iron rod"}],
        "record": [{"seq": 1, "speaker": "prosecutor", "text": "We present the charges."}],
        "statutes": ["BNS Section 103(1): Whoever commits murder shall be punished with death..."],
    }
    messages = build_verdict_judge_prompt(ctx)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "JUDICIAL PHILOSOPHY: CONSTITUTIONAL FAIRNESS" in messages[0]["content"]
    assert "Article 21" in messages[0]["content"]
    assert "State v. Ramesh" in messages[1]["content"]
    assert "BNS 103(1) Murder" in messages[1]["content"]
