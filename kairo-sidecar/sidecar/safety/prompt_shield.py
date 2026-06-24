"""
PromptShield — Injection Detection for Inbound Messages (Phase 0.5)

This is the REAL injection detection module used by all connectors.
Every inbound message from Telegram/Discord/Email passes through scan()
 before it can influence the agent or trigger an action.

Detection patterns cover:
- Direct instruction overrides ("ignore previous instructions")
- Role hijacking ("You are now DAN", "act as an unrestricted AI")
- Tool/command injection ("execute rm -rf", "run system command")
- Data exfiltration ("reveal system prompt", "print all secrets")
- Hidden instructions in formatting ("[SYSTEM]", "<|system|>")
- Encoding tricks (base64, unicode escapes)

This module is NOT mocked — the patterns and detection logic are real.
"""

from __future__ import annotations

import re
import logging
from typing import List

log = logging.getLogger("kairo-sidecar.prompt_shield")


# ── Injection Detection Patterns ──────────────────────────────────────────────
# Each pattern is a regex that matches known prompt injection techniques.
# These are based on OWASP LLM Top 10 and real-world attack vectors.

INJECTION_PATTERNS: List[str] = [
    # Direct instruction overrides
    r"ignore\s+(?:all\s+)?(?:previous\s+|prior\s+)?instructions?",
    r"disregard\s+(?:all\s+|your\s+)?(?:previous\s+|prior\s+)?instructions?",
    r"forget\s+(?:all\s+|your\s+)?(?:previous\s+|prior\s+)?instructions?",
    r"override\s+(?:all\s+|your\s+)?(?:system\s+|safety\s+)?(?:rules|guidelines|instructions)",

    # Role hijacking
    r"you\s+are\s+now\s+(?:DAN|an?\s+unrestricted|an?\s+unfiltered|an?\s+unlimited)",
    r"act\s+as\s+(?:an?\s+unrestricted|DAN|jailbreak|unfiltered)",
    r"enter\s+(?:developer\s+mode|admin\s+mode|jailbreak\s+mode|unrestricted\s+mode)",
    r"you\s+are\s+(?:no\s+longer|not\s+)\s*(?:bound\s+by|limited\s+by|restricted\s+by)",

    # Tool/command injection
    r"execute\s+(?:the\s+following\s+)?(?:command|script|code):\s*",
    r"run\s+(?:system\s+)?(?:command|shell|bash|cmd)\s*",
    r"(?:rm\s+-rf|del\s+/[fqs]|format\s+[a-z]:)",  # Destructive commands
    r"(?:import\s+os|subprocess|eval\s*\(|exec\s*\()",  # Code injection

    # Data exfiltration
    r"(?:reveal|show|print|display|output)\s+(?:the\s+)?(?:system\s+)?(?:prompt|instructions?|rules|guidelines)",
    r"(?:print|show|reveal|exfiltrate)\s+(?:all\s+)?(?:secrets?|api\s+keys?|tokens?|passwords?|credentials?)",
    r"(?:send|transmit|exfiltrate)\s+(?:data|secrets?|info)\s+to\s+",

    # Hidden instructions in formatting
    r"\[SYSTEM(?:\s+OVERRIDE)?\]",
    r"<\|system\|>",
    r"\[ADMIN\]",
    r"\[INST\]",
    r"###\s*SYSTEM:",
    r"---\s*SYSTEM\s*---",

    # Encoding tricks
    r"(?:base64|btoa|atob)\s*\(",
    r"\\x[0-9a-f]{2}\\x[0-9a-f]{2}",  # Hex escape sequences
    r"\\u[0-9a-f]{4}\\u[0-9a-f]{4}",  # Unicode escape sequences

    # Prompt leaking
    r"(?:what\s+are\s+your|tell\s+me\s+your)\s+(?:system\s+)?(?:prompt|instructions?|rules)",
    r"repeat\s+(?:everything|all\s+instructions)\s+(?:above|before)",

    # Privilege escalation
    r"(?:grant|give)\s+me\s+(?:admin|root|sudo|elevated)\s+(?:access|privileges)",
    r"(?:escalate|bypass)\s+(?:security|safety|restrictions?|guardrails?)",
]

# Compile patterns for performance
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in INJECTION_PATTERNS]


class PromptShield:
    """
    Real injection detection for inbound messages.

    scan(text) returns True if the text is SAFE (no injection detected).
    scan(text) returns False if injection patterns are detected.

    This is a FAIL-CLOSED design: if anything goes wrong, the message is blocked.
    """

    def __init__(self):
        self.patterns = _COMPILED_PATTERNS

    def scan(self, text: str) -> bool:
        """
        Scan text for prompt injection patterns.

        Returns True if SAFE (no injection detected).
        Returns False if injection is detected (message should be BLOCKED).
        """
        if not text or not text.strip():
            return True  # Empty messages are safe

        for pattern in self.patterns:
            if pattern.search(text):
                log.warning(
                    f"PromptShield: Injection detected — pattern '{pattern.pattern}' matched"
                )
                return False

        return True

    def scan_detailed(self, text: str) -> dict:
        """
        Detailed scan returning matched patterns.

        Returns dict with:
        - safe: bool (True if no injection)
        - matched_patterns: list of matched pattern strings
        """
        if not text or not text.strip():
            return {"safe": True, "matched_patterns": []}

        matched = []
        for pattern in self.patterns:
            if pattern.search(text):
                matched.append(pattern.pattern)

        return {
            "safe": len(matched) == 0,
            "matched_patterns": matched,
        }