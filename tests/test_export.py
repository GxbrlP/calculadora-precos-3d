from decimal import Decimal

from calculadora3d.core.export import quote_to_html, quote_to_text
from calculadora3d.core.pricing import CostBreakdown, FinishingTask, PriceTier
from calculadora3d.core.quotes import build_snapshot


def _snapshot(retail="30.00", name="Suporte", tasks=None, copies=2):
    tasks = [FinishingTask("Lixar", 30), FinishingTask("Pintar", 15)] if tasks is None else tasks
    breakdown = CostBreakdown(
        material=Decimal("4"), energy=Decimal("1"), depreciation=Decimal("2"),
        failure=Decimal("0.5"), labor=Decimal("10"), extras=Decimal("1.5"),
        total=Decimal("19"))
    tiers = [
        PriceTier("Varejo", Decimal("0.6"), Decimal(retail), Decimal(retail) / 2, None),
        PriceTier("Atacado", Decimal("0.4"), Decimal("200.00"), Decimal("20.00"), 10),
        PriceTier("Mínimo", Decimal("0.2"), Decimal("12.00"), Decimal("6.00"), None),
    ]
    usage = [{"slot": 1, "color": "#FF0000", "type": "PLA", "grams": Decimal("40")}]
    return build_snapshot(name, "peca.3mf", usage, tasks, breakdown, tiers,
                          copies, 3600)


def test_html_mostra_o_preco_de_varejo_formatado():
    html = quote_to_html(_snapshot(retail="100.5"))
    assert "R$ 100,50" in html


def test_html_nao_expoe_custo_interno_ao_cliente():
    for saida in (quote_to_html(_snapshot()), quote_to_text(_snapshot())):
        for palavra in ("depreciação", "falha", "custo", "margem"):
            assert palavra not in saida.lower()


def test_minimo_nunca_aparece():
    for saida in (quote_to_html(_snapshot()), quote_to_text(_snapshot())):
        assert "mínimo" not in saida.lower()
        assert "R$ 12,00" not in saida
        assert "R$ 6,00" not in saida


def test_texto_lista_as_pecas_e_o_prazo():
    texto = quote_to_text(_snapshot())
    assert "Projeto: Suporte" in texto
    assert "Quantidade: 2" in texto
    assert "Acabamento: Lixar, Pintar" in texto
    # 3600 s de impressão + 45 min de acabamento
    assert "Prazo de produção estimado: 1h 45min" in texto
    assert "Varejo (unitário): R$ 15,00" in texto
    assert "Varejo (total): R$ 30,00" in texto
    assert "Atacado (a partir de 10 un.): R$ 20,00" in texto
    assert "30min" not in texto and "15min" not in texto


def test_html_escapa_textos_do_usuario():
    snap = _snapshot(name="<b>x</b>", tasks=[FinishingTask("<i>y</i>", 5)])
    html = quote_to_html(snap)
    assert "<b>x</b>" not in html and "&lt;b&gt;x&lt;/b&gt;" in html
    assert "<i>y</i>" not in html and "&lt;i&gt;y&lt;/i&gt;" in html
