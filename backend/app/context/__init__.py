"""Context filters package enforcing information isolation per courtroom agent role."""

from app.context.clerk import build_clerk_context, build_clerk_opening_prompt
from app.context.defendant import build_defendant_answer_prompt, build_defendant_context
from app.context.defense import (
    build_defense_closing_prompt,
    build_defense_context,
    build_defense_examination_prompt,
    build_defense_objection_prompt,
)
from app.context.judge import (
    build_judge_closing_prompt,
    build_judge_context,
    build_judge_opening_prompt,
)
from app.context.juror import (
    build_juror_context,
    build_juror_deliberation_prompt,
    build_juror_vote_prompt,
)
from app.context.prosecutor import (
    build_prosecutor_closing_prompt,
    build_prosecutor_context,
    build_prosecutor_examination_prompt,
    build_prosecutor_objection_prompt,
)
from app.context.verdict_judge import (
    build_verdict_judge_context,
    build_verdict_judge_prompt,
)
from app.context.witness import build_witness_answer_prompt, build_witness_context

__all__ = [
    "build_judge_context",
    "build_judge_opening_prompt",
    "build_judge_closing_prompt",
    "build_clerk_context",
    "build_clerk_opening_prompt",
    "build_prosecutor_context",
    "build_prosecutor_examination_prompt",
    "build_prosecutor_objection_prompt",
    "build_prosecutor_closing_prompt",
    "build_defense_context",
    "build_defense_examination_prompt",
    "build_defense_objection_prompt",
    "build_defense_closing_prompt",
    "build_witness_context",
    "build_witness_answer_prompt",
    "build_defendant_context",
    "build_defendant_answer_prompt",
    "build_juror_context",
    "build_juror_vote_prompt",
    "build_juror_deliberation_prompt",
    "build_verdict_judge_context",
    "build_verdict_judge_prompt",
]
