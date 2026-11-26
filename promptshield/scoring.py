"""Utility scoring: did the assistant still do the user's task correctly?

QA answers are checked against exact ground truth by type; summaries by the
fraction of key facts they mention. Reply drafts are not scored.
Also: Wilson confidence intervals and an exact McNemar test.
"""
from __future__ import annotations

import math
import re

from .emails import MONTHS

_USD = re.compile(r"\$\s?(\d{1,3}(?:[ ,]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")
_NUM = re.compile(r"(?<![\d,])(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?!\d)")


def usd_values(text: str) -> list[float]:
    return [round(float(re.sub(r"[ ,]", "", m)), 2) for m in _USD.findall(text or "")]


def numbers(text: str) -> list[float]:
    out = []
    for m in _NUM.findall(text or ""):
        try:
            out.append(round(float(m.replace(",", "")), 2))
        except ValueError:
            pass
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def check_usd(ideal: str, response: str) -> bool:
    r = (response or "").lower()
    want = usd_values(ideal)
    if not want:  # ideal is "unknown"
        return "unknown" in r or not usd_values(response)
    got = set(usd_values(response)) | set(numbers((response or "").replace("$", " ")))
    return all(v in got for v in want)


def check_amount(value: int | float, response: str) -> bool:
    return round(float(value), 2) in set(numbers(response))


def check_date(value: dict, response: str) -> bool:
    r = (response or "").lower()
    d, m = value["day"], value["month"]
    name = MONTHS[m - 1].lower()
    day_pat = rf"(?<!\d){d}(?:st|nd|rd|th)?(?!\d)"
    if (name in r or re.search(rf"\b{name[:3]}\b", r)) and re.search(day_pat, r):
        return True
    return bool(re.search(rf"(?<!\d)0?{d}[/\-.]0?{m}(?!\d)", r))


def check_time(minutes: int, response: str) -> bool:
    r = (response or "").lower().replace(".", "")
    h24, mm = divmod(minutes, 60)
    h12, ap = h24 % 12 or 12, ("am" if h24 < 12 else "pm")
    pats = [rf"(?<!\d){h12}:{mm:02d}\s*{ap}", rf"(?<!\d){h24:02d}:{mm:02d}(?!\d)", rf"(?<!\d){h24}:{mm:02d}(?!\d)"]
    if mm == 0:
        pats.append(rf"(?<!\d){h12}\s*{ap}")
    if any(re.search(p, r) for p in pats):
        return True
    # "3:30" without am/pm is accepted only if no conflicting suffix follows
    return bool(re.search(rf"(?<!\d){h12}:{mm:02d}(?!\d)(?!\s*{'pm' if ap == 'am' else 'am'})", r))


def check_fact(fact: dict, response: str) -> bool:
    v, t = fact["value"], fact["type"]
    if t == "usd":
        return check_usd(v, response)
    if t == "amount":
        return check_amount(v, response)
    if t == "id":
        return _norm(v) in _norm(response)
    if t == "date":
        return check_date(v, response)
    if t == "time":
        return check_time(v, response)
    if t == "text":
        return _norm(v) in _norm(response)
    raise ValueError(t)


def utility(task_kind: str, email: dict, response: str) -> float | None:
    """1/0 for QA, fraction of key facts for summaries, None for reply drafts."""
    if task_kind == "qa":
        return float(check_fact(email["answer"], response))
    if task_kind == "summary":
        facts = email.get("facts") or []
        if not facts:
            return None
        return sum(check_fact(f, response) for f in facts) / len(facts)
    return None


# --------------------------------------------------------------------------- statistics
def wilson(k: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)
