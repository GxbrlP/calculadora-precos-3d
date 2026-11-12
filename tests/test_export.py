from dataclasses import fields
from datetime import date
from decimal import Decimal

import pytest

from calculadora3d.core.catalog import CompanyInfo
from calculadora3d.core.export import (
    ClientQuote, PriceOption, QuoteItem, build_client_quote,
    missing_company_fields, price_options, quote_item,
)
from calculadora3d.core.pricing import CostBreakdown, FinishingTask, PriceTier
from calculadora3d.core.quotes import build_snapshot

EMPRESA = CompanyInfo(name="Borcelle", address="Rua Alegre, 123 - Cidade Brasileira")


def _snapshot(copies=2, name="Suporte"):
    breakdown = CostBreakdown(
        material=Decimal("4"), energy=Decimal("1"), failure=Decimal("0.5"),
        labor=Decimal("10"), extras=Decimal("1.5"), total=Decimal("17"))
    tiers = [
        PriceTier("Varejo", Decimal("0.6"), Decimal("30.00"), Decimal("15.00"), None),
        PriceTier("Atacado", Decimal("0.4"), Decimal("20.00"), Decimal("10.00"), 10),
        PriceTier("Mínimo", Decimal("0.2"), Decimal("12.00"), Decimal("6.00"), None),
    ]
    usage = [{"slot": 1, "color": "#FF0000", "type": "PLA", "grams": Decimal("40")}]
    return build_snapshot(name, "peca.3mf", usage, [FinishingTask("Lixar", 30)],
                          breakdown, tiers, copies, 3600)


def test_atacado_so_e_opcao_quando_a_quantidade_atinge_o_minimo():
    assert [o.name for o in price_options(_snapshot(copies=9))] == ["Varejo", "Mínimo"]
    assert [o.name for o in price_options(_snapshot(copies=10))] == [
        "Varejo", "Atacado", "Mínimo"]


def test_opcao_traz_unitario_e_total_da_faixa():
    varejo = price_options(_snapshot())[0]
    assert varejo == PriceOption("Varejo", Decimal("15.00"), Decimal("30.00"))


def test_item_usa_a_faixa_escolhida_e_a_quantidade_de_produtos():
    item = quote_item(_snapshot(copies=2), "Mínimo", "  Suporte de parede  ")
    assert item == QuoteItem("Suporte de parede", Decimal("6.00"), 2, Decimal("12.00"))


def test_item_recusa_faixa_indisponivel_e_descricao_vazia():
    with pytest.raises(ValueError, match="Atacado"):
        quote_item(_snapshot(copies=2), "Atacado", "Suporte")
    with pytest.raises(ValueError, match="descrição"):
        quote_item(_snapshot(), "Varejo", "   ")


def test_orcamento_soma_os_itens_e_formata_a_data_sem_horario():
    itens = (QuoteItem("A", Decimal("15.00"), 2, Decimal("30.00")),
             QuoteItem("B", Decimal("6.00"), 10, Decimal("60.00")))
    quote = build_client_quote(EMPRESA, 7, date(2026, 11, 12), itens)
    assert quote.total == Decimal("90.00")
    assert quote.date == "12/11/2026"
    assert quote.number == 7 and quote.items == itens


def test_orcamento_nao_carrega_custo_interno():
    nomes = {f.name for f in fields(ClientQuote)} | {f.name for f in fields(QuoteItem)}
    for proibido in ("cost", "margin", "breakdown", "tier", "failure", "labor"):
        assert not any(proibido in n for n in nomes)


def test_empresa_e_endereco_sao_obrigatorios():
    assert missing_company_fields(EMPRESA) == []
    assert missing_company_fields(CompanyInfo(name=" ", address="")) == [
        "nome da empresa", "endereço"]
    with pytest.raises(ValueError, match="nome da empresa"):
        build_client_quote(CompanyInfo(address="Rua"), 1, date(2026, 1, 1),
                           (QuoteItem("A", Decimal("1"), 1, Decimal("1")),))


def test_orcamento_precisa_de_pelo_menos_um_item():
    with pytest.raises(ValueError, match="produto"):
        build_client_quote(EMPRESA, 1, date(2026, 1, 1), ())
