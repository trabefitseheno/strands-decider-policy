"""Deterministic check: a rewrite may not change, drop, or add any figure.

Figures = dates, times, money, numbers/percentages, plus any `must_preserve` strings
(places, eligibility rules) that must appear verbatim. Conservative by design: a rewrite
that spells "thirty" for "30" is rejected and the original is sent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_PATTERNS = [
    rf"\b{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b",  # October 30, 2026
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}\.?(?:,?\s+\d{{4}})?\b",  # 30 October 2026
    r"\b\d{4}-\d{2}-\d{2}\b",  # ISO
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?",  # times
    r"\$\s?\d[\d,]*(?:\.\d+)?",  # money
    r"\d+(?:[.,]\d+)*%?",  # any other number
    rf"\b{_MONTH}\b",  # bare month name
]
_RX = re.compile("|".join(f"(?:{p})" for p in _PATTERNS), re.IGNORECASE)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace(" ", " ")).strip()


def extract_figures(text: str) -> set[str]:
    return {_norm(m.group(0)) for m in _RX.finditer(text)}


@dataclass
class CheckResult:
    ok: bool
    missing: list[str] = field(default_factory=list)  # in source, absent from rewrite
    extra: list[str] = field(default_factory=list)  # in rewrite, absent from source
    missing_phrases: list[str] = field(default_factory=list)


def check_rewrite(original: str, rewrite: str, must_preserve: tuple[str, ...] = ()) -> CheckResult:
    src, new = extract_figures(original), extract_figures(rewrite)
    missing = sorted(src - new)
    extra = sorted(new - src)
    rw = _norm(rewrite)
    missing_phrases = [p for p in must_preserve if _norm(p) not in rw]
    return CheckResult(not (missing or extra or missing_phrases), missing, extra, missing_phrases)
