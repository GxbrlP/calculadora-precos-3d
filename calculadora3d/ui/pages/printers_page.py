"""Página Impressoras: lista do catálogo e formulário de cadastro/edição."""
from decimal import Decimal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import Catalog, Printer
from calculadora3d.ui.formatting import brl, parse_decimal

COLUMNS = ("Nome", "Modelo do 3mf", "Preço de compra", "Vida útil",
           "Potência média", "Manutenção/h")


def _text(value: Decimal) -> str:
    return str(value).replace(".", ",")


class PrintersPage(QWidget):
    catalog_changed = Signal()

    def __init__(self, catalog: Catalog, parent=None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self._printers: list[Printer] = []
        self._editing_id: int | None = None

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection)

        self.name_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("ex.: Bambu Lab A1")
        self.price_edit = QLineEdit()
        self.lifetime_edit = QLineEdit()
        self.watts_edit = QLineEdit()
        self.maintenance_edit = QLineEdit()

        self.message_label = QLabel()
        self.message_label.setStyleSheet("color: #b00020;")
        self.message_label.setWordWrap(True)

        self.save_button = QPushButton("Salvar")
        self.save_button.clicked.connect(self.save)
        self.new_button = QPushButton("Novo")
        self.new_button.clicked.connect(self.clear_form)
        self.delete_button = QPushButton("Excluir")
        self.delete_button.clicked.connect(self.delete_selected)

        form = QFormLayout()
        form.addRow("Nome", self.name_edit)
        form.addRow("Modelo do 3mf", self.model_edit)
        form.addRow("Preço de compra (R$)", self.price_edit)
        form.addRow("Vida útil (h)", self.lifetime_edit)
        form.addRow("Potência média (W)", self.watts_edit)
        form.addRow("Manutenção por hora (R$)", self.maintenance_edit)
        buttons = QHBoxLayout()
        for b in (self.save_button, self.new_button, self.delete_button):
            buttons.addWidget(b)
        buttons.addStretch(1)
        self.form_box = QGroupBox("Nova impressora")
        box_layout = QVBoxLayout(self.form_box)
        box_layout.addLayout(form)
        box_layout.addWidget(self.message_label)
        box_layout.addLayout(buttons)

        layout = QHBoxLayout(self)
        layout.addWidget(self.table, 3)
        layout.addWidget(self.form_box, 2)

        self.reload()

    def reload(self, select_id: int | None = None) -> None:
        self._printers = self.catalog.list_printers()
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._printers))
        for row, p in enumerate(self._printers):
            cells = (p.name, p.model_id, brl(p.purchase_price),
                     f"{_text(p.lifetime_hours)} h", f"{_text(p.average_watts)} W",
                     brl(p.maintenance_per_hour))
            for col, text in enumerate(cells):
                self.table.setItem(row, col, QTableWidgetItem(text))
            if p.id == select_id:
                self.table.selectRow(row)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.blockSignals(False)

    def clear_form(self) -> None:
        self._editing_id = None
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.blockSignals(False)
        for edit in (self.name_edit, self.model_edit, self.price_edit,
                     self.lifetime_edit, self.watts_edit, self.maintenance_edit):
            edit.clear()
        self.message_label.clear()
        self.form_box.setTitle("Nova impressora")

    def _on_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        p = self._printers[rows[0].row()]
        self._editing_id = p.id
        self.name_edit.setText(p.name)
        self.model_edit.setText(p.model_id)
        self.price_edit.setText(_text(p.purchase_price))
        self.lifetime_edit.setText(_text(p.lifetime_hours))
        self.watts_edit.setText(_text(p.average_watts))
        self.maintenance_edit.setText(_text(p.maintenance_per_hour))
        self.message_label.clear()
        self.form_box.setTitle("Editar impressora")

    def _number(self, edit: QLineEdit, label: str, positive: bool = False) -> Decimal:
        try:
            value = parse_decimal(edit.text())
        except ValueError:
            raise ValueError(f"{label} inválido(a).") from None
        if positive and value <= 0:
            raise ValueError(f"{label} deve ser maior que zero.")
        return value

    def save(self) -> None:
        try:
            name = self.name_edit.text().strip()
            if not name:
                raise ValueError("Informe o nome da impressora.")
            printer = Printer(
                self._editing_id, name, self.model_edit.text().strip(),
                self._number(self.price_edit, "Preço de compra"),
                self._number(self.lifetime_edit, "Vida útil", positive=True),
                self._number(self.watts_edit, "Potência média"),
                self._number(self.maintenance_edit, "Manutenção por hora"))
        except ValueError as error:
            self.message_label.setText(str(error))
            return
        saved_id = self.catalog.upsert_printer(printer)
        self.message_label.clear()
        self._editing_id = saved_id
        self.form_box.setTitle("Editar impressora")
        self.reload(select_id=saved_id)
        self.catalog_changed.emit()

    def delete_selected(self) -> None:
        if self._editing_id is None:
            self.message_label.setText("Selecione uma impressora para excluir.")
            return
        answer = QMessageBox.question(
            self, "Excluir impressora", "Excluir esta impressora do catálogo?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.catalog.delete_printer(self._editing_id)
        self.clear_form()
        self.reload()
        self.catalog_changed.emit()
