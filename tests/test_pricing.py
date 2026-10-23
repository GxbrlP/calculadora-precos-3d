from decimal import Decimal

import pytest

from calculadora3d.core.pricing import (
    FilamentLine,
    FinishingTask,
    PricingError,
    PricingInputs,
    PrinterCosts,
    TierConfig,
    compute_cost,
    round_up_to,
    suggest_prices,
)


def _printer():
    return PrinterCosts(Decimal("3000"), Decimal("4000"),
                        Decimal("120"), Decimal("0.10"))


def _inputs(**overrides):
    values = dict(
        filaments=(FilamentLine(Decimal("25"), Decimal("120"), Decimal("1000")),),
        seconds=3600,
        copies=1,
        printer=_printer(),
        kwh_price=Decimal("0.95"),
        failure_rate=Decimal("0.05"),
        labor_hourly=Decimal("25"),
        tasks=(),
        extra_materials=Decimal("0"),
        packaging=Decimal("1.50"),
    )
    values.update(overrides)
    return PricingInputs(**values)


def test_material_usa_preco_por_rolo_e_peso_do_rolo():
    # rolo de 750 g a R$ 120 → R$ 0,16/g → 25 g = R$ 4,00
    c = compute_cost(_inputs(filaments=(FilamentLine(Decimal("25"),
                                                     Decimal("120"),
                                                     Decimal("750")),)))
    assert c.material == Decimal("4.00")


def test_material_soma_varias_cores():
    f = (FilamentLine(Decimal("10"), Decimal("100"), Decimal("1000")),
         FilamentLine(Decimal("20"), Decimal("150"), Decimal("500")))
    assert compute_cost(_inputs(filaments=f)).material == Decimal("7.00")


def test_custos_de_maquina_e_falha():
    # 2 h, 120 W, R$ 0,95/kWh → energia = 0,228
    # depreciação = 2 × (3000/4000 + 0,10) = 1,70
    c = compute_cost(_inputs(seconds=7200, failure_rate=Decimal("0.05")))
    assert c.energy == Decimal("0.228")
    assert c.depreciation == Decimal("1.70")
    assert c.failure == (c.material + c.energy + c.depreciation) * Decimal("0.05")


def test_mao_de_obra_soma_minutos_das_tarefas():
    tasks = (FinishingTask("lixar", 20), FinishingTask("pintar", 40))
    c = compute_cost(_inputs(tasks=tasks, labor_hourly=Decimal("25")))
    assert c.labor == Decimal("25.00")


def test_extras_somam_materiais_e_embalagem():
    c = compute_cost(_inputs(extra_materials=Decimal("2.00"),
                             packaging=Decimal("1.50")))
    assert c.extras == Decimal("3.50")


def test_total_e_a_soma_das_partes():
    c = compute_cost(_inputs())
    assert c.total == c.material + c.energy + c.depreciation + c.failure + c.labor + c.extras


def test_rolo_com_peso_zero_levanta_pricingerror():
    with pytest.raises(PricingError, match="peso do rolo"):
        compute_cost(_inputs(filaments=(FilamentLine(Decimal("10"), Decimal("100"), Decimal("0")),)))


def test_filamento_com_preco_zero_levanta_pricingerror():
    with pytest.raises(PricingError, match="preço"):
        compute_cost(_inputs(filaments=(FilamentLine(Decimal("10"), Decimal("0"), Decimal("1000")),)))


def test_vida_util_zero_levanta_pricingerror():
    printer = PrinterCosts(Decimal("3000"), Decimal("0"), Decimal("120"), Decimal("0.10"))
    with pytest.raises(PricingError, match="vida útil"):
        compute_cost(_inputs(printer=printer))


def test_tempo_zero_nao_gera_custo_de_maquina():
    c = compute_cost(_inputs(seconds=0))
    assert c.energy == Decimal("0") and c.depreciation == Decimal("0")


@pytest.mark.parametrize("overrides", [
    dict(seconds=-1),
    dict(failure_rate=Decimal("-0.01")),
    dict(failure_rate=Decimal("1")),
    dict(tasks=(FinishingTask("lixar", -5),)),
    dict(filaments=(FilamentLine(Decimal("-1"), Decimal("100"), Decimal("1000")),)),
])
def test_entradas_negativas_ou_fora_de_faixa_levantam_pricingerror(overrides):
    with pytest.raises(PricingError):
        compute_cost(_inputs(**overrides))


def test_preco_usa_margem_sobre_o_preco():
    # custo 40, margem 60% → 40 / 0,4 = 100
    t, = suggest_prices(Decimal("40"), [TierConfig("Varejo", Decimal("0.6"), None)],
                        copies=1, rounding_step=Decimal("0"))
    assert t.total == Decimal("100")


def test_preco_unitario_divide_pelas_copias():
    t, = suggest_prices(Decimal("40"), [TierConfig("Varejo", Decimal("0.6"), None)],
                        copies=4, rounding_step=Decimal("0"))
    assert t.unit == Decimal("25")


def test_copias_zero_tratadas_como_uma():
    t, = suggest_prices(Decimal("40"), [TierConfig("Varejo", Decimal("0.6"), None)],
                        copies=0, rounding_step=Decimal("0"))
    assert t.unit == t.total


def test_arredondamento_para_cima_no_passo():
    assert round_up_to(Decimal("100.10"), Decimal("0.50")) == Decimal("100.50")
    assert round_up_to(Decimal("100.50"), Decimal("0.50")) == Decimal("100.50")
    assert round_up_to(Decimal("100.10"), Decimal("0")) == Decimal("100.10")


def test_margem_de_cem_por_cento_ou_mais_levanta_pricingerror():
    for m in (Decimal("1"), Decimal("1.2")):
        with pytest.raises(PricingError, match="margem"):
            suggest_prices(Decimal("40"), [TierConfig("x", m, None)], 1, Decimal("0"))


def test_margem_negativa_levanta_pricingerror():
    with pytest.raises(PricingError, match="margem"):
        suggest_prices(Decimal("40"), [TierConfig("x", Decimal("-0.1"), None)], 1, Decimal("0"))


def test_passo_negativo_levanta_pricingerror():
    with pytest.raises(PricingError):
        round_up_to(Decimal("10"), Decimal("-0.50"))


def test_unitario_arredondado_e_total_e_unitario_vezes_copias():
    # custo 41 / 0,4 = 102,50; 3 cópias → 34,1666... → 34,50; total 3 × 34,50
    t, = suggest_prices(Decimal("41"), [TierConfig("Varejo", Decimal("0.6"), None)],
                        copies=3, rounding_step=Decimal("0.50"))
    assert t.unit == Decimal("34.50")
    assert t.total == Decimal("103.50")
    assert t.unit * 3 == t.total


def test_copias_zero_com_passo_arredondam_como_uma():
    t, = suggest_prices(Decimal("41"), [TierConfig("Varejo", Decimal("0.6"), None)],
                        copies=0, rounding_step=Decimal("0.50"))
    assert t.unit == t.total == Decimal("102.50")


def test_passo_zero_nao_arredonda_unitario_nem_total():
    t, = suggest_prices(Decimal("41"), [TierConfig("Varejo", Decimal("0.6"), None)],
                        copies=3, rounding_step=Decimal("0"))
    assert t.total == Decimal("102.5")
    assert t.unit == Decimal("102.5") / 3


def test_tres_faixas_saem_na_ordem_dada():
    tiers = suggest_prices(Decimal("40"), [
        TierConfig("Varejo", Decimal("0.6"), None),
        TierConfig("Atacado", Decimal("0.4"), 10),
        TierConfig("Mínimo", Decimal("0.2"), None),
    ], 1, Decimal("0.50"))
    assert [t.name for t in tiers] == ["Varejo", "Atacado", "Mínimo"]
    assert tiers[1].min_quantity == 10
