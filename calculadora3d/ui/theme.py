"""Tamanho de fonte e de botões do aplicativo inteiro.

Ajuste as constantes abaixo para deixar tudo maior ou menor; o resto da
interface (tabelas, painéis) acompanha porque usa a fonte do aplicativo.
"""
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle

APP_FONT_PT = 11          # o padrão do Windows é 9
BUTTON_EXTRA_WIDTH = 16   # px a mais na largura de cada botão
BUTTON_EXTRA_HEIGHT = 10  # px a mais na altura de cada botão


class RoomyStyle(QProxyStyle):
    """Estilo nativo com botões mais folgados (mais fáceis de ler e clicar)."""

    def sizeFromContents(self, type_, option, size, widget=None):
        result = super().sizeFromContents(type_, option, size, widget)
        if type_ == QStyle.ContentsType.CT_PushButton:
            result += QSize(BUTTON_EXTRA_WIDTH, BUTTON_EXTRA_HEIGHT)
        return result


def apply_theme(app: QApplication) -> None:
    app.setStyle(RoomyStyle(app.style().name()))
    font = app.font()
    font.setPointSizeF(APP_FONT_PT)
    app.setFont(font)
