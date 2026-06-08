"""
Grounding / faithfulness metrics for the manager insights agent.

The insights agent must answer ONLY from the sales report + menu prices it is
given; it must not invent figures. These helpers measure how well a response's
numbers are supported by the data the agent actually had.
"""

import re
from typing import Iterable, List, Set


def extract_numbers(text: str) -> List[float]:
    """
    Pull numeric values out of free text. Handles both '35.31' and Romanian
    '35,31' decimals. Pure integers and decimals are returned as floats.
    """
    if not text:
        return []
    nums: List[float] = []
    for raw in re.findall(r"\d+(?:[.,]\d+)?", text):
        try:
            nums.append(float(raw.replace(",", ".")))
        except ValueError:
            continue
    return nums


def _is_supported(value: float, allowed: Iterable[float], tol: float = 0.5) -> bool:
    """A number is supported if it (approximately) matches any allowed figure."""
    return any(abs(value - a) <= tol for a in allowed)


def unsupported_numbers(text: str, allowed: Iterable[float], tol: float = 0.5) -> List[float]:
    """Return the numbers in `text` that are NOT backed by any allowed figure."""
    allowed = list(allowed)
    return [n for n in extract_numbers(text) if not _is_supported(n, allowed, tol)]


def grounding_score(text: str, allowed: Iterable[float], tol: float = 0.5) -> float:
    """
    Fraction of numbers in `text` that are supported by `allowed` (1.0 if the
    text contains no numbers at all — nothing to hallucinate).
    """
    nums = extract_numbers(text)
    if not nums:
        return 1.0
    allowed = list(allowed)
    supported = sum(1 for n in nums if _is_supported(n, allowed, tol))
    return supported / len(nums)


def report_numbers(report: dict) -> Set[float]:
    """Collect every figure the agent is allowed to cite from a range report."""
    allowed: Set[float] = set()
    for key in ("total_revenue", "total_orders", "average_order_value"):
        val = report.get(key)
        if isinstance(val, (int, float)):
            allowed.add(float(val))
    for t in report.get("top_items", []):
        q = t.get("quantity_sold")
        if isinstance(q, (int, float)):
            allowed.add(float(q))
    for d in report.get("revenue_by_day", []):
        r = d.get("revenue")
        if isinstance(r, (int, float)):
            allowed.add(float(r))
    return allowed


def is_discount_of(suggested: float, base: float, min_pct: float = 0.05, max_pct: float = 0.40) -> bool:
    """
    True if `suggested` is a plausible discounted price of `base` — i.e. a
    reduction between min_pct and max_pct. Used to check happy-hour suggestions
    are derived from the real menu price, not invented.
    """
    if base <= 0:
        return False
    lowest = base * (1 - max_pct)
    highest = base * (1 - min_pct)
    return lowest - 1e-6 <= suggested <= highest + 1e-6
