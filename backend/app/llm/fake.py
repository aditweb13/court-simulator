"""Deterministic fake LLM client for unattended batch simulations and fast testing.

Generates schema-compliant outputs for all courtroom roles without external API calls.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.llm.logger import record_llm_call
from app.orchestrator.schemas import (
    ClerkAnnouncementOutput,
    ClosingArgumentOutput,
    ExaminationQuestionOutput,
    JudgeClosingOutput,
    JudgeOpeningOutput,
    JudgeVerdictOutput,
    JurorDeliberationOutput,
    JurorVoteOutput,
    ObjectionOutput,
    WitnessAnswerOutput,
)

logger = logging.getLogger("app.llm.fake")

T = TypeVar("T", bound=BaseModel)


class DeterministicFakeLLM:
    """Configurable fake LLM handler generating valid structured outputs."""

    def __init__(
        self,
        default_guilty_prob: float = 0.82,
        tokens_per_call_in: int = 150,
        tokens_per_call_out: int = 50,
        simulated_latency_ms: int = 15,
    ) -> None:
        self.default_guilty_prob = default_guilty_prob
        self.tokens_per_call_in = tokens_per_call_in
        self.tokens_per_call_out = tokens_per_call_out
        self.simulated_latency_ms = simulated_latency_ms
        self.total_tokens_in: int = 0
        self.total_tokens_out: int = 0
        self.total_calls: int = 0

    async def chat(
        self,
        tier: str,
        messages: List[Dict[str, str]],
        *,
        response_model: Optional[Type[T]] = None,
        timeout: float = 60.0,
        max_attempts: int = 8,
        trial_id: Optional[UUID] = None,
        agent_role: Optional[str] = None,
    ) -> Any:
        """Mimics the signature of app.llm.router.chat()."""
        self.total_calls += 1
        self.total_tokens_in += self.tokens_per_call_in
        self.total_tokens_out += self.tokens_per_call_out

        # Record simulated call in database audit table
        try:
            await record_llm_call(
                provider="fake",
                model=f"fake-{tier}",
                key_alias="fake#local",
                tokens_in=self.tokens_per_call_in,
                tokens_out=self.tokens_per_call_out,
                latency_ms=self.simulated_latency_ms,
                status="ok",
                trial_id=trial_id,
                agent_role=agent_role,
            )
        except Exception as exc:
            logger.debug("Fake LLM record_llm_call skipped: %s", exc)

        if response_model is None:
            return "Deterministic simulated courtroom dialogue text."

        return self._generate_output(response_model, messages, agent_role)

    def _generate_output(
        self,
        response_model: Type[T],
        messages: List[Dict[str, str]],
        agent_role: Optional[str],
    ) -> Any:
        # 1. Openings & Announcements
        if response_model is JudgeOpeningOutput:
            return JudgeOpeningOutput(
                text=(
                    "The Court is now in session. "
                    "The clerk will read the charges against the accused."
                ),
                action="gavel",
                emotion="neutral",
                camera="judge",
            )
        if response_model is ClerkAnnouncementOutput:
            return ClerkAnnouncementOutput(
                text="Case is called under Section 103(1) of the Bharatiya Nyaya Sanhita, 2023.",
                action="stand",
                emotion="neutral",
                camera="wide",
            )

        # 2. Examination
        if response_model is ExaminationQuestionOutput:
            return ExaminationQuestionOutput(
                text="Please state to the court what you observed on the afternoon in question.",
                action="point",
                emotion="firm",
                camera="witness",
            )
        if response_model is WitnessAnswerOutput:
            return WitnessAnswerOutput(
                text=(
                    "I was present at the scene and saw the accused "
                    "enter the premises shortly before 3 PM."
                ),
                action="talk",
                emotion="nervous",
                camera="witness",
            )
        if response_model is ObjectionOutput:
            return ObjectionOutput(
                raise_objection=False,
            )

        # 3. Closings
        if response_model is ClosingArgumentOutput:
            if agent_role == "defense":
                return ClosingArgumentOutput(
                    text=(
                        "The prosecution failed to establish "
                        "culpability beyond reasonable doubt."
                    ),
                    action="stand",
                    emotion="firm",
                    camera="close",
                )
            return ClosingArgumentOutput(
                text=(
                    "The forensic proof and witness testimony "
                    "conclusively prove the offence."
                ),
                action="stand",
                emotion="firm",
                camera="close",
            )
        if response_model is JudgeClosingOutput:
            return JudgeClosingOutput(
                text=(
                    "Arguments have concluded. "
                    "The assessors will now deliberate upon the facts."
                ),
                action="sit",
                emotion="neutral",
                camera="judge",
            )

        # 4. Jurors
        if response_model is JurorVoteOutput:
            prob = self.default_guilty_prob
            full_txt = " ".join(m.get("content", "") for m in messages).lower()
            if "skeptical" in full_txt:
                prob = max(0.55, prob - 0.15)
            elif "analytic" in full_txt or "empirical" in full_txt:
                prob = min(0.92, prob + 0.05)

            is_guilty = prob >= 0.75
            return JurorVoteOutput(
                guilty=is_guilty,
                guilt_probability=round(prob, 2),
                confidence=0.85,
                reasoning=(
                    "The admitted exhibits and testimony "
                    "satisfy the standard of proof."
                ),
                cited_turn_seqs=[2, 3],
            )
        if response_model is JurorDeliberationOutput:
            return JurorDeliberationOutput(
                statement=(
                    "Considering corroborating statements, "
                    "the timeline appears consistent."
                ),
                current_leaning=(
                    "guilty" if self.default_guilty_prob >= 0.75 else "not_guilty"
                ),
            )

        # 5. Verdict Judges
        if response_model is JudgeVerdictOutput:
            prob = self.default_guilty_prob
            is_guilty = prob >= 0.75
            return JudgeVerdictOutput(
                guilty=is_guilty,
                guilt_probability=round(prob, 2),
                confidence=0.90,
                reasoning=(
                    "Upon reviewing the clean admitted record under Bharatiya Sakshya Adhiniyam "
                    "standards, statutory ingredients are fulfilled."
                ),
                cited_sections=["BNS Section 103(1)"],
            )

        # Fallback instantiate if possible
        try:
            return response_model()  # type: ignore[call-arg]
        except Exception:
            raise ValueError(
                f"DeterministicFakeLLM does not support response_model: {response_model}"
            )
