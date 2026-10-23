"""Orçamento para o cliente: peças, quantidade, acabamento, prazo e preço.

Nunca expõe a decomposição de custo nem a faixa de preço mínimo.
"""
from datetime import datetime
from decimal import Decimal
from html import escape

from calculadora3d.core.formatting import brl, date_time, duration

HIDDEN_TIER = "mínimo"


def _lead_seconds(snapshot: dict) -> int:
    minutes = sum(int(t.get("minutes", 0)) for t in snapshot.get("tasks", []))
    return int(snapshot["seconds"]) + minutes * 60


def _prices(snapshot: dict) -> list[tuple[str, str]]:
    """Linhas (rótulo, valor) de preço: varejo primeiro, depois atacado."""
    tiers = snapshot.get("tiers", [])
    rows: list[tuple[str, str]] = []
    for index, tier in enumerate(tiers):
        name = str(tier["name"])
        if index > 0 and name.casefold() == HIDDEN_TIER:
            continue
        unit = brl(Decimal(str(tier["unit"])))
        if index == 0:
            rows.append((f"{name} (unitário)", unit))
            rows.append((f"{name} (total)", brl(Decimal(str(tier["total"])))))
        else:
            minimum = tier.get("min_quantity")
            suffix = f" (a partir de {minimum} un.)" if minimum else ""
            rows.append((f"{name}{suffix}", unit))
    return rows


def _fields(snapshot: dict) -> list[tuple[str, str]]:
    created = datetime.fromisoformat(snapshot["created_at"])
    finishing = ", ".join(t["name"] for t in snapshot.get("tasks", [])) or "—"
    return [
        ("Projeto", str(snapshot["project_name"])),
        ("Data", date_time(created)),
        ("Quantidade", str(snapshot["copies"])),
        ("Acabamento", finishing),
        ("Prazo de produção estimado", duration(_lead_seconds(snapshot))),
    ]


def quote_to_text(snapshot: dict) -> str:
    lines = ["ORÇAMENTO", ""]
    lines += [f"{label}: {value}" for label, value in _fields(snapshot)]
    lines += ["", "Preços"]
    lines += [f"{label}: {value}" for label, value in _prices(snapshot)]
    return "\n".join(lines) + "\n"


def quote_to_html(snapshot: dict) -> str:
    def rows(items):
        return "".join(
            f"<tr><td>{escape(label)}</td><td align='right'><b>{escape(value)}</b></td></tr>"
            for label, value in items)

    return (
        "<html><head><meta charset='utf-8'></head>"
        "<body style='font-family: sans-serif; font-size: 11pt;'>"
        "<h1>Orçamento</h1>"
        f"<table cellspacing='0' cellpadding='6'>{rows(_fields(snapshot))}</table>"
        "<h2>Preços</h2>"
        f"<table cellspacing='0' cellpadding='6'>{rows(_prices(snapshot))}</table>"
        "</body></html>")
