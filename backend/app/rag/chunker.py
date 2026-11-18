"""Legal document chunker and section parser.

Extracts discrete legal sections from statutory acts, normalizes legislative
text, and attaches mandatory domain, audience, and licensing metadata.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Official legislative license notice under Indian Copyright Act 1957
OFFICIAL_INDIAN_LAW_LICENSE = (
    "Public Domain / Government Work under Section 52(1)(q) of the Indian Copyright Act, 1957"
)


@dataclass
class RawSection:
    """A single discrete legal provision with accompanying metadata."""

    act: str
    section_no: str
    title: str
    body: str
    domain: str = "statute"
    audience: List[str] = field(default_factory=lambda: ["judge", "lawyer"])
    ipc_equivalent: Optional[str] = None
    valid_from: Optional[datetime.date] = None
    valid_to: Optional[datetime.date] = None
    source: str = "The Gazette of India"
    license: str = OFFICIAL_INDIAN_LAW_LICENSE
    parent_section: Optional[str] = None
    token_count: int = 0


def verify_act_in_sources(act: str, sources_path: Optional[Path] = None) -> bool:
    """Verify that the Act is registered in SOURCES.md.

    Ingestion refuses to run for an act with no entry in SOURCES.md.
    """
    if sources_path is None:
        sources_path = Path(__file__).resolve().parents[3] / "data" / "law_corpus" / "SOURCES.md"

    if not sources_path.exists():
        logger.error("SOURCES.md not found at %s", sources_path)
        return False

    content = sources_path.read_text(encoding="utf-8")
    # Match backticked or plain act key in markdown table, e.g. `BNS` or | BNS |
    act_normalized = act.strip().upper()
    pattern = rf"[`|]\s*{re.escape(act_normalized)}\s*[`|]"
    if re.search(pattern, content, re.IGNORECASE):
        return True

    logger.error("Act '%s' has no entry in %s", act, sources_path)
    return False


def clean_legal_text(text: str) -> str:
    """Normalize legal text formatting, quotes, and inconsistent whitespace."""
    if not text:
        return ""
    # Normalize unicode quotes and dashes
    t = text.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u2014", "—").replace("\u2013", "-")
    # Replace carriage returns and excessive tabs
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple consecutive horizontal whitespaces
    t = re.sub(r"[ \t]+", " ", t)
    # Collapse more than two consecutive newlines into double newline
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def strip_gazette_noise(text: str) -> str:
    """Strip common gazette headers, footers, page numbers and publication notices."""
    # Remove Gazette of India header lines
    noise_patterns = [
        r"(?i)THE\s+GAZETTE\s+OF\s+INDIA\s*:?\s*EXTRAORDINARY",
        r"(?i)PART\s+[I|V|X]+\s*—\s*SECTION\s+\d+",
        r"(?i)PUBLISHED\s+BY\s+AUTHORITY",
        r"(?i)NEW\s+DELHI,\s+[A-Z]+,\s+[A-Z]+\s+\d+,\s+\d{4}\s*/\s*[A-Z]+\s+\d+,\s+\d{4}",
        r"(?i)MINISTRY\s+OF\s+LAW\s+AND\s+JUSTICE",
        r"(?i)\(Legislative\s+Department\)",
        r"(?i)SEC\.\s*\d+\]\s+THE\s+GAZETTE\s+OF\s+INDIA\s+EXTRAORDINARY\s+\d+",
        r"\n\s*\d+\s*\n",  # Bare page numbers
    ]
    cleaned = text
    for pat in noise_patterns:
        cleaned = re.sub(pat, "", cleaned)
    return cleaned


def extract_pdf_text(pdf_path: Union[str, Path]) -> str:
    """Extract plain text from a PDF file using PyMuPDF and strip gazette noise."""
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    pages: List[str] = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        pages.append(page.get_text())
    doc.close()

    full_text = "\n".join(pages)
    return clean_legal_text(strip_gazette_noise(full_text))


def default_estimate_tokens(text: str) -> int:
    """Deterministic token estimate for offline/testing use (~1 token per 3.5 chars)."""
    words = text.split()
    return max(len(words), int(len(text) / 3.5))


# Regex pattern to match Section or Article headers
# e.g.:
# "Section 103. Punishment for murder.—(1) Whoever..."
# "103. Punishment for murder.—..."
# "Article 21. Protection of life and personal liberty.—..."
_SECTION_HEADER_RE = re.compile(
    r"(?:^|\n+)[ \t]*(?:(?:Section|Sec\.|Article|Art\.)\s+)?"
    r"(\d+[A-Z]?)\.\s*([^\n.—]+)(?:[.—\s]+)\s*",
    re.IGNORECASE,
)

# Regex pattern for sub-section boundaries: e.g. "(1) ", "(2) "
_SUBSECTION_SPLIT_RE = re.compile(r"\n+(?=\(\d+\)\s+)")


def split_long_section(
    section: RawSection,
    max_tokens: int = 512,
    token_counter: Optional[Callable[[str], int]] = None,
) -> List[RawSection]:
    """Split a section if it exceeds max_tokens at sub-section boundaries.

    Repeats the section number and title in every piece with a parent reference.
    """
    counter = token_counter or default_estimate_tokens
    full_text = f"{section.title}. {section.body}"
    total_tokens = counter(full_text)
    section.token_count = total_tokens

    if total_tokens <= max_tokens:
        return [section]

    # Split body on sub-section boundaries "(1)", "(2)", etc.
    parts = _SUBSECTION_SPLIT_RE.split(section.body)
    if len(parts) <= 1:
        # Fallback to paragraph-level splitting
        parts = [p.strip() for p in section.body.split("\n\n") if p.strip()]

    if len(parts) <= 1:
        # Cannot split further cleanly
        return [section]

    # Group parts into chunks under max_tokens
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_tokens = counter(section.title)

    for part in parts:
        part_tokens = counter(part)
        if current_chunk and (current_tokens + part_tokens > max_tokens):
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [part]
            current_tokens = counter(section.title) + part_tokens
        else:
            current_chunk.append(part)
            current_tokens += part_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    if len(chunks) <= 1:
        return [section]

    split_sections: List[RawSection] = []
    total_pieces = len(chunks)
    for i, chunk_text in enumerate(chunks):
        piece_sec_no = f"{section.section_no} (Part {i + 1}/{total_pieces})"
        split_sections.append(
            RawSection(
                act=section.act,
                section_no=piece_sec_no,
                title=f"{section.title} [Part {i + 1}/{total_pieces}]",
                body=chunk_text,
                domain=section.domain,
                audience=list(section.audience),
                ipc_equivalent=section.ipc_equivalent,
                valid_from=section.valid_from,
                valid_to=section.valid_to,
                source=section.source,
                license=section.license,
                parent_section=section.section_no,
                token_count=counter(chunk_text),
            )
        )

    return split_sections


def parse_act_text(
    raw_text: str,
    act_name: str,
    *,
    domain: str = "statute",
    audience: Optional[List[str]] = None,
    valid_from: Optional[datetime.date] = None,
    source: str = "The Gazette of India",
    max_tokens: int = 512,
    token_counter: Optional[Callable[[str], int]] = None,
) -> List[RawSection]:
    """Parse raw plain-text legislative text into structured RawSection items."""
    cleaned = clean_legal_text(raw_text)
    if not cleaned:
        return []

    target_audience = audience or ["judge", "lawyer"]
    matches = list(_SECTION_HEADER_RE.finditer(cleaned))
    if not matches:
        return []

    sections: List[RawSection] = []
    for i, match in enumerate(matches):
        sec_no = match.group(1).strip()
        sec_title = match.group(2).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)

        body_content = cleaned[body_start:body_end].strip()
        if not body_content:
            continue

        raw_sec = RawSection(
            act=act_name,
            section_no=sec_no,
            title=sec_title,
            body=body_content,
            domain=domain,
            audience=list(target_audience),
            valid_from=valid_from,
            source=source,
            license=OFFICIAL_INDIAN_LAW_LICENSE,
        )

        split_pieces = split_long_section(
            raw_sec, max_tokens=max_tokens, token_counter=token_counter
        )
        sections.extend(split_pieces)

    return sections


def parse_act_json(
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    default_act: Optional[str] = None,
    max_tokens: int = 512,
    token_counter: Optional[Callable[[str], int]] = None,
) -> List[RawSection]:
    """Parse JSON representation of an act into a list of RawSection items."""
    raw_list: List[Dict[str, Any]]
    if isinstance(data, str):
        parsed = json.loads(data)
        if isinstance(parsed, dict) and "sections" in parsed:
            raw_list = parsed["sections"]
            default_act = default_act or parsed.get("act")
        elif isinstance(parsed, list):
            raw_list = parsed
        else:
            raw_list = [parsed]
    elif isinstance(data, dict):
        if "sections" in data:
            raw_list = data["sections"]
            default_act = default_act or data.get("act")
        else:
            raw_list = [data]
    else:
        raw_list = data

    results: List[RawSection] = []
    for item in raw_list:
        act = item.get("act") or default_act or "Unknown"
        sec_no = str(item.get("section_no", "")).strip()
        title = str(item.get("title", "")).strip()
        body = clean_legal_text(str(item.get("body", "")))

        if not sec_no or not body:
            continue

        valid_from_val: Optional[datetime.date] = None
        if item.get("valid_from"):
            try:
                valid_from_val = datetime.date.fromisoformat(str(item["valid_from"]))
            except ValueError:
                pass

        valid_to_val: Optional[datetime.date] = None
        if item.get("valid_to"):
            try:
                valid_to_val = datetime.date.fromisoformat(str(item["valid_to"]))
            except ValueError:
                pass

        raw_sec = RawSection(
            act=act,
            section_no=sec_no,
            title=title,
            body=body,
            domain=item.get("domain", "statute"),
            audience=item.get("audience", ["judge", "lawyer"]),
            ipc_equivalent=item.get("ipc_equivalent"),
            valid_from=valid_from_val,
            valid_to=valid_to_val,
            source=item.get("source", "The Gazette of India"),
            license=item.get("license", OFFICIAL_INDIAN_LAW_LICENSE),
        )

        split_pieces = split_long_section(
            raw_sec, max_tokens=max_tokens, token_counter=token_counter
        )
        results.extend(split_pieces)

    return results


def validate_section(section: RawSection) -> bool:
    """Validate that a legal section satisfies minimum corpus hygiene constraints."""
    if not section.act or not section.section_no:
        return False
    if not section.body or len(section.body.strip()) < 10:
        return False
    if not section.audience:
        return False
    return True

