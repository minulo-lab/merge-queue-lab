"""Unit tests for mqlab.basket_s3."""

from mqlab.basket_s3 import basket_total


def test_basket_total_applies_discount_to_each_item() -> None:
    """
    arrange: two prices
    act: total them with 10 percent off
    assert: each item is discounted, then summed
    """
    assert basket_total([1000, 500], 10) == 1350
