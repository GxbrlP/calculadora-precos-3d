import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from calculadora3d.core import paths
from calculadora3d.core.catalog import Catalog
from calculadora3d.ui.main_window import MainWindow
from calculadora3d.ui.theme import apply_theme


def resource_path(name: str) -> Path:
    """Caminho de um recurso, no código-fonte ou dentro do PyInstaller."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "calculadora3d" / "resources" / name
    return Path(__file__).resolve().parent / "resources" / name


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app)
    app.setWindowIcon(QIcon(str(resource_path("icon.png"))))
    catalog = Catalog(paths.db_path())
    try:
        catalog.migrate()
        window = MainWindow(catalog)
        window.show()
        return app.exec()
    finally:
        catalog.close()
