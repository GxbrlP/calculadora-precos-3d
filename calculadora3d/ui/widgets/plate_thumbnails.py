"""Faixa com a miniatura de cada placa, para reconhecer o arquivo de relance."""
from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from calculadora3d.core.models import PlateThumbnail

THUMB_SIZE = 128
# O render do fatiador tem fundo transparente: cinza médio mantém visível peça
# preta no tema escuro e peça branca no claro.
THUMB_STYLE = "background-color: #b4b4b4; border-radius: 6px;"


def caption(t: PlateThumbnail) -> str:
    return f"Placa {t.plate} · não fatiada" if t.unsliced else f"Placa {t.plate}"


class PlateThumbnails(QWidget):
    def __init__(self, thumbnails: Sequence[PlateThumbnail], parent=None) -> None:
        super().__init__(parent)
        strip = QWidget()
        row = QHBoxLayout(strip)
        row.setContentsMargins(0, 0, 0, 0)
        ratio = self.devicePixelRatioF()
        side = round(THUMB_SIZE * ratio)
        self._shown = 0
        for thumbnail in thumbnails:
            pixmap = QPixmap()
            if not pixmap.loadFromData(thumbnail.png, "PNG"):
                continue  # imagem estragada: some sem atrapalhar o resto
            pixmap = pixmap.scaled(side, side, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            pixmap.setDevicePixelRatio(ratio)
            image = QLabel()
            image.setPixmap(pixmap)
            image.setFixedSize(THUMB_SIZE, THUMB_SIZE)
            image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image.setStyleSheet(THUMB_STYLE)
            text = QLabel(caption(thumbnail))
            text.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            item = QVBoxLayout()
            item.addWidget(image)
            item.addWidget(text)
            row.addLayout(item)
            self._shown += 1
        row.addStretch(1)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(strip)
        scroll.setFixedHeight(strip.sizeHint().height()
                              + scroll.horizontalScrollBar().sizeHint().height())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        if not self._shown:
            self.hide()  # sem imagem não sobra quadro vazio

    def shown(self) -> int:
        return self._shown
