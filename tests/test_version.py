import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import re  # noqa: E402
import tomllib  # noqa: E402
from pathlib import Path  # noqa: E402

import calculadora3d  # noqa: E402
from tools import check_version  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", calculadora3d.__version__)


def test_pyproject_reads_version_from_package():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" not in data["project"]
    assert "version" in data["project"]["dynamic"]
    assert data["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "calculadora3d.__version__"}


def test_tag_check_accepts_matching_tag():
    assert check_version.main([f"v{calculadora3d.__version__}"]) == 0


def test_tag_check_rejects_other_version_and_missing_v(capsys):
    assert check_version.main(["v99.0.0"]) == 1
    assert check_version.main([calculadora3d.__version__]) == 1
    assert "não bate" in capsys.readouterr().err


def test_window_title_shows_version(tmp_path):
    from PySide6.QtWidgets import QApplication

    from calculadora3d.core.catalog import Catalog
    from calculadora3d.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])  # noqa: F841
    catalog = Catalog(tmp_path / "t.db")
    catalog.migrate()
    try:
        title = MainWindow(catalog).windowTitle()
        assert title == f"Calculadora 3D {calculadora3d.__version__}"
    finally:
        catalog.close()
