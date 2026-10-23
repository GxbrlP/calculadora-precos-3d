"""Área de soltar arquivos .3mf, com botão para abrir pelo seletor de arquivos."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget,
)


def filter_3mf(items) -> list[Path]:
    """Mantém só caminhos com sufixo .3mf (sem diferenciar maiúsculas).

    Aceita Path, str ou QUrl; URLs que não são arquivos locais são ignoradas.
    """
    result: list[Path] = []
    for item in items:
        if hasattr(item, "toLocalFile"):
            text = item.toLocalFile()
        else:
            text = str(item)
        if text and text.lower().endswith(".3mf"):
            result.append(Path(text))
    return result


class DropArea(QWidget):
    files_dropped = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self.setMinimumHeight(110)
        self._set_highlight(False)

        self._label = QLabel("Arraste um ou mais arquivos .3mf aqui")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.open_button = QPushButton("Abrir arquivos…")
        self.open_button.clicked.connect(self._open_dialog)

        layout = QVBoxLayout(self)
        layout.addWidget(self._label)
        layout.addWidget(self.open_button, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _set_highlight(self, on: bool) -> None:
        color = "#2d7ff9" if on else "#888888"
        self.setStyleSheet(
            f"#dropArea {{ border: 2px dashed {color}; border-radius: 8px; }}")

    def _open_dialog(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self, "Abrir arquivos", "", "Projetos 3MF (*.3mf)")
        paths = filter_3mf(names)
        if paths:
            self.files_dropped.emit(paths)

    def dragEnterEvent(self, event) -> None:
        if filter_3mf(event.mimeData().urls()):
            event.acceptProposedAction()
            self._set_highlight(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._set_highlight(False)

    def dropEvent(self, event) -> None:
        self._set_highlight(False)
        paths = filter_3mf(event.mimeData().urls())
        if paths:
            event.acceptProposedAction()
            self.files_dropped.emit(paths)
        else:
            event.ignore()
