"""Integer minor-unit money. Store cents; format only on the way out.

Never let a float near a monetary value. ``Decimal`` in, integer cents out.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

DEFAULT_EXPONENT = 2


def to_minor_units(value: object, exponent: int = DEFAULT_EXPONENT) -> int | None:
    """``'50.00'`` / ``50`` / ``Decimal('50.00')`` -> ``5000``. Floats are stringified first."""
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    quantum = Decimal(1).scaleb(-exponent)  # 0.01
    return int(amount.quantize(quantum, rounding=ROUND_HALF_UP).scaleb(exponent))


def from_minor_units(minor: int | None, exponent: int = DEFAULT_EXPONENT) -> str:
    """``5000`` -> ``'50.00'``."""
    if minor is None:
        return ""
    amount = Decimal(minor).scaleb(-exponent)
    return f"{amount:,.{exponent}f}"
