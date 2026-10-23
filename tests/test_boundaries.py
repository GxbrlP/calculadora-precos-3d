import re
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent / "calculadora3d" / "core"
UI_IMPORT = re.compile(r"^\s*(from\s+calculadora3d\.ui|import\s+calculadora3d\.ui"
                       r"|from\s+calculadora3d\s+import\s+ui)", re.MULTILINE)


def test_core_nao_importa_pyside6_nem_ui():
    arquivos = list(CORE.rglob("*.py"))
    assert arquivos, f"nenhum arquivo .py em {CORE}"
    for arquivo in arquivos:
        texto = arquivo.read_text(encoding="utf-8")
        assert "PySide6" not in texto, arquivo
        assert not UI_IMPORT.search(texto), arquivo
