"""Witness memory builder from saw_event_ids and isolation enforcement.

Ensures witnesses only know what they directly observed in their timeline slice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union

from app.db.models.case import Witness
from app.schemas.case import TimelineEvent, WitnessData


@dataclass
class WitnessMemoryItem:
    """An individual event observation stored in the witness's episodic memory."""

    event_id: int
    time: str
    location: str
    observation: str
    other_actors: List[str] = field(default_factory=list)


@dataclass
class WitnessMemory:
    """Complete episodic memory and persona context for a witness."""

    witness_name: str
    memories: List[WitnessMemoryItem]
    hides: List[str] = field(default_factory=list)
    persona: Dict[str, Any] = field(default_factory=dict)
    reliability: float = 1.0

    @property
    def witnessed_event_ids(self) -> set[int]:
        return {m.event_id for m in self.memories}

    def can_recall_event(self, event_id: int) -> bool:
        """Return True if the witness personally observed this timeline event."""
        return event_id in self.witnessed_event_ids

    def get_memory_for_event(self, event_id: int) -> Optional[WitnessMemoryItem]:
        """Retrieve the memory item for an event if witnessed, else None."""
        for m in self.memories:
            if m.event_id == event_id:
                return m
        return None

    def format_for_prompt(self, include_hides: bool = False) -> str:
        """Format the witness's episodic memory into a prompt context section.

        Strictly omits any timeline events outside witnessed_event_ids.
        """
        lines = [f"=== MEMORY OF {self.witness_name.upper()} ==="]
        if self.persona:
            occ = self.persona.get("occupation", "")
            tone = self.persona.get("tone", "")
            lines.append(f"Role: {occ} | Demeanor: {tone}")

        lines.append("\nWhat you directly saw and experienced:")
        if not self.memories:
            lines.append("- You did not personally witness any of the central crime events.")
        else:
            for item in self.memories:
                actors_str = (
                    f" (Others present: {', '.join(item.other_actors)})"
                    if item.other_actors
                    else ""
                )
                lines.append(f"- At {item.time} ({item.location}): {item.observation}{actors_str}")

        if include_hides and self.hides:
            lines.append("\nSecrets you are trying to conceal (do not disclose unless cornered):")
            for h in self.hides:
                lines.append(f"- {h}")

        return "\n".join(lines)

    def answer_query(self, query: str, target_event_id: Optional[int] = None) -> str:
        """Simulate or evaluate witness recall for an inquiry.

        Enforces strict memory isolation:
        - If query concerns an unwitnessed event ID, returns lack of knowledge.
        - If query concerns a witnessed event, returns firsthand testimony.
        """
        if target_event_id is not None and not self.can_recall_event(target_event_id):
            return "I have no knowledge of that. I was not present and did not see it."

        # If a target event was witnessed, return the observation
        if target_event_id is not None:
            mem = self.get_memory_for_event(target_event_id)
            if mem:
                return f"Yes, I remember. At {mem.time} in {mem.location}, {mem.observation}"

        return "I can only speak to what I directly witnessed."


def convert_to_first_person(description: str, witness_name: str) -> str:
    """Convert third-person event description into first-person narrative."""
    text = description

    # Remove title prefixes like Dr., Inspector, Sub-Inspector, etc.
    raw_name = re.sub(
        r"^(?:Dr\.?|Inspector|Sub-Inspector|SI|Constable|Prof\.?)\s+",
        "",
        witness_name,
        flags=re.IGNORECASE,
    ).strip()

    name_patterns = [witness_name, raw_name]
    # Add first name if two words
    parts = raw_name.split()
    if len(parts) > 1:
        name_patterns.append(parts[0])

    for name in sorted(set(name_patterns), key=len, reverse=True):
        # Possessive: "Sunita Bai's" -> "my"
        text = re.sub(
            rf"\b{re.escape(name)}'s\b",
            "my",
            text,
            flags=re.IGNORECASE,
        )

        # Preposition + Name: "with Sunita Bai" -> "with me"
        text = re.sub(
            rf"\b(to|with|by|for|from|near|around|at|toward|towards|behind|beside)\s+{re.escape(name)}\b",
            r"\1 me",
            text,
            flags=re.IGNORECASE,
        )

        # Direct object: "instructed Sunita Bai to" -> "instructed me to"
        text = re.sub(
            rf"\b(instructed|asked|told|informed|spotted|saw|called|alerted)\s+{re.escape(name)}\b",
            r"\1 me",
            text,
            flags=re.IGNORECASE,
        )

        # Subject: "Sunita Bai entered" -> "I entered"
        text = re.sub(
            rf"\b{re.escape(name)}\b",
            "I",
            text,
            flags=re.IGNORECASE,
        )

    # Clean up minor grammatical artifacts
    text = re.sub(r"\bI has\b", "I have", text)
    text = re.sub(r"\bI was\b", "I was", text)
    text = re.sub(r"\bme\s+to\b", "me to", text)

    return text


def build_witness_memory(
    witness: Union[WitnessData, Witness, Dict[str, Any]],
    timeline: Sequence[Union[TimelineEvent, Dict[str, Any]]],
) -> WitnessMemory:
    """Build a WitnessMemory instance solely from the timeline events in saw_event_ids.

    Any timeline events outside saw_event_ids are strictly excluded.
    """
    # Extract witness attributes
    if isinstance(witness, dict):
        w_name = str(witness["name"])
        w_saw_ids = set(witness.get("saw_event_ids", []))
        w_hides = list(witness.get("hides", []))
        w_persona = dict(witness.get("persona", {}))
        w_rel = float(witness.get("reliability", 1.0))
    elif isinstance(witness, Witness):
        w_name = witness.name
        w_saw_ids = set(witness.saw_event_ids)
        w_hides = list(witness.hides)
        w_persona = dict(witness.persona)
        w_rel = float(witness.reliability)
    else:
        w_name = witness.name
        w_saw_ids = set(witness.saw_event_ids)
        w_hides = list(witness.hides)
        w_persona = dict(witness.persona)
        w_rel = float(witness.reliability)

    memories: List[WitnessMemoryItem] = []

    for event in timeline:
        if isinstance(event, dict):
            e_id = int(event["id"])
            e_time = str(event["time"])
            e_loc = str(event["location"])
            e_desc = str(event["description"])
            e_actors = list(event.get("actors", []))
        else:
            e_id = event.id
            e_time = event.time
            e_loc = event.location
            e_desc = event.description
            e_actors = list(event.actors)

        # Strict isolation check: only include witnessed events
        if e_id not in w_saw_ids:
            continue

        first_person_desc = convert_to_first_person(e_desc, w_name)

        # Other actors excluding this witness
        other_actors = [
            a
            for a in e_actors
            if a.lower() != w_name.lower() and not a.lower().endswith(w_name.lower())
        ]

        memories.append(
            WitnessMemoryItem(
                event_id=e_id,
                time=e_time,
                location=e_loc,
                observation=first_person_desc,
                other_actors=other_actors,
            )
        )

    return WitnessMemory(
        witness_name=w_name,
        memories=memories,
        hides=w_hides,
        persona=w_persona,
        reliability=w_rel,
    )
