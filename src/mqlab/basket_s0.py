"""Basket totals (added by scenario s0)."""

from mqlab.pricing import discounted_price


def basket_total(prices_cents: list[int], percent: int) -> int:
    """Total of all prices after the same discount."""
    return sum(discounted_price(p, percent) for p in prices_cents)
