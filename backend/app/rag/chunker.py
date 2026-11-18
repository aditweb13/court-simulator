"""Legal document chunker and section parser.

Extracts discrete legal sections from statutory acts, normalizes legislative
text, and attaches mandatory domain, audience, and licensing metadata.
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

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


def parse_act_text(
    raw_text: str,
    act_name: str,
    *,
    domain: str = "statute",
    audience: Optional[List[str]] = None,
    valid_from: Optional[datetime.date] = None,
    source: str = "The Gazette of India",
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

        sections.append(
            RawSection(
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
        )

    return sections


def parse_act_json(
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    default_act: Optional[str] = None,
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

        # Optional valid_from date
        valid_from_val: Optional[datetime.date] = None
        if item.get("valid_from"):
            try:
                valid_from_val = datetime.date.fromisoformat(str(item["valid_from"]))
            except ValueError:
                pass

        results.append(
            RawSection(
                act=act,
                section_no=sec_no,
                title=title,
                body=body,
                domain=item.get("domain", "statute"),
                audience=item.get("audience", ["judge", "lawyer"]),
                ipc_equivalent=item.get("ipc_equivalent"),
                valid_from=valid_from_val,
                source=item.get("source", "The Gazette of India"),
                license=item.get("license", OFFICIAL_INDIAN_LAW_LICENSE),
            )
        )

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
