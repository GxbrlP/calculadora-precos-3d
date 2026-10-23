from decimal import Decimal
from pathlib import Path

from calculadora3d.core.models import FilamentUsage, Plate, SlicedProject


def test_total_seconds_ignora_placa_pulada():
    p = SlicedProject(
        name="x", source_path=Path("x.3mf"), printer_model="C11",
        plates=(Plate(1, 3600, Decimal("10"), 2, False),
                Plate(2, 1800, Decimal("5"), 1, True)),
        usage=(), is_sliced=True, warnings=(),
    )
    assert p.total_seconds == 3600
    assert p.copies == 2


def test_color_count_conta_slots_nao_cores_distintas():
    usage = (
        FilamentUsage(1, "PLA", "#000000", Decimal("5"), Decimal("1.7"), None, None),
        FilamentUsage(2, "PLA", "#000000", Decimal("3"), Decimal("1.0"), None, None),
    )
    p = SlicedProject("x", Path("x.3mf"), None, (), usage, True, ())
    assert p.color_count == 2
    assert p.total_grams == Decimal("8")


def test_copies_minimo_um_quando_nao_ha_instancias():
    p = SlicedProject("x", Path("x.3mf"), None,
                      (Plate(1, 60, Decimal("1"), 0, False),), (), True, ())
    assert p.copies == 1


def test_color_count_nao_fatiado_conta_todas_as_entradas():
    usage = tuple(
        FilamentUsage(i, "PLA", "#000000", Decimal("0"), Decimal("0"), None, None)
        for i in (1, 2, 3)
    )
    p = SlicedProject("x", Path("x.3mf"), None, (), usage, False, ())
    assert p.color_count == 3
    assert p.total_grams == Decimal("0")
    assert p.total_seconds == 0


def test_color_count_fatiado_ignora_slot_sem_gramas():
    usage = (
        FilamentUsage(1, "PLA", "#000000", Decimal("5"), Decimal("1.7"), None, None),
        FilamentUsage(2, "PLA", "#FFFFFF", Decimal("0"), Decimal("0"), None, None),
    )
    p = SlicedProject("x", Path("x.3mf"), None, (), usage, True, ())
    assert p.color_count == 1


def test_copies_usa_model_instances_quando_nao_ha_placas():
    p = SlicedProject("x", Path("x.3mf"), None, (), (), False, (), model_instances=3)
    assert p.copies == 3


def test_copies_minimo_um_sem_placas_e_sem_instancias():
    p = SlicedProject("x", Path("x.3mf"), None, (), (), False, ())
    assert p.copies == 1
