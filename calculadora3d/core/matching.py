import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from calculadora3d.core.catalog import Filament
from calculadora3d.core.models import FilamentUsage


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass(frozen=True)
class Match:
    filament: Filament | None
    confidence: Confidence


def _norm(text: str | None) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


def _clean_settings_id(settings_id: str | None) -> str:
    text = re.sub(r"\([^()]*\)\s*$", "", settings_id or "")
    return _norm(text.split("@", 1)[0])


def match_slot(usage: FilamentUsage, filaments: Sequence[Filament]) -> Match:
    vendor = _norm(usage.vendor)
    type_ = _norm(usage.type)
    settings = _clean_settings_id(usage.settings_id)
    same_brand = [f for f in filaments
                  if vendor and _norm(f.brand_name) == vendor]

    by_line = [f for f in same_brand
               if _norm(f.line) and _norm(f.line) in settings]
    if by_line:
        longest = max(len(_norm(f.line)) for f in by_line)
        top = [f for f in by_line if len(_norm(f.line)) == longest]
        if len(top) == 1:
            return Match(top[0], Confidence.HIGH)

    by_type = [f for f in same_brand if _norm(f.type) == type_]
    if len(by_type) == 1:
        return Match(by_type[0], Confidence.MEDIUM)

    only_type = [f for f in filaments if _norm(f.type) == type_]
    if len(only_type) == 1:
        return Match(only_type[0], Confidence.LOW)

    return Match(None, Confidence.NONE)
