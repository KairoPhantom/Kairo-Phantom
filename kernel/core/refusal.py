"""
Kairo Phantom — Refusal Diagnostic UX (SPEC §S3, T8)

Produces clear, actionable refusal messages that name the cascade stage
that blocked the answer and suggest next steps.

Every refusal contains:
  - A clear LABEL ("No grounded source found")
  - The STAGE that blocked (e.g. "BLOCK", "FUZZY", "SEMANTIC")
  - An actionable SUGGESTION

The kernel imports NOTHING from /domains or /legacy.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from kernel.core.data_model import Answer

logger = logging.getLogger("kairo.refusal")

# ---------------------------------------------------------------------------
# Cascade stage descriptions
# ---------------------------------------------------------------------------
_STAGE_DESCRIPTIONS: dict[str, str] = {
    "BLOCK": "no exact/fuzzy/semantic/visual match above threshold",
    "FUZZY": "fuzzy match found but below the 0.92 threshold",
    "SEMANTIC": "semantic match found but below the 0.86 threshold or re-verification failed",
    "VISUAL": "visual retrieval attempted but IoU below 0.5 threshold",
    "NORMALIZE": "text normalization failed — input could not be processed",
    "EXACT": "exact match attempted but no verbatim source text found",
}

_STAGE_SUGGESTIONS: dict[str, str] = {
    "BLOCK": "The answer may not be in this document, or the relevant section wasn't extracted cleanly. Try rephrasing the query or verifying the document was ingested correctly.",
    "FUZZY": "A near-match was found but didn't meet the 0.92 similarity threshold. Check if the source text has typos or formatting differences.",
    "SEMANTIC": "A semantically similar passage was found but didn't pass re-verification. The meaning may be related but not directly supported by the source.",
    "VISUAL": "A visual region was identified but the overlap (IoU) was below 0.5. The relevant figure or table may need higher-resolution ingestion.",
    "NORMALIZE": "The input text could not be normalized for matching. Check for encoding issues or non-standard characters.",
    "EXACT": "No verbatim match was found in the source. The exact wording may differ — try a broader query.",
}


def format_refusal(answer: Answer) -> str:
    """Format a refusal Answer into a clear, actionable diagnostic message.

    The output always contains:
      1. A clear LABEL ("No grounded source found")
      2. The STAGE that blocked (naming the cascade stage)
      3. An actionable SUGGESTION

    Returns the answer text directly if the answer is not a refusal.
    """
    if not answer.refused:
        return answer.text

    stage = answer.refusal_stage or "BLOCK"
    reason = answer.refusal_reason or _STAGE_DESCRIPTIONS.get(
        stage, _STAGE_DESCRIPTIONS["BLOCK"]
    )
    suggestion = answer.refusal_suggestion or _STAGE_SUGGESTIONS.get(
        stage, _STAGE_SUGGESTIONS["BLOCK"]
    )

    return (
        f"No grounded source found — reached {stage}: {reason} "
        f"{suggestion}"
    )


def get_refusal_metadata(answer: Answer) -> dict[str, str]:
    """Return structured refusal metadata for logging/UI rendering.

    Always returns a dict with 'label', 'stage', 'reason', 'suggestion' keys.
    If the answer is not a refusal, returns empty strings for all fields.
    """
    if not answer.refused:
        return {
            "label": "",
            "stage": "",
            "reason": "",
            "suggestion": "",
        }

    stage = answer.refusal_stage or "BLOCK"
    return {
        "label": "No grounded source found",
        "stage": stage,
        "reason": answer.refusal_reason or _STAGE_DESCRIPTIONS.get(
            stage, _STAGE_DESCRIPTIONS["BLOCK"]
        ),
        "suggestion": answer.refusal_suggestion or _STAGE_SUGGESTIONS.get(
            stage, _STAGE_SUGGESTIONS["BLOCK"]
        ),
    }


def log_refusal(answer: Answer) -> None:
    """Write an audit-trail log entry for a refusal.

    Every refusal is logged with timestamp, query, stage, and reason.
    This provides the audit trail required by T8.
    """
    if not answer.refused:
        return

    metadata = get_refusal_metadata(answer)
    logger.warning(
        "REFUSAL_AUDIT | timestamp=%s | query=%s | stage=%s | reason=%s | suggestion=%s",
        datetime.now(timezone.utc).isoformat(),
        answer.query[:200],  # truncate for log safety
        metadata["stage"],
        metadata["reason"],
        metadata["suggestion"],
    )