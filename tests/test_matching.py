from decimal import Decimal

from calculadora3d.core.catalog import Filament
from calculadora3d.core.matching import Confidence, Match, match_slot
from calculadora3d.core.models import FilamentUsage


def _f(brand, line, type_):
    return Filament(None, 1, brand, line, type_, Decimal("1000"),
                    Decimal("100"), None, True)


def _usage(type="PLA", vendor="Bambu Lab", settings_id=None):
    return FilamentUsage(1, type, "#000", Decimal("10"), Decimal("3"),
                         vendor=vendor, settings_id=settings_id)


def test_marca_e_linha_batem_da_confianca_alta():
    u = _usage(vendor="Bambu Lab", settings_id="Bambu PLA Basic @BBL X1C")
    m = match_slot(u, [_f("Bambu Lab", "PLA Basic", "PLA"), _f("Voolt", "PLA", "PLA")])
    assert m.confidence is Confidence.HIGH and m.filament.line == "PLA Basic"


def test_so_a_marca_e_o_tipo_batem_da_confianca_media():
    u = _usage(vendor="Bambu Lab", settings_id="Algo Desconhecido @BBL A1")
    m = match_slot(u, [_f("Bambu Lab", "PLA Matte", "PLA"), _f("Voolt", "PLA", "PLA"),
                       _f("Bambu Lab", "PETG HF", "PETG")])
    assert m.confidence is Confidence.MEDIUM and m.filament.line == "PLA Matte"


def test_tipo_unico_no_catalogo_da_confianca_baixa():
    m = match_slot(_usage(type="PETG", vendor="Marca Desconhecida"),
                   [_f("Voolt", "PETG", "PETG")])
    assert m.confidence is Confidence.LOW


def test_dois_candidatos_do_mesmo_tipo_sem_marca_nao_casam():
    m = match_slot(_usage(type="PLA", vendor=None),
                   [_f("A", "PLA", "PLA"), _f("B", "PLA", "PLA")])
    assert m.confidence is Confidence.NONE and m.filament is None


def test_catalogo_vazio_nao_casa():
    assert match_slot(_usage(), []) == Match(None, Confidence.NONE)


def test_empate_na_maior_linha_nao_da_confianca_alta():
    u = _usage(settings_id="Bambu PLA Basic @BBL A1")
    m = match_slot(u, [_f("Bambu Lab", "PLA Basic", "PLA"),
                       _f("Bambu Lab", "pla basic", "PLA")])
    assert m.confidence is Confidence.NONE and m.filament is None


def test_maior_linha_vence_entre_varias_contidas():
    u = _usage(settings_id="Bambu PLA Basic @BBL A1")
    m = match_slot(u, [_f("Bambu Lab", "PLA", "PLA"),
                       _f("Bambu Lab", "PLA Basic", "PLA")])
    assert m.confidence is Confidence.HIGH and m.filament.line == "PLA Basic"


def test_varios_candidatos_de_marca_e_tipo_nao_sao_media():
    u = _usage(settings_id="Outra Coisa")
    m = match_slot(u, [_f("Bambu Lab", "PLA Matte", "PLA"),
                       _f("Bambu Lab", "PLA Silk", "PLA"),
                       _f("Voolt", "PLA", "PLA"), _f("Voolt", "PETG", "PETG")])
    assert m.confidence is Confidence.NONE and m.filament is None


def test_marca_ignora_caixa_e_acento():
    u = _usage(vendor="  bambu lab ", settings_id="Bambu PLA Basic @BBL A1")
    m = match_slot(u, [_f("Bámbu Lab", "PLA Basic", "PLA")])
    assert m.confidence is Confidence.HIGH


def test_settings_id_e_limpo_do_sufixo_e_do_arroba():
    u = _usage(settings_id="Bambu PLA Basic @BBL X1C(Butterfly_knife_free_movement.3mf)")
    m = match_slot(u, [_f("Bambu Lab", "PLA Basic", "PLA"), _f("Bambu Lab", "X1C", "PLA"),
                       _f("Bambu Lab", "Butterfly", "PLA")])
    assert m.confidence is Confidence.HIGH and m.filament.line == "PLA Basic"


def test_sufixo_entre_parenteses_sem_arroba_tambem_e_removido():
    u = _usage(settings_id="Bambu PLA Basic(Projeto Matte.3mf)")
    m = match_slot(u, [_f("Bambu Lab", "PLA Basic", "PLA"), _f("Bambu Lab", "Matte", "PLA")])
    assert m.filament.line == "PLA Basic" and m.confidence is Confidence.HIGH


def test_fixture_generica_casa_pela_linha():
    u = _usage(vendor="Generic", settings_id="Generic PLA @BBL A1")
    m = match_slot(u, [_f("Generic", "PLA", "PLA"), _f("Generic", "PETG", "PETG")])
    assert m.confidence is Confidence.HIGH and m.filament.type == "PLA"
