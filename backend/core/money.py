"""Exact INR money handling (T104 / F001-FR11).

Canonical storage and arithmetic use **integer paise**.  Floats are accepted
only at the legacy API edge and are converted through ``Decimal(str(x))`` so
that binary representation error cannot leak in.  Non-finite values, more than
two fractional digits (ambiguous rounding), and absurd magnitudes are rejected
instead of silently coerced.
"""
from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import Any, Optional

PAISE_PER_RUPEE = 100
# Rs 1,000 crore (10^13 paise).  Larger values are more likely a typo than a
# household figure; they are rejected rather than stored.
MAX_PAISE = 10 ** 13
_TWO_PLACES = Decimal("0.01")


class MoneyError(ValueError):
    """Invalid monetary input."""


def parse_rupees(value: Any, *, allow_negative: bool = False) -> Decimal:
    """Parse a user/API supplied rupee amount into an exact Decimal."""
    if isinstance(value, bool) or value is None:
        raise MoneyError("amount must be a number")
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise MoneyError("amount must be finite")
        dec = Decimal(repr(value))
    elif isinstance(value, Decimal):
        dec = value
    elif isinstance(value, int):
        dec = Decimal(value)
    elif isinstance(value, str):
        text = value.strip().replace(",", "")
        try:
            dec = Decimal(text)
        except InvalidOperation as exc:
            raise MoneyError("amount is not a valid number") from exc
    else:
        raise MoneyError("amount must be a number")

    if not dec.is_finite():
        raise MoneyError("amount must be finite")
    if dec.copy_abs() > MAX_PAISE:  # cheap bound first: quantize overflows on huge exponents
        raise MoneyError("amount exceeds the supported maximum")
    try:
        exact = dec == dec.quantize(_TWO_PLACES)
    except InvalidOperation as exc:
        raise MoneyError("amount is not a valid number") from exc
    if not exact:
        raise MoneyError("amount may have at most two decimal places")
    if dec < 0 and not allow_negative:
        raise MoneyError("amount must not be negative")
    if abs(dec) * PAISE_PER_RUPEE > MAX_PAISE:
        raise MoneyError("amount exceeds the supported maximum")
    return dec.quantize(_TWO_PLACES)


def rupees_to_paise(value: Any, *, allow_negative: bool = False) -> int:
    dec = parse_rupees(value, allow_negative=allow_negative)
    return int((dec * PAISE_PER_RUPEE).to_integral_value(rounding=ROUND_HALF_EVEN))


def paise_to_decimal(paise: Optional[int]) -> Optional[Decimal]:
    if paise is None:
        return None
    check_paise(paise)
    return (Decimal(int(paise)) / PAISE_PER_RUPEE).quantize(_TWO_PLACES)


def paise_to_float(paise: Optional[int]) -> Optional[float]:
    """Legacy display float.  Never feed this back into calculations."""
    dec = paise_to_decimal(paise)
    return None if dec is None else float(dec)


def check_paise(paise: Any) -> int:
    if isinstance(paise, bool) or not isinstance(paise, int):
        raise MoneyError("paise must be an integer")
    if abs(paise) > MAX_PAISE:
        raise MoneyError("paise amount exceeds the supported maximum")
    return paise


def format_inr(paise: Optional[int]) -> str:
    """Indian digit grouping, e.g. 1234567 paise-rupees -> Rs 12,345.67."""
    if paise is None:
        return "unavailable"
    sign = "-" if paise < 0 else ""
    rupees, rem = divmod(abs(int(paise)), PAISE_PER_RUPEE)
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"{sign}Rs {s}.{rem:02d}" if rem else f"{sign}Rs {s}"


def sum_paise(values) -> int:
    total = 0
    for v in values:
        total += check_paise(v)
    return check_paise(total)
