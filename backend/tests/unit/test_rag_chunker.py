"""Unit tests for statutory legal chunker and text normalizer."""

import datetime

from app.rag.chunker import (
    OFFICIAL_INDIAN_LAW_LICENSE,
    RawSection,
    clean_legal_text,
    parse_act_json,
    parse_act_text,
    validate_section,
)


def test_clean_legal_text_normalization() -> None:
    raw = (
        "Section\t103.  \u201cPunishment\u201d for murder\u2014\r\n\r\n\r\n"
        "Whoever commits murder..."
    )
    cleaned = clean_legal_text(raw)

    assert "\u201c" not in cleaned
    assert '"Punishment"' in cleaned
    assert "\r" not in cleaned
    assert "  " not in cleaned
    assert "—" in cleaned
    assert cleaned.startswith("Section 103.")


def test_parse_act_text_multiple_sections() -> None:
    sample_text = """
    Section 103. Punishment for murder.—(1) Whoever commits murder shall be punished.
    (2) Group murder on ground of caste or sex shall also be punished.

    Section 104. Causing death by negligence.—Whoever causes death by rash act.
    """

    sections = parse_act_text(
        sample_text,
        act_name="BNS",
        domain="statute",
        audience=["judge", "lawyer"],
        valid_from=datetime.date(2024, 7, 1),
    )

    assert len(sections) == 2

    s1 = sections[0]
    assert s1.act == "BNS"
    assert s1.section_no == "103"
    assert s1.title == "Punishment for murder"
    assert "(1) Whoever commits murder" in s1.body
    assert s1.valid_from == datetime.date(2024, 7, 1)
    assert s1.license == OFFICIAL_INDIAN_LAW_LICENSE

    s2 = sections[1]
    assert s2.act == "BNS"
    assert s2.section_no == "104"
    assert s2.title == "Causing death by negligence"
    assert "rash act" in s2.body


def test_parse_act_json_structured() -> None:
    json_data = """{
        "act": "BNS",
        "sections": [
            {
                "section_no": "318",
                "title": "Cheating",
                "body": "Whoever, by deceiving any person, dishonestly induces...",
                "ipc_equivalent": "IPC 415",
                "audience": ["judge", "lawyer", "juror"],
                "valid_from": "2024-07-01"
            }
        ]
    }"""

    sections = parse_act_json(json_data)
    assert len(sections) == 1
    sec = sections[0]
    assert sec.act == "BNS"
    assert sec.section_no == "318"
    assert sec.title == "Cheating"
    assert sec.ipc_equivalent == "IPC 415"
    assert sec.audience == ["judge", "lawyer", "juror"]
    assert sec.valid_from == datetime.date(2024, 7, 1)


def test_validate_section() -> None:
    valid = RawSection(
        act="BSA",
        section_no="3",
        title="Evidence",
        body="Evidence means and includes all statements which the Court permits...",
    )
    assert validate_section(valid) is True

    # Empty body
    invalid_body = RawSection(act="BSA", section_no="3", title="Evidence", body="   ")
    assert validate_section(invalid_body) is False

    # Too short body
    too_short = RawSection(act="BSA", section_no="3", title="Evidence", body="Short")
    assert validate_section(too_short) is False

    # Missing act
    missing_act = RawSection(act="", section_no="3", title="Evidence", body="A" * 20)
    assert validate_section(missing_act) is False
