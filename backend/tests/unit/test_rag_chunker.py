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


def test_verify_act_in_sources() -> None:
    from app.rag.chunker import verify_act_in_sources

    assert verify_act_in_sources("BNS") is True
    assert verify_act_in_sources("BNSS") is True
    assert verify_act_in_sources("BSA") is True
    assert verify_act_in_sources("CONSTITUTION") is True
    assert verify_act_in_sources("NONEXISTENT_ACT_XYZ") is False


def test_strip_gazette_noise() -> None:
    from app.rag.chunker import strip_gazette_noise

    noisy = (
        "THE GAZETTE OF INDIA : EXTRAORDINARY\n"
        "PART II — SECTION 1\n"
        "PUBLISHED BY AUTHORITY\n"
        "Section 103. Murder punishment.\n"
        "MINISTRY OF LAW AND JUSTICE\n"
    )
    cleaned = strip_gazette_noise(noisy)
    assert "EXTRAORDINARY" not in cleaned
    assert "AUTHORITY" not in cleaned
    assert "Section 103. Murder punishment." in cleaned


def test_split_long_section_at_subsections() -> None:
    from app.rag.chunker import split_long_section

    long_body = (
        "(1) First subsection with substantive criminal law text detailing the offence.\n\n"
        "(2) Second subsection with additional aggravating factors and exceptions.\n\n"
        "(3) Third subsection with sentencing parameters and minimum penalties."
    )
    section = RawSection(
        act="BNS",
        section_no="103",
        title="Punishment for murder",
        body=long_body,
    )

    # Force splitting by passing a low max_tokens
    chunks = split_long_section(
        section,
        max_tokens=20,
        token_counter=lambda text: len(text.split()),
    )

    assert len(chunks) > 1
    for i, piece in enumerate(chunks):
        assert piece.act == "BNS"
        assert piece.parent_section == "103"
        assert f"Part {i + 1}/" in piece.section_no
        assert "Punishment for murder" in piece.title

    # Too short body
    too_short = RawSection(act="BSA", section_no="3", title="Evidence", body="Short")
    assert validate_section(too_short) is False

    # Missing act
    missing_act = RawSection(act="", section_no="3", title="Evidence", body="A" * 20)
    assert validate_section(missing_act) is False


def test_ipc_bns_map() -> None:
    from app.rag.ipc_bns_map import get_bns_equivalent, get_ipc_equivalent

    assert get_ipc_equivalent("103") == "302"
    assert get_bns_equivalent("302") == "103"
    assert get_ipc_equivalent("318") == "415, 417, 420"
    assert get_bns_equivalent("420") == "318"
    assert get_ipc_equivalent("9999") is None


def test_parse_act_markdown_bns() -> None:
    from app.rag.chunker import parse_act_markdown

    sample_bns_md = (
        "**1.** ( _1_ ) ThisAct maybe called the Bharatiya Nyaya Sanhita, 2023.\n\n"
        "Definitions.\n\n"
        "**2.** In this Sanhita, unless the context otherwise requires,––\n\n"
        "Punishment for murder.\n\n"
        "**103.** (1) Whoever commits murder shall be punished with death or imprisonment for life."
    )
    sections = parse_act_markdown(sample_bns_md, act_name="BNS")
    assert len(sections) == 3
    assert sections[0].section_no == "1"
    assert sections[1].section_no == "2"
    assert sections[2].section_no == "103"
    assert sections[2].ipc_equivalent == "302"
    assert sections[2].audience == ["judge", "lawyer"]


def test_parse_act_markdown_constitution() -> None:
    from app.rag.chunker import parse_act_markdown

    # Synthetic text simulating constitution after table of contents (> 40000 characters padding)
    padding = "TABLE OF CONTENTS\n" * 2500
    sample_const = (
        padding
        + "**20. Protection in respect of conviction for offences.** "
        + "—(1) No person shall be convicted...\n\n"
        + "**21. Protection of life and personal liberty.** "
        + "—No person shall be deprived of his life...\n\n"
        + "**50. Separation of judiciary from executive.** "
        + "The State shall take steps to separate..."
    )
    sections = parse_act_markdown(sample_const, act_name="CONSTITUTION")
    assert len(sections) == 3

    sec_map = {s.section_no: s for s in sections}
    assert "juror" in sec_map["20"].audience
    assert "juror" in sec_map["21"].audience
    assert "juror" not in sec_map["50"].audience
    assert sec_map["50"].audience == ["judge", "lawyer"]
