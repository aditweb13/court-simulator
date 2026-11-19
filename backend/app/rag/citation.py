"""Citation validation and verification against retrieved legal chunks.

Enforces anti-hallucination constraint: any statutory section or constitutional
article cited by an AI agent must be strictly present among the knowledge chunks
retrieved in that agent's current retrieval context.
"""

from __future__ import annotations

import logging
import re
from typing import List, Set, Tuple

from app.rag.ipc_bns_map import get_bns_equivalent
from app.rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

# Regular expressions for detecting statutory and constitutional citations
_CITATION_DETECTION_PATTERNS = [
    # "Section 103 BNS", "s. 103 of BNS", "Section 103 of the Bharatiya Nyaya Sanhita"
    re.compile(
        r"\b(?:Section|Sec\.?|s\.)\s*(\d+[A-Z]?)\s*(?:of\s+(?:the\s+)?)?(BNS|BNSS|BSA)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(BNS|BNSS|BSA)\s*(?:Section|Sec\.?|s\.)?\s*(\d+[A-Z]?)\b",
        re.IGNORECASE,
    ),
    # "Article 21", "Art. 21", "Article 21 of Constitution"
    re.compile(
        r"\b(?:Article|Art\.?)\s*(\d+[A-Z]?)(?:\s*(?:of\s+(?:the\s+)?)?(?:Constitution|COI))?\b",
        re.IGNORECASE,
    ),
    # "IPC 302", "Section 302 IPC"
    re.compile(
        r"\b(?:Section|Sec\.?|s\.)?\s*(\d+[A-Z]?)\s*(?:of\s+(?:the\s+)?)?(IPC)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(IPC)\s*(?:Section|Sec\.?|s\.)?\s*(\d+[A-Z]?)\b",
        re.IGNORECASE,
    ),
]


def extract_cited_provisions(text: str) -> List[Tuple[str, str]]:
    """Extract all statutory and constitutional citations from an agent's statement.

    Returns a list of (act, section_number) tuples.
    IPC references are automatically normalized to corresponding BNS provisions.
    """
    citations: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    for pat in _CITATION_DETECTION_PATTERNS:
        for match in pat.finditer(text):
            matched_text = match.group(0).upper()
            groups = match.groups()

            if "IPC" in matched_text:
                raw_sec = groups[0] if groups[0].isdigit() else groups[1]
                sec_val = raw_sec.strip().upper()
                bns_equiv = get_bns_equivalent(sec_val)
                pair = ("BNS", bns_equiv if bns_equiv else sec_val)
            elif len(groups) == 1:
                # Article match for Constitution
                pair = ("CONSTITUTION", groups[0].strip().upper())
            else:
                val1, val2 = groups[0].strip().upper(), groups[1].strip().upper()
                if val1 in {"BNS", "BNSS", "BSA"}:
                    pair = (val1, val2)
                elif val2 in {"BNS", "BNSS", "BSA"}:
                    pair = (val2, val1)
                else:
                    continue

            if pair not in seen:
                seen.add(pair)
                citations.append(pair)

    return citations


def verify_citations(
    agent_text: str,
    retrieved_chunks: List[RetrievedChunk],
) -> Tuple[bool, List[str]]:
    """Validate that every statutory citation in agent_text appears in retrieved_chunks.

    Returns (is_valid, list_of_violations).
    If any cited section is not supported by the retrieved chunks, validation fails.
    """
    cited = extract_cited_provisions(agent_text)
    if not cited:
        # No citations present -> valid
        return True, []

    # Build set of supported provisions from retrieved chunks
    supported: Set[Tuple[str, str]] = set()
    for chunk in retrieved_chunks:
        act_norm = chunk.act.upper()
        # Clean section number e.g. "103 (Part 1/2)" -> "103"
        clean_sec = chunk.section_no.split()[0].split("(")[0].strip().upper()
        supported.add((act_norm, clean_sec))
        if chunk.parent_section:
            supported.add((act_norm, chunk.parent_section.strip().upper()))
        if chunk.ipc_equivalent:
            supported.add(("IPC", chunk.ipc_equivalent.strip().upper()))

    violations: List[str] = []
    for act, sec in cited:
        if (act, sec) not in supported:
            violations.append(f"Unretrieved citation: {act} Section/Article {sec}")

    is_valid = len(violations) == 0
    return is_valid, violations

