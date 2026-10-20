"""Price helpers used by the lab scenarios.

Scenario "semantic conflict" renames `apply_discount` in one pull request while a
second pull request adds a new caller of the old name. Each pull request is green
on its own; only the combination is broken. See docs/scenarios.md.
"""


def apply_discount(price_cents: int, percent: int) -> int:
    """Return the price after a percentage discount, rounded down to whole cents.

    Args:
        price_cents: price in cents, must be non-negative.
        percent: discount in percent, 0 to 100 inclusive.

    Raises:
        ValueError: if an argument is out of range.
    """
    if price_cents < 0:
        raise ValueError("price_cents must be non-negative")
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return price_cents * (100 - percent) // 100
