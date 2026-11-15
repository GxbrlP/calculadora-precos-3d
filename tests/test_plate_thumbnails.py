import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QIODevice  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from calculadora3d.core.models import PlateThumbnail  # noqa: E402
from calculadora3d.core.threemf import PNG_SIGNATURE  # noqa: E402
from calculadora3d.ui.widgets.plate_thumbnails import PlateThumbnails, caption  # noqa: E402


def _png() -> bytes:
    image = QImage(4, 4, QImage.Format.Format_RGB32)
    image.fill(0x336699)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def test_legendas():
    assert caption(PlateThumbnail(3, b"")) == "Placa 3"
    assert caption(PlateThumbnail(2, b"", unsliced=True)) == "Placa 2 · não fatiada"


def test_faixa_mostra_so_as_imagens_validas():
    QApplication.instance() or QApplication([])
    parent = QWidget()
    w = PlateThumbnails([PlateThumbnail(1, _png()), PlateThumbnail(2, PNG_SIGNATURE + b"x")],
                        parent)
    assert w.shown() == 1
    assert w.isVisibleTo(parent)


def test_sem_imagem_fica_oculta():
    QApplication.instance() or QApplication([])
    parent = QWidget()
    w = PlateThumbnails([], parent)
    assert w.shown() == 0
    assert not w.isVisibleTo(parent)
