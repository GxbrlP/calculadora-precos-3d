import pytest
from decimal import Decimal

from datetime import datetime

from calculadora3d.ui.formatting import brl, date_time, duration, grams


def test_brl_usa_ponto_de_milhar_e_virgula_decimal():
    assert brl(Decimal("1234.5")) == "R$ 1.234,50"
    assert brl(Decimal("0")) == "R$ 0,00"
    assert brl(Decimal("1.005")) == "R$ 1,01"   # ROUND_HALF_UP


def test_brl_milhoes_e_negativos():
    assert brl(Decimal("1234567.891")) == "R$ 1.234.567,89"
    assert brl(Decimal("-1")) == "-R$ 1,00"
    assert brl(Decimal("-0.001")) == "R$ 0,00"


def test_duration_em_horas_e_minutos():
    assert duration(3600) == "1h 00min"
    assert duration(5430) == "1h 30min"
    assert duration(0) == "0min"


def test_duration_abaixo_de_uma_hora_e_truncada_em_minutos():
    assert duration(2181) == "36min"
    assert duration(11037) == "3h 03min"
    assert duration(59) == "0min"


def test_grams_com_duas_casas_e_virgula():
    assert grams(Decimal("33.83")) == "33,83 g"
    assert grams(Decimal("0.005")) == "0,01 g"
    assert grams(Decimal("1234.5")) == "1.234,50 g"


def test_parse_decimal_aceita_virgula_e_milhar_sem_float():
    from calculadora3d.ui.formatting import parse_decimal
    assert parse_decimal("1.234,56") == Decimal("1234.56")
    assert parse_decimal(" 12,5 ") == Decimal("12.5")
    assert parse_decimal("0.1") == Decimal("0.1")


def test_parse_decimal_rejeita_invalido_e_negativo():
    from calculadora3d.ui.formatting import parse_decimal
    for bad in ("", "abc", "-1", "NaN", "Infinity"):
        with pytest.raises(ValueError):
            parse_decimal(bad)


def test_parse_decimal_ponto_so_de_milhar_e_milhar():
    from calculadora3d.ui.formatting import parse_decimal
    assert parse_decimal("1.000") == Decimal("1000")
    assert parse_decimal("1.500") == Decimal("1500")
    assert parse_decimal("1.234.567") == Decimal("1234567")
    assert parse_decimal("1.234,56") == Decimal("1234.56")
    assert parse_decimal("0.1") == Decimal("0.1")
    assert parse_decimal("12.5") == Decimal("12.5")


def test_parse_decimal_grupo_zero_a_esquerda_e_decimal():
    from calculadora3d.ui.formatting import parse_decimal
    assert parse_decimal("0.500") == Decimal("0.5")
    assert parse_decimal("0.100") == Decimal("0.1")
    assert parse_decimal("1.000") == Decimal("1000")


def test_date_time_dia_mes_ano_hora_minuto():
    assert date_time(datetime(2026, 3, 7, 9, 5, 42)) == "07/03/2026 09:05"
