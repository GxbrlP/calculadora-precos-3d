import sys
from pathlib import Path

import pytest

from decimal import Decimal

from calculadora3d.core.catalog import (Brand, Catalog, Filament, Printer,
                                        Settings, TaskPreset, printer_for_model)
from calculadora3d.core.pricing import FilamentLine, PrinterCosts
from calculadora3d.core.paths import data_dir, db_path


@pytest.fixture
def cat(tmp_path):
    catalog = Catalog(tmp_path / "d.db")
    catalog.migrate()
    yield catalog
    catalog.close()


def test_migrate_cria_as_tabelas(cat):
    cat.migrate()
    nomes = {r[0] for r in cat.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"brands", "filaments", "printers", "settings",
            "task_presets", "quotes"} <= nomes


def test_migrate_e_idempotente(cat):
    cat.migrate()
    cat.migrate()


def test_chave_estrangeira_ativa_e_respeitada(cat):
    import sqlite3
    cat.migrate()
    assert cat.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        cat.connection.execute(
            "INSERT INTO filaments (brand_id, line, type, roll_grams,"
            " roll_price, density, active) VALUES (999, 'x', 'PLA', '1000',"
            " '100', '1.24', 1)")


def test_data_dir_respeita_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert data_dir() == tmp_path / "Calculadora3D"
    assert (tmp_path / "Calculadora3D").is_dir()


def test_data_dir_respeita_xdg_no_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert data_dir() == tmp_path / "calculadora3d"
    assert (tmp_path / "calculadora3d").is_dir()


def test_data_dir_linux_padrao_usa_local_share(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert data_dir() == tmp_path / ".local" / "share" / "calculadora3d"


def test_db_path_e_dados_db(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert db_path() == tmp_path / "calculadora3d" / "dados.db"


def _filamento(brand_id, brand_name="Bambu Lab", line="PLA Basic", grams="1000",
               price="149.90", active=True, fid=None):
    return Filament(fid, brand_id, brand_name, line, "PLA", Decimal(grams),
                    Decimal(price), None, active)


def _impressora(model_id="Bambu Lab A1", pid=None):
    return Printer(pid, "A1", model_id, Decimal("120"))


def test_filamento_ida_e_volta_preserva_decimal(cat):
    b = cat.add_brand("Bambu Lab")
    cat.upsert_filament(_filamento(b))
    f, = cat.list_filaments()
    assert f.roll_price == Decimal("149.90") and f.price_per_kg == Decimal("149.90")
    assert f.density is None and f.active is True


def test_price_per_kg_com_rolo_de_750g():
    f = _filamento(1, grams="750", price="120")
    assert f.price_per_kg == Decimal("160.00")


def test_price_per_kg_com_rolo_zerado_nao_levanta():
    assert _filamento(1, grams="0").price_per_kg == Decimal("0")


def test_list_filaments_traz_o_nome_da_marca(cat):
    a = cat.add_brand("Voolt")
    b = cat.add_brand("Bambu Lab")
    cat.upsert_filament(_filamento(a, line="PLA"))
    cat.upsert_filament(_filamento(b, line="PETG"))
    cat.upsert_filament(_filamento(b, line="ABS"))
    assert [(f.brand_name, f.line) for f in cat.list_filaments()] == [
        ("Bambu Lab", "ABS"), ("Bambu Lab", "PETG"), ("Voolt", "PLA")]
    assert [x.name for x in cat.list_brands()] == ["Bambu Lab", "Voolt"]


def test_active_only_filtra_inativos(cat):
    b = cat.add_brand("Bambu Lab")
    cat.upsert_filament(_filamento(b, line="Ativo"))
    cat.upsert_filament(_filamento(b, line="Inativo", active=False))
    assert [f.line for f in cat.list_filaments()] == ["Ativo"]
    assert len(cat.list_filaments(active_only=False)) == 2


def test_find_printer_by_model_casa_sem_diferenciar_caixa(cat):
    pid = cat.upsert_printer(_impressora("Bambu Lab A1"))
    assert cat.find_printer_by_model("  bambu lab a1 ").id == pid
    assert cat.find_printer_by_model("Bambu Lab P1S") is None


def test_get_settings_devolve_os_padroes_em_banco_novo(cat):
    s = cat.get_settings()
    assert s.retail_margin == Decimal("0.6") and s.kwh_price == Decimal("0.95")
    assert s == Settings(Decimal("0.95"), Decimal("0.05"), Decimal("25.00"),
                         Decimal("1.50"), Decimal("0.6"), Decimal("0.4"), 10,
                         Decimal("0.2"), Decimal("0.50"))


def test_get_settings_completa_chave_ausente_com_o_padrao(cat):
    cat.connection.execute("INSERT INTO settings VALUES ('kwh_price', '1.10')")
    s = cat.get_settings()
    assert s.kwh_price == Decimal("1.10") and s.packaging == Decimal("1.50")


def test_save_settings_sobrescreve_e_persiste(tmp_path):
    c = Catalog(tmp_path / "x.db")
    c.migrate()
    novo = Settings(Decimal("1.20"), Decimal("0.10"), Decimal("30"),
                    Decimal("2"), Decimal("0.5"), Decimal("0.3"), 5,
                    Decimal("0.15"), Decimal("1"))
    c.save_settings(novo)
    c.save_settings(novo)
    c.close()
    c2 = Catalog(tmp_path / "x.db")
    assert c2.get_settings() == novo
    c2.close()


def test_save_settings_rejeita_valores_invalidos(cat):
    base = cat.get_settings()
    from dataclasses import replace
    for ruim in (replace(base, retail_margin=Decimal("1")),
                 replace(base, wholesale_margin=Decimal("-0.1")),
                 replace(base, minimum_margin=Decimal("1.5")),
                 replace(base, failure_rate=Decimal("1")),
                 replace(base, kwh_price=Decimal("-1")),
                 replace(base, packaging=Decimal("-0.01")),
                 replace(base, rounding_step=Decimal("-0.5")),
                 replace(base, wholesale_min_quantity=-1)):
        with pytest.raises(ValueError):
            cat.save_settings(ruim)
    assert cat.get_settings() == base


def test_upsert_filament_com_id_atualiza_em_vez_de_inserir(cat):
    b = cat.add_brand("Bambu Lab")
    fid = cat.upsert_filament(_filamento(b))
    again = cat.upsert_filament(_filamento(b, price="99.90", fid=fid))
    assert again == fid
    f, = cat.list_filaments()
    assert f.roll_price == Decimal("99.90")


def test_densidade_preenchida_volta_como_decimal(cat):
    b = cat.add_brand("Bambu Lab")
    f = _filamento(b)
    cat.upsert_filament(Filament(None, b, "", f.line, "PLA", f.roll_grams,
                                 f.roll_price, Decimal("1.24"), True))
    assert cat.list_filaments()[0].density == Decimal("1.24")


def test_pontes_para_o_calculo():
    f = _filamento(1, grams="750", price="120")
    assert f.as_filament_line(Decimal("10")) == FilamentLine(
        Decimal("10"), Decimal("120"), Decimal("750"))
    assert _impressora().as_printer_costs() == PrinterCosts(Decimal("120"))


def test_delete_brand_com_filamentos_levanta_value_error(cat):
    b = cat.add_brand("Bambu Lab")
    fid = cat.upsert_filament(_filamento(b))
    with pytest.raises(ValueError, match="filamentos"):
        cat.delete_brand(b)
    cat.delete_filament(fid)
    cat.delete_brand(b)
    assert cat.list_brands() == []


def test_presets_de_tarefa_crud(cat):
    tid = cat.upsert_task_preset(TaskPreset(None, "Lixar", 15))
    cat.upsert_task_preset(TaskPreset(tid, "Lixar bem", 20))
    p, = cat.list_task_presets()
    assert (p.id, p.name, p.minutes) == (tid, "Lixar bem", 20)
    cat.delete_task_preset(tid)
    assert cat.list_task_presets() == []


def test_impressora_ida_e_volta_e_update(cat):
    pid = cat.upsert_printer(_impressora())
    cat.upsert_printer(_impressora(pid=pid))
    p, = cat.list_printers()
    assert (p.name, p.model_id, p.average_watts) == ("A1", "Bambu Lab A1",
                                                     Decimal("120"))


def test_delete_printer_remove_so_a_escolhida(cat):
    a = cat.upsert_printer(_impressora("Bambu Lab A1"))
    b = cat.upsert_printer(_impressora("Bambu Lab P1S"))
    cat.delete_printer(a)
    assert [p.id for p in cat.list_printers()] == [b]


def test_migrate_remove_custos_antigos_da_impressora(tmp_path):
    import sqlite3
    path = tmp_path / "antigo.db"
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE printers (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            model_id TEXT NOT NULL DEFAULT '', purchase_price TEXT NOT NULL,
            lifetime_hours TEXT NOT NULL, average_watts TEXT NOT NULL,
            maintenance_per_hour TEXT NOT NULL);
        INSERT INTO printers VALUES (7, 'A1', 'Bambu Lab A1', '4500', '5000', '120', '0.30');
    """)
    old.commit()
    old.close()
    cat = Catalog(path)
    cat.migrate()
    colunas = {r["name"] for r in cat.connection.execute("PRAGMA table_info(printers)")}
    assert colunas == {"id", "name", "model_id", "average_watts"}
    assert cat.list_printers() == [Printer(7, "A1", "Bambu Lab A1", Decimal("120"))]
    cat.upsert_printer(Printer(None, "P1S", "Bambu Lab P1S", Decimal("150")))
    assert len(cat.list_printers()) == 2
    cat.close()


def test_dados_da_empresa_ida_e_volta(cat):
    from calculadora3d.core.catalog import CompanyInfo
    assert cat.get_company() == CompanyInfo()
    info = CompanyInfo(name="Borcelle", address="Rua Alegre, 123", phone="(12) 3456-7890",
                       site="www.grandesite.com.br", email="ola@grandesite.com.br",
                       social="@grandesite")
    cat.save_company(info)
    assert cat.get_company() == info
    cat.save_company(CompanyInfo(name="  Borcelle  ", address="Rua"))
    assert cat.get_company() == CompanyInfo(name="Borcelle", address="Rua")


def test_dados_da_empresa_nao_atrapalham_as_configuracoes(cat):
    from calculadora3d.core.catalog import CompanyInfo
    cat.save_company(CompanyInfo(name="Borcelle", address="Rua"))
    assert cat.get_settings() == Settings()


def test_numero_do_orcamento_so_avanca_quando_confirmado(cat):
    assert cat.next_quote_number() == 1
    assert cat.next_quote_number() == 1
    cat.confirm_quote_number(1)
    assert cat.next_quote_number() == 2
    cat.confirm_quote_number(2)
    cat.confirm_quote_number(1)  # confirmação atrasada não volta o contador
    assert cat.next_quote_number() == 3


def test_printer_for_model_ignora_caixa_e_espacos():
    a1 = Printer(1, "A1", " Bambu Lab A1 ", Decimal("120"))
    p1s = Printer(2, "P1S", "Bambu Lab P1S", Decimal("150"))
    assert printer_for_model([a1, p1s], "bambu lab a1") == a1
    assert printer_for_model([a1, p1s], "") is None
    assert printer_for_model([a1, p1s], None) is None
    assert printer_for_model([a1], "X1C") is None
