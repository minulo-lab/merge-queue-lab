"""Basket totals (added by scenario s0)."""

from mqlab.pricing import apply_discount


def basket_total(prices_cents: list[int], percent: int) -> int:
    """Total of all prices after the same discount."""
    return sum(apply_discount(p, percent) for p in prices_cents)
