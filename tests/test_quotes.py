import json
from datetime import datetime
from decimal import Decimal

import pytest

from calculadora3d.core.catalog import Catalog, Filament
from calculadora3d.core.pricing import (FilamentLine, FinishingTask,
                                        PriceTier, PricingInputs, PrinterCosts,
                                        compute_cost)
from calculadora3d.core.quotes import (build_snapshot, delete_quote,
                                       list_quotes, load_quote, save_quote,
                                       snapshot_project, snapshot_result)


@pytest.fixture
def cat(tmp_path):
    catalog = Catalog(tmp_path / "d.db")
    catalog.migrate()
    yield catalog
    catalog.close()


def _breakdown(roll_price="100"):
    return compute_cost(PricingInputs(
        filaments=(FilamentLine(Decimal("40"), Decimal(roll_price), Decimal("1000")),),
        seconds=3600, copies=1,
        printer=PrinterCosts(Decimal("4500"), Decimal("5000"), Decimal("120"),
                             Decimal("0.30")),
        kwh_price=Decimal("0.95"), failure_rate=Decimal("0.05"),
        labor_hourly=Decimal("25"), tasks=(FinishingTask("Lixar", 30),),
        extra_materials=Decimal("0"), packaging=Decimal("1.50")))


def _tiers(retail="30.00"):
    return [PriceTier("Varejo", Decimal("0.6"), Decimal(retail), Decimal(retail), None),
            PriceTier("Atacado", Decimal("0.2"), Decimal("20.00"), Decimal("2.00"), 10)]


def _snap(name="Peça", breakdown=None, tiers=None, **kw):
    return build_snapshot(
        name, "peca.3mf",
        [{"slot": 1, "color": "#FF0000", "type": "PLA", "grams": Decimal("40"),
          "filament_id": 3, "label": "Bambu PLA"}],
        [FinishingTask("Lixar", 30)], breakdown or _breakdown(),
        _tiers() if tiers is None else tiers, 1, 3600, **kw)


def test_snapshot_sobrevive_a_reajuste_de_preco(cat):
    brand = cat.add_brand("Bambu Lab")
    fid = cat.upsert_filament(Filament(None, brand, "Bambu Lab", "PLA", "PLA",
                                       Decimal("1000"), Decimal("100"), None, True))
    qid = save_quote(cat, _snap())
    cat.upsert_filament(Filament(fid, brand, "Bambu Lab", "PLA", "PLA",
                                 Decimal("1000"), Decimal("300"), None, True))
    assert Decimal(load_quote(cat, qid)["breakdown"]["material"]) == Decimal("4.00")


def test_list_quotes_mais_recente_primeiro(cat):
    a = save_quote(cat, _snap("A"))
    b = save_quote(cat, _snap("B"))
    c = save_quote(cat, _snap("C"))
    assert [q.id for q in list_quotes(cat)] == [c, b, a]
    resumo = list_quotes(cat)[0]
    assert resumo.name == "C" and isinstance(resumo.created_at, datetime)
    assert resumo.retail_price == Decimal("30.00")
    assert resumo.total_cost == Decimal(_snap()["breakdown"]["total"])


def test_snapshot_e_json_serializavel_com_decimal():
    snap = _snap(printer_id=2, extra_materials=Decimal("3.5"))
    assert json.loads(json.dumps(snap)) == snap
    assert snap["usage"][0]["grams"] == "40"
    assert snap["schema_version"] == 1
    assert snap["printer_id"] == 2 and snap["extra_materials"] == "3.5"
    assert snap["tasks"] == [{"name": "Lixar", "minutes": 30}]
    assert snap["tiers"][1]["min_quantity"] == 10


def test_snapshot_converte_decimal_aninhado_nas_linhas_de_uso():
    snap = build_snapshot("P", "", [{"x": [{"g": Decimal("1.5")}]}], [],
                          _breakdown(), [], 1, 0)
    assert snap["usage"] == [{"x": [{"g": "1.5"}]}]


def test_sem_faixas_preco_de_varejo_e_o_custo(cat):
    qid = save_quote(cat, _snap(tiers=[]))
    q, = list_quotes(cat)
    assert q.id == qid and q.retail_price == q.total_cost


def test_load_quote_inexistente_levanta_keyerror(cat):
    with pytest.raises(KeyError):
        load_quote(cat, 999)


def test_delete_quote_remove_e_ignora_inexistente(cat):
    qid = save_quote(cat, _snap())
    delete_quote(cat, 999)
    assert len(list_quotes(cat)) == 1
    delete_quote(cat, qid)
    assert list_quotes(cat) == []


def test_snapshot_result_reconstroi_os_valores_salvos():
    breakdown = _breakdown()
    snap = json.loads(json.dumps(_snap(breakdown=breakdown)))
    restored, tiers = snapshot_result(snap)
    assert restored == breakdown
    assert tiers == tuple(_tiers())
    assert all(isinstance(t.total, Decimal) for t in tiers)


def test_snapshot_project_monta_uma_placa_com_tempo_peso_e_copias():
    snap = build_snapshot(
        "Vaso", "a.3mf, b.3mf",
        [{"slot": 1, "color": "#FF0000FF", "type": "PLA", "grams": Decimal("40.5"),
          "filament_id": 3},
         {"slot": 4, "color": "#000000FF", "type": "PETG", "grams": Decimal("2.25"),
          "filament_id": 7}],
        [], _breakdown(), _tiers(), 3, 7200)
    project = snapshot_project(json.loads(json.dumps(snap)))
    assert project.name == "Vaso" and project.is_sliced
    assert project.total_seconds == 7200
    assert project.copies == 3
    assert project.total_grams == Decimal("42.75")
    assert [(u.slot, u.type, u.color, u.grams) for u in project.usage] == [
        (1, "PLA", "#FF0000FF", Decimal("40.5")),
        (4, "PETG", "#000000FF", Decimal("2.25"))]
    assert project.plates[0].weight_grams == Decimal("42.75")
