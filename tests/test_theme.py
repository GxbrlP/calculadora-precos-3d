import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from calculadora3d.ui import theme  # noqa: E402


def test_apply_theme_enlarges_font_and_buttons():
    app = QApplication.instance() or QApplication([])
    before = QPushButton("Salvar").sizeHint()

    theme.apply_theme(app)

    assert app.font().pointSizeF() == theme.APP_FONT_PT
    after = QPushButton("Salvar").sizeHint()
    assert after.height() >= before.height() + theme.BUTTON_EXTRA_HEIGHT
    assert after.width() > before.width()
