"""Histórico de orçamentos: snapshots JSON imunes a reajustes do catálogo."""
import json
from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from calculadora3d.core.catalog import Catalog
from calculadora3d.core.models import FilamentUsage, Plate, SlicedProject
from calculadora3d.core.pricing import CostBreakdown, FinishingTask, PriceTier

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class QuoteSummary:
    id: int
    name: str
    created_at: datetime
    total_cost: Decimal
    retail_price: Decimal


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def build_snapshot(project_name: str, source_file: str,
                   usage_rows: Sequence[dict], tasks: Sequence[FinishingTask],
                   breakdown: CostBreakdown, tiers: Sequence[PriceTier],
                   copies: int, seconds: int, *,
                   printer_id: int | None = None,
                   extra_materials: Decimal = Decimal("0")) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "source_file": source_file,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "copies": copies,
        "seconds": seconds,
        "usage": [_jsonable(row) for row in usage_rows],
        "tasks": [{"name": t.name, "minutes": t.minutes} for t in tasks],
        "breakdown": {
            "material": str(breakdown.material),
            "energy": str(breakdown.energy),
            "failure": str(breakdown.failure),
            "labor": str(breakdown.labor),
            "extras": str(breakdown.extras),
            "total": str(breakdown.total),
        },
        "tiers": [{"name": t.name, "margin": str(t.margin),
                   "total": str(t.total), "unit": str(t.unit),
                   "min_quantity": t.min_quantity} for t in tiers],
        "printer_id": printer_id,
        "extra_materials": str(extra_materials),
    }


def snapshot_result(snapshot: dict) -> tuple[CostBreakdown, tuple[PriceTier, ...]]:
    """Custos e faixas exatamente como foram salvos, sem recalcular.

    Snapshots antigos podem trazer a chave "depreciation", que não existe mais;
    ela é ignorada e o total salvo é mantido.
    """
    saved = snapshot["breakdown"]
    breakdown = CostBreakdown(**{f.name: Decimal(str(saved[f.name]))
                                 for f in fields(CostBreakdown)})
    tiers = tuple(PriceTier(t["name"], Decimal(str(t["margin"])),
                            Decimal(str(t["total"])), Decimal(str(t["unit"])),
                            t["min_quantity"]) for t in snapshot["tiers"])
    return breakdown, tiers


def snapshot_project(snapshot: dict) -> SlicedProject:
    """Projeto de uma placa com o tempo, as gramas e as cópias do orçamento salvo."""
    usage = tuple(
        FilamentUsage(slot=int(row["slot"]), type=row.get("type") or "",
                      color=row.get("color") or "",
                      grams=Decimal(str(row.get("grams", "0"))),
                      meters=Decimal(0), vendor=None, settings_id=None)
        for row in snapshot["usage"])
    total = sum((u.grams for u in usage), Decimal(0))
    plate = Plate(1, int(snapshot["seconds"]), total, int(snapshot["copies"]), False)
    name = snapshot["project_name"]
    return SlicedProject(name=name, source_path=Path(name), printer_model=None,
                         plates=(plate,), usage=usage, is_sliced=True, warnings=())


def save_quote(catalog: Catalog, snapshot: dict) -> int:
    total_cost = snapshot["breakdown"]["total"]
    tiers = snapshot["tiers"]
    retail_price = tiers[0]["total"] if tiers else total_cost
    with catalog.connection:
        cursor = catalog.connection.execute(
            "INSERT INTO quotes (name, created_at, source_file, total_cost,"
            " retail_price, snapshot_json) VALUES (?, ?, ?, ?, ?, ?)",
            (snapshot["project_name"], snapshot["created_at"],
             snapshot["source_file"], total_cost, retail_price,
             json.dumps(snapshot, ensure_ascii=False)))
    return cursor.lastrowid


def list_quotes(catalog: Catalog) -> list[QuoteSummary]:
    rows = catalog.connection.execute(
        "SELECT id, name, created_at, total_cost, retail_price FROM quotes"
        " ORDER BY created_at DESC, id DESC")
    return [QuoteSummary(r["id"], r["name"],
                         datetime.fromisoformat(r["created_at"]),
                         Decimal(r["total_cost"]), Decimal(r["retail_price"]))
            for r in rows]


def load_quote(catalog: Catalog, quote_id: int) -> dict:
    row = catalog.connection.execute(
        "SELECT snapshot_json FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    if row is None:
        raise KeyError(quote_id)
    return json.loads(row["snapshot_json"])


def delete_quote(catalog: Catalog, quote_id: int) -> None:
    with catalog.connection:
        catalog.connection.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
