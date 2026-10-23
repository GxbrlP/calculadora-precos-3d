from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class FilamentUsage:
    slot: int
    type: str
    color: str
    grams: Decimal
    meters: Decimal
    vendor: str | None
    settings_id: str | None
    density: Decimal | None = None
    cost_per_kg: Decimal | None = None


@dataclass(frozen=True)
class Plate:
    index: int
    seconds: int
    weight_grams: Decimal
    instances: int
    skipped: bool


@dataclass(frozen=True)
class SlicedProject:
    name: str
    source_path: Path
    printer_model: str | None
    plates: tuple[Plate, ...]
    usage: tuple[FilamentUsage, ...]
    is_sliced: bool
    warnings: tuple[str, ...]
    sources: tuple[Path, ...] = ()
    model_instances: int = 0
    unsliced_plates: tuple[int, ...] = ()

    @property
    def total_seconds(self) -> int:
        return sum(p.seconds for p in self.plates if not p.skipped)

    @property
    def total_hours(self) -> Decimal:
        return Decimal(self.total_seconds) / Decimal(3600)

    @property
    def total_grams(self) -> Decimal:
        return sum((u.grams for u in self.usage), Decimal(0))

    @property
    def color_count(self) -> int:
        if not self.is_sliced:
            return len(self.usage)
        return sum(1 for u in self.usage if u.grams > 0)

    @property
    def copies(self) -> int:
        if self.plates:
            count = sum(p.instances for p in self.plates if not p.skipped)
        else:
            count = self.model_instances
        return max(count, 1)
