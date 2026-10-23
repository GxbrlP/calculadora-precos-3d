from pathlib import Path

from calculadora3d.ui.widgets.drop_area import filter_3mf


def test_filtra_apenas_3mf_sem_diferenciar_maiusculas():
    itens = ["a.3mf", "b.TXT", Path("c.3MF"), "d.gcode.3mf", "e.3mf.bak", ""]
    assert filter_3mf(itens) == [Path("a.3mf"), Path("c.3MF"), Path("d.gcode.3mf")]
