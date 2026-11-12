"""Página Histórico: orçamentos salvos, para reabrir, duplicar ou excluir."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import Catalog
from calculadora3d.core.quotes import (
    QuoteSummary, delete_quote, list_quotes, load_quote, order_products,
)
from calculadora3d.ui.formatting import brl, date_time
from calculadora3d.ui.pdf_export import TITLE as EXPORT_TITLE, export_quotes_pdf

COLUMNS = ("Data", "Nome", "Custo total", "Preço de varejo")
EMPTY_TEXT = "Nenhum orçamento salvo. Salve um cálculo na tela Precificar."
RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class HistoryPage(QWidget):
    reopen_requested = Signal(int)
    duplicate_requested = Signal(int)

    def __init__(self, catalog: Catalog, parent=None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self._quotes: list[QuoteSummary] = []

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        for col in range(len(COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.cellDoubleClicked.connect(lambda _r, _c: self._emit(self.reopen_requested))

        self.empty_label = QLabel(EMPTY_TEXT)
        self.empty_label.setStyleSheet("color: gray;")

        self.reopen_button = QPushButton("Reabrir")
        self.reopen_button.setToolTip("Mostra os valores do momento em que foi salvo")
        self.reopen_button.clicked.connect(lambda: self._emit(self.reopen_requested))
        self.duplicate_button = QPushButton("Duplicar")
        self.duplicate_button.setToolTip(
            "Usa este orçamento como base de um novo cálculo, com os preços atuais")
        self.duplicate_button.clicked.connect(lambda: self._emit(self.duplicate_requested))
        self.export_button = QPushButton(EXPORT_TITLE)
        self.export_button.setToolTip(
            "Selecione um ou mais orçamentos (Ctrl ou Shift) para virarem os produtos do PDF")
        self.export_button.clicked.connect(self.export_selected)
        self.delete_button = QPushButton("Excluir")
        self.delete_button.clicked.connect(self.delete_selected)
        buttons = QHBoxLayout()
        for button in (self.reopen_button, self.duplicate_button, self.export_button,
                       self.delete_button):
            buttons.addWidget(button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)

        self.reload()

    def showEvent(self, event) -> None:
        self.reload()
        super().showEvent(event)

    def reload(self) -> None:
        self._quotes = list_quotes(self.catalog)
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.setRowCount(len(self._quotes))
        for row, quote in enumerate(self._quotes):
            cells = (date_time(quote.created_at), quote.name,
                     brl(quote.total_cost), brl(quote.retail_price))
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col >= 2:
                    item.setTextAlignment(RIGHT)
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)
        self.empty_label.setVisible(not self._quotes)
        self._update_buttons()

    def selected_ids(self) -> list[int]:
        """Ids selecionados, na ordem da tabela."""
        rows = sorted(r.row() for r in self.table.selectionModel().selectedRows())
        return [self._quotes[r].id for r in rows if 0 <= r < len(self._quotes)]

    def selected_id(self) -> int | None:
        """Id do orçamento selecionado, só quando há exatamente um."""
        ids = self.selected_ids()
        return ids[0] if len(ids) == 1 else None

    def export_selected(self) -> None:
        ids = self.selected_ids()
        if not ids:
            return
        try:
            products = [product for quote_id in ids
                        for product in order_products(load_quote(self.catalog, quote_id))]
        except Exception as exc:
            QMessageBox.warning(self, EXPORT_TITLE,
                                f"Não foi possível abrir o orçamento: {exc}")
            return
        export_quotes_pdf(self, self.catalog, products)

    def delete_selected(self) -> None:
        quote_id = self.selected_id()
        if quote_id is None:
            return
        name = next(q.name for q in self._quotes if q.id == quote_id)
        answer = QMessageBox.question(
            self, "Excluir orçamento",
            f"Excluir o orçamento “{name}” do histórico? Isso não pode ser desfeito.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_quote(self.catalog, quote_id)
        except Exception as exc:
            QMessageBox.warning(self, "Excluir orçamento",
                                f"Não foi possível excluir o orçamento: {exc}")
        self.reload()

    # Interno
    def _emit(self, signal) -> None:
        quote_id = self.selected_id()
        if quote_id is not None:
            signal.emit(quote_id)

    def _update_buttons(self) -> None:
        single = self.selected_id() is not None
        for button in (self.reopen_button, self.duplicate_button, self.delete_button):
            button.setEnabled(single)
        self.export_button.setEnabled(bool(self.selected_ids()))
