"""Formatação pt-BR de exibição (sem locale, sem Qt)."""
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal


def _number(value: Decimal) -> tuple[str, bool]:
    q = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole, frac = f"{abs(q):.2f}".split(".")
    groups = f"{int(whole):,}".replace(",", ".")
    return f"{groups},{frac}", q < 0


def brl(value: Decimal) -> str:
    text, negative = _number(value)
    return f"{'-' if negative else ''}R$ {text}"


def grams(value: Decimal) -> str:
    text, negative = _number(value)
    return f"{'-' if negative else ''}{text} g"


def duration(seconds: int) -> str:
    minutes_total = int(seconds) // 60
    hours, minutes = divmod(minutes_total, 60)
    if hours:
        return f"{hours}h {minutes:02d}min"
    return f"{minutes}min"


def date_time(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M")
