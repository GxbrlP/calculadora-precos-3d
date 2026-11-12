"""Orçamento para o cliente: empresa, produtos e um preço por produto.

Só carrega o que vai impresso: descrição, preço unitário da faixa escolhida,
quantidade e totais. Custos, margens e nomes de faixa nunca entram.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from calculadora3d.core.catalog import CompanyInfo
from calculadora3d.core.formatting import date_br

_REQUIRED_COMPANY = (("name", "nome da empresa"), ("address", "endereço"))


@dataclass(frozen=True)
class PriceOption:
    """Uma faixa de preço que pode ser apresentada ao cliente."""
    name: str
    unit: Decimal
    total: Decimal


@dataclass(frozen=True)
class QuoteItem:
    description: str
    unit: Decimal
    quantity: int
    total: Decimal


@dataclass(frozen=True)
class ClientQuote:
    company: CompanyInfo
    number: int
    date: str
    items: tuple[QuoteItem, ...]
    total: Decimal


def price_options(snapshot: dict) -> tuple[PriceOption, ...]:
    """Faixas do orçamento salvo; uma faixa com quantidade mínima só entra se atingida."""
    quantity = int(snapshot["copies"])
    options = []
    for tier in snapshot.get("tiers", []):
        minimum = tier.get("min_quantity")
        if minimum is not None and quantity < int(minimum):
            continue
        options.append(PriceOption(str(tier["name"]), Decimal(str(tier["unit"])),
                                   Decimal(str(tier["total"]))))
    return tuple(options)


def quote_item(snapshot: dict, tier_name: str, description: str) -> QuoteItem:
    description = description.strip()
    if not description:
        raise ValueError("Informe a descrição do produto.")
    option = next((o for o in price_options(snapshot) if o.name == tier_name), None)
    if option is None:
        raise ValueError(f"A faixa {tier_name} não está disponível para este produto.")
    return QuoteItem(description, option.unit, int(snapshot["copies"]), option.total)


def missing_company_fields(company: CompanyInfo) -> list[str]:
    return [label for attr, label in _REQUIRED_COMPANY
            if not getattr(company, attr).strip()]


def build_client_quote(company: CompanyInfo, number: int, when: date,
                       items: Sequence[QuoteItem]) -> ClientQuote:
    missing = missing_company_fields(company)
    if missing:
        raise ValueError("Configure em Configurações: " + ", ".join(missing) + ".")
    if not items:
        raise ValueError("O orçamento precisa de pelo menos um produto.")
    total = sum((item.total for item in items), Decimal(0))
    return ClientQuote(company, number, date_br(when), tuple(items), total)
