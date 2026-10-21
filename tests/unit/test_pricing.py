"""Unit tests for mqlab.pricing."""

import pytest

from mqlab.pricing import discounted_price


def test_discounted_price_rounds_down() -> None:
    """
    arrange: a price that does not divide evenly
    act: apply a 33 percent discount
    assert: the result is rounded down to whole cents
    """
    assert discounted_price(1000, 33) == 670


@pytest.mark.parametrize("percent", [-1, 101])
def test_discounted_price_rejects_out_of_range_percent(percent: int) -> None:
    """
    arrange: a percentage outside 0..100
    act: apply it
    assert: ValueError names the offending argument
    """
    with pytest.raises(ValueError, match="percent"):
        discounted_price(1000, percent)


def test_discounted_price_rejects_negative_price() -> None:
    """
    arrange: a negative price
    act: apply a discount
    assert: ValueError names the offending argument
    """
    with pytest.raises(ValueError, match="price_cents"):
        discounted_price(-1, 10)
