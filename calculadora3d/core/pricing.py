"""Custo de produção e faixas de preço: funções puras em Decimal."""
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

_ZERO = Decimal("0")


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class FilamentLine:
    grams: Decimal
    roll_price: Decimal
    roll_grams: Decimal


@dataclass(frozen=True)
class PrinterCosts:
    purchase_price: Decimal
    lifetime_hours: Decimal
    average_watts: Decimal
    maintenance_per_hour: Decimal


@dataclass(frozen=True)
class FinishingTask:
    name: str
    minutes: int


@dataclass(frozen=True)
class PricingInputs:
    filaments: tuple[FilamentLine, ...]
    seconds: int
    copies: int
    printer: PrinterCosts
    kwh_price: Decimal
    failure_rate: Decimal
    labor_hourly: Decimal
    tasks: tuple[FinishingTask, ...]
    extra_materials: Decimal
    packaging: Decimal


@dataclass(frozen=True)
class CostBreakdown:
    material: Decimal
    energy: Decimal
    depreciation: Decimal
    failure: Decimal
    labor: Decimal
    extras: Decimal
    total: Decimal


def _validate(inputs: PricingInputs) -> None:
    for line in inputs.filaments:
        if line.roll_grams <= _ZERO:
            raise PricingError("O peso do rolo deve ser maior que zero.")
        if line.roll_price <= _ZERO:
            raise PricingError("O preço do filamento deve ser maior que zero.")
        if line.grams < _ZERO:
            raise PricingError("A gramagem não pode ser negativa.")
    if inputs.seconds < 0:
        raise PricingError("O tempo de impressão não pode ser negativo.")
    if inputs.printer.lifetime_hours <= _ZERO:
        raise PricingError("A vida útil da impressora deve ser maior que zero.")
    if not _ZERO <= inputs.failure_rate < 1:
        raise PricingError("A taxa de falha deve estar entre 0 e 1 (exclusive).")
    if any(t.minutes < 0 for t in inputs.tasks):
        raise PricingError("Os minutos de uma tarefa não podem ser negativos.")


def compute_cost(inputs: PricingInputs) -> CostBreakdown:
    _validate(inputs)
    printer = inputs.printer
    hours = Decimal(inputs.seconds) / Decimal(3600)

    material = sum((f.grams * f.roll_price / f.roll_grams
                    for f in inputs.filaments), _ZERO)
    energy = hours * (printer.average_watts / Decimal(1000)) * inputs.kwh_price
    depreciation = hours * (printer.purchase_price / printer.lifetime_hours
                            + printer.maintenance_per_hour)
    machine_subtotal = material + energy + depreciation
    failure = machine_subtotal * inputs.failure_rate
    minutes = sum((t.minutes for t in inputs.tasks), 0)
    labor = Decimal(minutes) / Decimal(60) * inputs.labor_hourly
    extras = inputs.extra_materials + inputs.packaging
    total = machine_subtotal + failure + labor + extras
    return CostBreakdown(material, energy, depreciation, failure, labor, extras, total)


@dataclass(frozen=True)
class TierConfig:
    name: str
    margin: Decimal
    min_quantity: int | None


@dataclass(frozen=True)
class PriceTier:
    name: str
    margin: Decimal
    total: Decimal
    unit: Decimal
    min_quantity: int | None


def round_up_to(value: Decimal, step: Decimal) -> Decimal:
    """Arredonda para cima ao múltiplo de `step`; `step == 0` desliga."""
    if step < _ZERO:
        raise PricingError("O passo de arredondamento não pode ser negativo.")
    if step == _ZERO:
        return value
    return (value / step).to_integral_value(rounding=ROUND_CEILING) * step


def suggest_prices(total_cost: Decimal, tiers: Sequence[TierConfig],
                   copies: int, rounding_step: Decimal) -> tuple[PriceTier, ...]:
    """Preço = custo / (1 − margem); unitário arredondado e total = unitário × cópias."""
    copies = max(copies, 1)
    result = []
    for tier in tiers:
        if not _ZERO <= tier.margin < 1:
            raise PricingError(
                f"A margem da faixa '{tier.name}' deve estar entre 0 e 1 (exclusive).")
        price = total_cost / (1 - tier.margin)
        if rounding_step == _ZERO:
            total, unit = price, price / Decimal(copies)
        else:
            unit = round_up_to(price / Decimal(copies), rounding_step)
            total = unit * copies
        result.append(PriceTier(tier.name, tier.margin, total, unit, tier.min_quantity))
    return tuple(result)
