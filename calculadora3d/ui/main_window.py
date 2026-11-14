from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget, QMainWindow,
)

from calculadora3d.core.catalog import Catalog
from calculadora3d.core.quotes import load_quote
from calculadora3d.ui.pages.filaments_page import FilamentsPage
from calculadora3d.ui.pages.history_page import HistoryPage
from calculadora3d.ui.pages.printers_page import PrintersPage
from calculadora3d.ui.pages.pricing_page import PricingPage
from calculadora3d.ui.pages.settings_page import SettingsPage

PAGE_NAMES = ("Precificar", "Filamentos", "Impressoras", "Configurações", "Histórico")


class MainWindow(QMainWindow):
    def __init__(self, catalog: Catalog):
        super().__init__()
        self.catalog = catalog
        self.setWindowTitle("Calculadora 3D")
        self._resize_to_screen(1280, 820)

        self._stack = QStackedWidget()
        self._buttons: dict[str, QPushButton] = {}
        self._pages: dict[str, QWidget] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        sidebar = QVBoxLayout()
        sidebar.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._sidebar = sidebar

        side_widget = QWidget()
        side_widget.setFixedWidth(210)
        side_widget.setLayout(sidebar)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(side_widget)
        layout.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        for name in PAGE_NAMES:
            placeholder = QLabel(name)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.add_page(name, placeholder)
        self.pricing_page = PricingPage(catalog)
        self.pricing_page.go_to_page.connect(self.show_page)
        self.add_page("Precificar", self.pricing_page)
        self.filaments_page = FilamentsPage(catalog)
        self.printers_page = PrintersPage(catalog)
        self.add_page("Filamentos", self.filaments_page)
        self.add_page("Impressoras", self.printers_page)
        self.settings_page = SettingsPage(catalog)
        self.add_page("Configurações", self.settings_page)
        self.settings_page.settings_changed.connect(self.pricing_page.refresh_catalog)
        self.filaments_page.catalog_changed.connect(self.pricing_page.refresh_catalog)
        self.printers_page.catalog_changed.connect(self.pricing_page.refresh_catalog)
        self.pricing_page.register_filament_requested.connect(self._register_filament)
        self.history_page = HistoryPage(catalog)
        self.add_page("Histórico", self.history_page)
        self.pricing_page.quote_saved.connect(lambda _id: self.history_page.reload())
        self.history_page.reopen_requested.connect(
            lambda quote_id: self._open_quote(quote_id, recalculate=False))
        self.history_page.duplicate_requested.connect(
            lambda quote_id: self._open_quote(quote_id, recalculate=True))
        self.show_page(PAGE_NAMES[0])

    def _resize_to_screen(self, width: int, height: int) -> None:
        """Tamanho inicial, sem passar da área livre da tela."""
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            free = screen.availableGeometry()
            width = min(width, free.width() - 40)
            height = min(height, free.height() - 40)
        self.resize(width, height)

    def _register_filament(self, data: dict) -> None:
        self.show_page("Filamentos")
        self.filaments_page.prefill(data)

    def _open_quote(self, quote_id: int, *, recalculate: bool) -> None:
        try:
            snapshot = load_quote(self.catalog, quote_id)
            self.pricing_page.load_snapshot(snapshot, recalculate=recalculate)
        except Exception as exc:
            QMessageBox.warning(self, "Histórico",
                                f"Não foi possível abrir o orçamento: {exc}")
            self.history_page.reload()
            return
        self.show_page("Precificar")

    def add_page(self, name: str, widget: QWidget) -> None:
        """Registra uma página; se o nome já existe, substitui o widget."""
        if name in self._pages:
            old = self._pages[name]
            index = self._stack.indexOf(old)
            was_current = self._stack.currentWidget() is old
            self._stack.removeWidget(old)
            old.deleteLater()
            self._stack.insertWidget(index, widget)
            if was_current:
                self._stack.setCurrentWidget(widget)
            self._pages[name] = widget
            return
        self._stack.addWidget(widget)
        self._pages[name] = widget
        button = QPushButton(name)
        button.setCheckable(True)
        button.clicked.connect(lambda _checked=False, n=name: self.show_page(n))
        self._group.addButton(button)
        self._sidebar.addWidget(button)
        self._buttons[name] = button

    def show_page(self, name: str) -> None:
        self._stack.setCurrentWidget(self._pages[name])
        self._buttons[name].setChecked(True)

    def current_page_name(self) -> str:
        current = self._stack.currentWidget()
        return next(n for n, w in self._pages.items() if w is current)
