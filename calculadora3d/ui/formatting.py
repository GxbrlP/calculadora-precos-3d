"""Formatação pt-BR manual (sem locale, sem Qt)."""
import re
from decimal import Decimal, InvalidOperation

from calculadora3d.core.formatting import brl, date_time, duration, grams  # noqa: F401

_THOUSANDS = re.compile(r"[1-9]\d{0,2}(\.\d{3})+")


def parse_decimal(text: str) -> Decimal:
    """Lê "1.234,56" ou "12.5" como Decimal; levanta ValueError se inválido ou negativo."""
    raw = text.strip().replace("R$", "").replace("g", "").strip()
    if "," in raw or _THOUSANDS.fullmatch(raw):
        raw = raw.replace(".", "").replace(",", ".")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"Valor inválido: {text!r}") from None
    if not value.is_finite() or value < 0:
        raise ValueError(f"Valor inválido: {text!r}")
    return value
