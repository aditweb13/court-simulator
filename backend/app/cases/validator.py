"""Validation rules for courtroom Case definitions and ground truth constraints."""

from __future__ import annotations

import datetime
from typing import List

from app.schemas.case import CaseSchema


class CaseValidationError(ValueError):
    """Raised when a case violates courtroom or legal simulation constraints."""


def validate_case_integrity(case: CaseSchema) -> List[str]:
    """Validate cross-entity business rules for a CaseSchema instance.

    Checks:
    - Timeline has at least 1 event and unique IDs
    - All dated timeline events occur on or after 2024-07-01 (BNS effective date)
    - At least one evidence exhibit is inadmissible, with reason_inadmissible given
    - Exhibit numbers are unique
    - Witness saw_event_ids only reference existing timeline IDs
    - Witness names are unique
    - Witness reliability is between 0.0 and 1.0
    """
    errors: List[str] = []

    # 1. Timeline integrity
    if not case.truth.timeline:
        errors.append("Case truth timeline must contain at least 1 event.")

    timeline_ids = {event.id for event in case.truth.timeline}
    if len(timeline_ids) != len(case.truth.timeline):
        errors.append("Timeline contains duplicate event IDs.")

    # 2. Offence date rule: must be on or after 2024-07-01 so BNS applies
    bns_start_date = datetime.date(2024, 7, 1)
    for event in case.truth.timeline:
        if len(event.time) >= 10:
            try:
                event_date = datetime.date.fromisoformat(event.time[:10])
                if event_date < bns_start_date:
                    errors.append(
                        f"Timeline event {event.id} date '{event.time[:10]}' "
                        "is before BNS effective date 2024-07-01."
                    )
            except ValueError:
                pass  # Non-ISO relative timestamp

    # 3. Evidence integrity
    inadmissible_count = 0
    exhibit_numbers: set[str] = set()
    for ev in case.evidence:
        if ev.exhibit_no in exhibit_numbers:
            errors.append(f"Duplicate exhibit number: '{ev.exhibit_no}'.")
        exhibit_numbers.add(ev.exhibit_no)

        if not ev.admissible:
            inadmissible_count += 1
            if not ev.reason_inadmissible or not ev.reason_inadmissible.strip():
                errors.append(
                    f"Inadmissible exhibit '{ev.exhibit_no}' must specify reason_inadmissible."
                )

    if inadmissible_count == 0:
        errors.append("Case must contain at least one inadmissible evidence exhibit.")

    # 4. Witness integrity
    witness_names: set[str] = set()
    for w in case.witnesses:
        if w.name in witness_names:
            errors.append(f"Duplicate witness name: '{w.name}'.")
        witness_names.add(w.name)

        invalid_ids = [eid for eid in w.saw_event_ids if eid not in timeline_ids]
        if invalid_ids:
            errors.append(
                f"Witness '{w.name}' references non-existent timeline event IDs: {invalid_ids}."
            )

        if not (0.0 <= w.reliability <= 1.0):
            errors.append(
                f"Witness '{w.name}' reliability {w.reliability} is outside range [0.0, 1.0]."
            )

    return errors


def assert_case_valid(case: CaseSchema) -> None:
    """Raise CaseValidationError if case fails integrity checks."""
    errors = validate_case_integrity(case)
    if errors:
        raise CaseValidationError(
            f"Case validation failed for '{case.slug}':\n" + "\n".join(f"- {e}" for e in errors)
        )
