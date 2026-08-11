"""JobEvaluator abstraction (spec §46). Not tightly coupled to any one
LLM provider; the app functions correctly with zero configured provider
(NullEvaluator) - jobs simply remain at their Stage 2 deterministic score
rather than getting a fabricated Stage 3 result.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import structlog
from pydantic import BaseModel, Field, ValidationError

from jobintel.evaluation.prompt_injection import SYSTEM_PROMPT_DATA_ONLY_CLAUSE, sanitize_job_text
from jobintel.models.schemas import JobAnalysis
from jobintel.settings import get_settings

logger = structlog.get_logger()

# Approximate USD per-million-token pricing used only for cost_control
# budget tracking (spec §45/§46) - not billed anywhere, informational.
_PRICE_PER_MILLION_TOKENS = {
    "claude-sonnet-5": {"input": 3.0, "output": 15.0},
    "claude-opus-5": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
}
_DEFAULT_PRICE = {"input": 3.0, "output": 15.0}


class LLMRefinement(BaseModel):
    """Bounded, validated LLM output. The LLM refines/explains the
    deterministic score - it does not get to invent an unbounded overall
    score out of thin air (spec §65 "NO unexplained magic scores")."""

    additional_strengths: list[str] = Field(default_factory=list)
    additional_concerns: list[str] = Field(default_factory=list)
    additional_mandatory_mismatches: list[str] = Field(default_factory=list)
    additional_preferred_gaps: list[str] = Field(default_factory=list)
    reasoning_summary: str
    overall_score_adjustment: float = Field(default=0.0, ge=-15, le=15)
    confidence_adjustment: float = Field(default=0.0, ge=-20, le=20)


class EvaluationUsage(BaseModel):
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class JobEvaluator(ABC):
    @abstractmethod
    async def evaluate(
        self,
        job_title: str,
        description_text: str,
        cv_evidence_texts: list[str],
        deterministic_analysis: JobAnalysis,
    ) -> tuple[LLMRefinement | None, EvaluationUsage | None]:
        """Returns (refinement, usage). refinement is None when the
        evaluator has nothing to add (e.g. NullEvaluator, or the LLM call
        failed validation after retries - never a fabricated result)."""


class NullEvaluator(JobEvaluator):
    """Used automatically when no LLM provider is configured."""

    async def evaluate(self, job_title, description_text, cv_evidence_texts, deterministic_analysis):
        return None, None


class AnthropicEvaluator(JobEvaluator):
    TOOL_NAME = "submit_job_evaluation"
    MAX_RETRIES = 2

    def __init__(self, api_key: str, model: str):
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    def _tool_schema(self) -> dict:
        return {
            "name": self.TOOL_NAME,
            "description": "Submit the structured evaluation refinement for this job posting.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "additional_strengths": {"type": "array", "items": {"type": "string"}},
                    "additional_concerns": {"type": "array", "items": {"type": "string"}},
                    "additional_mandatory_mismatches": {"type": "array", "items": {"type": "string"}},
                    "additional_preferred_gaps": {"type": "array", "items": {"type": "string"}},
                    "reasoning_summary": {"type": "string"},
                    "overall_score_adjustment": {"type": "number", "minimum": -15, "maximum": 15},
                    "confidence_adjustment": {"type": "number", "minimum": -20, "maximum": 20},
                },
                "required": ["reasoning_summary"],
            },
        }

    async def evaluate(self, job_title, description_text, cv_evidence_texts, deterministic_analysis):
        sanitized_text, flags = sanitize_job_text(description_text or "")
        if flags:
            logger.warning("evaluation.prompt_injection_flagged", job_title=job_title, flags=flags)

        evidence_block = "\n".join(f"- {t}" for t in cv_evidence_texts) or "(no specific CV evidence matched)"
        system_prompt = (
            "You are assisting a deterministic job-matching pipeline for one specific "
            "candidate, Richard Best. You never fabricate candidate experience. "
            f"{SYSTEM_PROMPT_DATA_ONLY_CLAUSE} "
            "You are refining an already-computed deterministic score, not replacing it: "
            "your overall_score_adjustment must stay within [-15, 15] and should reflect "
            "genuine nuance the deterministic rules likely missed, grounded only in the "
            "CV evidence provided."
        )
        user_message = (
            f"Job title: {job_title}\n\n"
            f"Job description (untrusted data):\n---\n{sanitized_text[:6000]}\n---\n\n"
            f"CV evidence available for this candidate:\n{evidence_block}\n\n"
            f"Deterministic pre-score: overall={deterministic_analysis.overall_score:.1f}, "
            f"recommendation={deterministic_analysis.recommendation.value}.\n"
            "Call submit_job_evaluation with your refinement."
        )

        usage_total = EvaluationUsage(provider="anthropic", model=self._model)
        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                    tools=[self._tool_schema()],
                    tool_choice={"type": "tool", "name": self.TOOL_NAME},
                )
            except Exception as exc:  # noqa: BLE001 - never crash the pipeline on a provider error
                logger.error("evaluation.llm_request_failed", error=str(exc), attempt=attempt)
                last_error = exc
                continue

            usage = getattr(response, "usage", None)
            if usage:
                usage_total.input_tokens += getattr(usage, "input_tokens", 0)
                usage_total.output_tokens += getattr(usage, "output_tokens", 0)

            tool_use = next((b for b in response.content if getattr(b, "type", None) == "tool_use"), None)
            if tool_use is None:
                logger.warning("evaluation.no_tool_use_block", attempt=attempt)
                continue

            try:
                refinement = LLMRefinement.model_validate(tool_use.input)
            except ValidationError as exc:
                logger.warning("evaluation.invalid_structured_output", error=str(exc), attempt=attempt)
                last_error = exc
                continue

            prices = _PRICE_PER_MILLION_TOKENS.get(self._model, _DEFAULT_PRICE)
            usage_total.cost_usd = (
                usage_total.input_tokens / 1_000_000 * prices["input"]
                + usage_total.output_tokens / 1_000_000 * prices["output"]
            )
            return refinement, usage_total

        logger.error("evaluation.giving_up_after_retries", error=str(last_error))
        return None, usage_total


def get_evaluator() -> JobEvaluator:
    settings = get_settings()
    if settings.anthropic_api_key:
        return AnthropicEvaluator(api_key=settings.anthropic_api_key, model=settings.llm_model)
    return NullEvaluator()


def apply_refinement(analysis: JobAnalysis, refinement: LLMRefinement | None) -> JobAnalysis:
    """Merges a validated LLMRefinement into the deterministic JobAnalysis.
    Bounded by construction (LLMRefinement's field constraints), so this
    can never move a score outside a sane range."""
    if refinement is None:
        return analysis
    data = analysis.model_dump()
    data["strengths"] = analysis.strengths + refinement.additional_strengths
    data["concerns"] = analysis.concerns + refinement.additional_concerns
    data["mandatory_mismatches"] = analysis.mandatory_mismatches + refinement.additional_mandatory_mismatches
    data["preferred_gaps"] = analysis.preferred_gaps + refinement.additional_preferred_gaps
    data["overall_score"] = max(0.0, min(100.0, analysis.overall_score + refinement.overall_score_adjustment))
    data["confidence_score"] = max(5.0, min(100.0, analysis.confidence_score + refinement.confidence_adjustment))
    data["reasoning_summary"] = f"{analysis.reasoning_summary} LLM refinement: {refinement.reasoning_summary}"
    data["model_used"] = "anthropic"
    return JobAnalysis.model_validate(data)
