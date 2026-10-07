"""Money helpers: integer minor units, no float drift."""

from decimal import Decimal

import pytest

from docextract.money import from_minor_units, to_minor_units


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("50.00", 5000),
        ("50", 5000),
        (50, 5000),
        (Decimal("50.00"), 5000),
        ("49.995", 5000),        # half-up rounding
        ("0.005", 1),            # half-up rounding
        ("1,063.15", 106315),    # thousands separator tolerated
        ("39,460.00", 3946000),
        (4.47, 447),             # floats are stringified, not float-multiplied
        ("0.00", 0),
        ("—", None),             # em dash the prototype uses for "no value"
        ("", None),
        (None, None),
        ("not-a-number", None),
    ],
)
def test_to_minor_units(value, expected):
    assert to_minor_units(value) == expected


def test_no_float_drift():
    # the exact failure this exists to prevent
    assert to_minor_units("0.10") + to_minor_units("0.20") == to_minor_units("0.30")
    assert to_minor_units(50.0) == 5000


@pytest.mark.parametrize(
    ("minor", "expected"),
    [
        (5000, "50.00"),
        (3946000, "39,460.00"),
        (6337098, "63,370.98"),
        (0, "0.00"),
        (None, ""),
    ],
)
def test_from_minor_units(minor, expected):
    assert from_minor_units(minor) == expected


def test_round_trip_is_stable():
    for raw in ("50.00", "39,460.00", "0.00", "1,063.15"):
        minor = to_minor_units(raw)
        assert to_minor_units(from_minor_units(minor)) == minor
