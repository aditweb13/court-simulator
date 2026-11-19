"""Rules engine for evidentiary admissibility under Bharatiya Sakshya Adhiniyam, 2023.

Pure functions only — no side-effects or database/LLM dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def evaluate_evidence_admissibility(
    evidence_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """Determine whether an exhibit is admissible under statutory Indian evidence rules.

    Returns:
        (is_admissible, rejection_reason)
    """
    meta = metadata or {}
    ev_type = evidence_type.lower().strip()

    # Rule 1: Electronic Record Certificate requirement under BSA Section 63
    # (replaces former Indian Evidence Act Section 65B)
    if ev_type in ("electronic", "digital", "phone_log", "cctv", "audio_recording"):
        has_certificate = meta.get("bsa_63_certificate", meta.get("certificate_attached", False))
        if not has_certificate:
            return (
                False,
                "Inadmissible under Section 63 of Bharatiya Sakshya Adhiniyam, 2023: "
                "Missing mandatory electronic record certificate proving device integrity "
                "and custody.",
            )

    # Rule 2: Inadmissibility of Confession made to Police Officer under BSA Section 23
    # (replaces former Indian Evidence Act Section 25)
    if meta.get("police_confession", False) or ev_type == "police_confession":
        return (
            False,
            "Inadmissible under Section 23 of Bharatiya Sakshya Adhiniyam, 2023: "
            "Confessions made to a police officer are strictly inadmissible against the accused.",
        )

    # Rule 3: Secondary Evidence prerequisites under BSA Section 60
    # Secondary evidence requires established loss or destruction of original
    if meta.get("is_secondary_evidence", False) and not meta.get("original_loss_proven", False):
        return (
            False,
            "Inadmissible under Section 60 of Bharatiya Sakshya Adhiniyam, 2023: "
            "Secondary evidence is inadmissible without foundational proof of "
            "original loss or destruction.",
        )

    return True, None
