"""Histórico de orçamentos: snapshots JSON imunes a reajustes do catálogo."""
import base64
import binascii
import json
from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from calculadora3d.core.catalog import Catalog
from calculadora3d.core.export import price_options
from calculadora3d.core.models import FilamentUsage, Plate, PlateThumbnail, SlicedProject
from calculadora3d.core.pricing import CostBreakdown, FinishingTask, PriceTier
from calculadora3d.core.threemf import PNG_SIGNATURE

SCHEMA_VERSION = 2


@dataclass(frozen=True)
class QuoteSummary:
    id: int
    name: str
    created_at: datetime
    total_cost: Decimal
    retail_price: Decimal


@dataclass(frozen=True)
class OrderTotals:
    """Totais do pedido; uma faixa é None se algum produto não pode usá-la."""
    quantity: int
    cost: Decimal
    tiers: dict[str, Decimal | None]


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def build_product(project_name: str, source_file: str,
                  usage_rows: Sequence[dict], tasks: Sequence[FinishingTask],
                  breakdown: CostBreakdown, tiers: Sequence[PriceTier],
                  copies: int, seconds: int, *,
                  printer_id: int | None = None,
                  extra_materials: Decimal = Decimal("0"),
                  thumbnails: Sequence[PlateThumbnail] = ()) -> dict:
    """Um produto (um arquivo) do pedido, com os valores do momento do cálculo."""
    return {
        "project_name": project_name,
        "source_file": source_file,
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
        "thumbnails": [{"plate": t.plate, "unsliced": t.unsliced,
                        "png": base64.b64encode(t.png).decode("ascii")}
                       for t in thumbnails],
    }


def _thumbnail(entry) -> PlateThumbnail | None:
    if not isinstance(entry, dict):
        return None
    plate, encoded = entry.get("plate"), entry.get("png")
    if not isinstance(plate, int) or isinstance(plate, bool) or not isinstance(encoded, str):
        return None
    try:
        png = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not png.startswith(PNG_SIGNATURE):
        return None
    return PlateThumbnail(plate, png, bool(entry.get("unsliced", False)))


def snapshot_thumbnails(snapshot: dict) -> tuple[PlateThumbnail, ...]:
    """Miniaturas salvas no produto; orçamento antigo ou entrada estragada fica sem imagem."""
    entries = snapshot.get("thumbnails")
    if not isinstance(entries, list):
        return ()
    found = (_thumbnail(entry) for entry in entries)
    return tuple(t for t in found if t is not None)


def build_order(name: str, products: Sequence[dict]) -> dict:
    """Snapshot v2: um orçamento com N produtos."""
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "products": list(products),
    }


def normalize_order(snapshot: dict) -> dict:
    """v2 volta como está; um snapshot v1 (um produto só) vira pedido de 1 produto."""
    if "products" in snapshot:
        return snapshot
    product = {k: v for k, v in snapshot.items()
               if k not in ("schema_version", "created_at")}
    return {"schema_version": SCHEMA_VERSION, "name": snapshot["project_name"],
            "created_at": snapshot["created_at"], "products": [product]}


def order_products(snapshot: dict) -> list[dict]:
    return normalize_order(snapshot)["products"]


def order_totals(products: Sequence[dict]) -> OrderTotals:
    """Somas do pedido; as faixas seguem a ordem das do primeiro produto."""
    if not products:
        return OrderTotals(0, Decimal(0), {})
    quantity = sum(int(p["copies"]) for p in products)
    cost = sum((Decimal(str(p["breakdown"]["total"])) for p in products), Decimal(0))
    available = [{o.name: o.total for o in price_options(p)} for p in products]
    tiers: dict[str, Decimal | None] = {}
    for tier in products[0].get("tiers", []):
        name = str(tier["name"])
        if all(name in options for options in available):
            tiers[name] = sum((options[name] for options in available), Decimal(0))
        else:
            tiers[name] = None
    return OrderTotals(quantity, cost, tiers)


def snapshot_result(snapshot: dict) -> tuple[CostBreakdown, tuple[PriceTier, ...]]:
    """Custos e faixas de um produto exatamente como foram salvos, sem recalcular.

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
    """Projeto de uma placa com o tempo, as gramas e as cópias de um produto salvo."""
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
                         plates=(plate,), usage=usage, is_sliced=True, warnings=(),
                         thumbnails=snapshot_thumbnails(snapshot))


def save_quote(catalog: Catalog, order: dict) -> int:
    order = normalize_order(order)
    products = order["products"]
    source_file = ", ".join(p["source_file"] for p in products if p["source_file"])
    total_cost = Decimal(0)
    retail_price = Decimal(0)
    for product in products:
        cost = Decimal(str(product["breakdown"]["total"]))
        tiers = product["tiers"]
        total_cost += cost
        retail_price += Decimal(str(tiers[0]["total"])) if tiers else cost
    with catalog.connection:
        cursor = catalog.connection.execute(
            "INSERT INTO quotes (name, created_at, source_file, total_cost,"
            " retail_price, snapshot_json) VALUES (?, ?, ?, ?, ?, ?)",
            (order["name"], order["created_at"], source_file, str(total_cost),
             str(retail_price), json.dumps(order, ensure_ascii=False)))
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
    return normalize_order(json.loads(row["snapshot_json"]))


def delete_quote(catalog: Catalog, quote_id: int) -> None:
    with catalog.connection:
        catalog.connection.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
