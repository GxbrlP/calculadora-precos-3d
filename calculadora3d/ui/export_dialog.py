"""Diálogo de exportação: descrição e faixa de preço de cada produto do orçamento."""
from collections.abc import Sequence
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import CompanyInfo
from calculadora3d.core.export import (
    QuoteItem, missing_company_fields, price_options, quote_item,
)
from calculadora3d.ui.formatting import brl

GO_TO_SETTINGS = 2
HEADERS = ("Descrição do produto", "Preço a apresentar", "Qt.", "Total")
RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class ExportDialog(QDialog):
    def __init__(self, company: CompanyInfo, products: Sequence[dict], number: int,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportar orçamento")
        self.setMinimumWidth(880)
        self._products = list(products)
        self._descriptions: list[QLineEdit] = []
        self._combos: list[QComboBox] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Orçamento nº {number}"))

        self.table = QTableWidget(len(self._products), len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        for row, product in enumerate(self._products):
            description = QLineEdit(str(product.get("project_name", "")))
            description.setPlaceholderText("ex.: Suporte de parede")
            description.textChanged.connect(self._update)
            combo = QComboBox()
            for option in price_options(product):
                combo.addItem(f"{option.name} — {brl(option.unit)}/un.", option.name)
            combo.currentIndexChanged.connect(self._update)
            quantity = QTableWidgetItem(str(product["copies"]))
            quantity.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            total = QTableWidgetItem()
            total.setTextAlignment(RIGHT)
            self.table.setCellWidget(row, 0, description)
            self.table.setCellWidget(row, 1, combo)
            self.table.setItem(row, 2, quantity)
            self.table.setItem(row, 3, total)
            self._descriptions.append(description)
            self._combos.append(combo)
        self.table.resizeRowsToContents()
        layout.addWidget(self.table)

        self.total_label = QLabel()
        self.total_label.setAlignment(RIGHT)
        self.total_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.total_label)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.message_label)

        self.buttons = QDialogButtonBox()
        self.export_button = self.buttons.addButton(
            "Exportar PDF", QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        bottom = QHBoxLayout()
        missing = missing_company_fields(company)
        if missing:
            self.message_label.setText(
                "Antes de exportar, preencha em Configurações: " + ", ".join(missing) + ".")
            settings_button = QPushButton("Abrir Configurações")
            settings_button.clicked.connect(lambda: self.done(GO_TO_SETTINGS))
            bottom.addWidget(settings_button)
        self._company_ok = not missing
        bottom.addStretch(1)
        bottom.addWidget(self.buttons)
        layout.addLayout(bottom)
        self._update()

    def items(self) -> tuple[QuoteItem, ...]:
        """Itens do orçamento; levanta ValueError se alguma linha estiver incompleta."""
        return tuple(quote_item(product, combo.currentData(), edit.text())
                     for product, combo, edit in
                     zip(self._products, self._combos, self._descriptions))

    def _update(self) -> None:
        grand = Decimal(0)
        problem = None
        for row, (product, combo, edit) in enumerate(
                zip(self._products, self._combos, self._descriptions)):
            cell = self.table.item(row, 3)
            try:
                item = quote_item(product, combo.currentData(), edit.text())
            except ValueError as exc:
                cell.setText("—")
                problem = problem or str(exc)
                continue
            cell.setText(brl(item.total))
            grand += item.total
        self.total_label.setText(f"Total geral: {brl(grand)}")
        if self._company_ok:
            self.message_label.setText(problem or "")
        self.export_button.setEnabled(self._company_ok and problem is None)
