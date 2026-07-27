from decimal import Decimal

TWO_PLACES = Decimal("0.01")


def to_money(value) -> Decimal:
    """Normalize any numeric input to a 2dp Decimal (NGN kobo precision)."""
    return Decimal(str(value)).quantize(TWO_PLACES)
