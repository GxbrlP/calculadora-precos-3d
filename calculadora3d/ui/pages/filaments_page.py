"""Página Filamentos: lista do catálogo e formulário de cadastro/edição."""
from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import Catalog, Filament
from calculadora3d.ui.formatting import brl, grams, parse_decimal

NEW_BRAND = "+ Nova marca…"
COLUMNS = ("Marca", "Linha", "Tipo", "Peso do rolo", "Preço do rolo",
           "Preço por kg", "Ativo")
FILAMENT_TYPES = ("PLA", "PETG", "ABS", "ASA", "TPU", "PA", "PC")


def _optional_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


class FilamentsPage(QWidget):
    catalog_changed = Signal()

    def __init__(self, catalog: Catalog, parent=None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self._filaments: list[Filament] = []
        self._editing_id: int | None = None

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection)

        self.brand_combo = QComboBox()
        self.brand_combo.currentIndexChanged.connect(self._on_brand_changed)
        self.delete_brand_button = QPushButton("Excluir marca")
        self.delete_brand_button.clicked.connect(self.delete_brand)
        self.new_brand_edit = QLineEdit()
        self.new_brand_edit.setPlaceholderText("Nome da nova marca")
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("ex.: PLA Basic")
        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems(FILAMENT_TYPES)
        self.roll_grams_edit = QLineEdit("1000")
        self.roll_price_edit = QLineEdit()
        self.roll_price_edit.setPlaceholderText("ex.: 120,00")
        self.density_edit = QLineEdit()
        self.density_edit.setPlaceholderText("opcional, ex.: 1,24")
        self.per_kg_label = QLabel("—")
        self.active_check = QCheckBox("Ativo")
        self.active_check.setChecked(True)
        self.roll_grams_edit.textChanged.connect(self._update_per_kg)
        self.roll_price_edit.textChanged.connect(self._update_per_kg)

        self.message_label = QLabel()
        self.message_label.setStyleSheet("color: #b00020;")
        self.message_label.setWordWrap(True)

        self.save_button = QPushButton("Salvar")
        self.save_button.clicked.connect(self.save)
        self.new_button = QPushButton("Novo")
        self.new_button.clicked.connect(self.clear_form)
        self.delete_button = QPushButton("Excluir")
        self.delete_button.clicked.connect(self.delete_selected)

        brand_row = QHBoxLayout()
        brand_row.addWidget(self.brand_combo, 1)
        brand_row.addWidget(self.delete_brand_button)
        form = QFormLayout()
        form.addRow("Marca", brand_row)
        form.addRow("", self.new_brand_edit)
        form.addRow("Linha", self.line_edit)
        form.addRow("Tipo", self.type_combo)
        form.addRow("Peso do rolo (g)", self.roll_grams_edit)
        form.addRow("Preço do rolo (R$)", self.roll_price_edit)
        form.addRow("Densidade (g/cm³)", self.density_edit)
        form.addRow("Preço por kg", self.per_kg_label)
        form.addRow("", self.active_check)
        buttons = QHBoxLayout()
        for b in (self.save_button, self.new_button, self.delete_button):
            buttons.addWidget(b)
        buttons.addStretch(1)
        self.form_box = QGroupBox("Filamento")
        box_layout = QVBoxLayout(self.form_box)
        box_layout.addLayout(form)
        box_layout.addWidget(self.message_label)
        box_layout.addLayout(buttons)

        layout = QHBoxLayout(self)
        layout.addWidget(self.table, 3)
        layout.addWidget(self.form_box, 2)

        self.reload()

    # Dados
    def reload(self, select_id: int | None = None) -> None:
        self._filaments = self.catalog.list_filaments(active_only=False)
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._filaments))
        for row, f in enumerate(self._filaments):
            cells = (f.brand_name, f.line, f.type, grams(f.roll_grams),
                     brl(f.roll_price), brl(f.price_per_kg),
                     "Sim" if f.active else "Não")
            for col, text in enumerate(cells):
                self.table.setItem(row, col, QTableWidgetItem(text))
            if f.id == select_id:
                self.table.selectRow(row)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.blockSignals(False)
        self._reload_brands()

    def _reload_brands(self, select: str | None = None) -> None:
        current = select if select is not None else self.brand_combo.currentText()
        self.brand_combo.blockSignals(True)
        self.brand_combo.clear()
        self.brand_combo.addItems([b.name for b in self.catalog.list_brands()])
        self.brand_combo.addItem(NEW_BRAND)
        index = self.brand_combo.findText(current, Qt.MatchFlag.MatchFixedString)
        self.brand_combo.setCurrentIndex(index if index >= 0 else 0)
        self.brand_combo.blockSignals(False)
        self._on_brand_changed()

    def _on_brand_changed(self) -> None:
        is_new = self.brand_combo.currentText() == NEW_BRAND
        self.new_brand_edit.setVisible(is_new)
        self.delete_brand_button.setEnabled(not is_new)

    def _update_per_kg(self) -> None:
        try:
            grams_ = parse_decimal(self.roll_grams_edit.text())
            price = parse_decimal(self.roll_price_edit.text())
            if grams_ <= 0:
                raise ValueError
            derived = Filament(None, 0, "", "", "", grams_, price, None, True)
            self.per_kg_label.setText(brl(derived.price_per_kg))
        except ValueError:
            self.per_kg_label.setText("—")

    # Formulário
    def clear_form(self) -> None:
        self._editing_id = None
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.blockSignals(False)
        self.line_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.roll_grams_edit.setText("1000")
        self.roll_price_edit.clear()
        self.density_edit.clear()
        self.new_brand_edit.clear()
        self.active_check.setChecked(True)
        self.message_label.clear()
        self.form_box.setTitle("Novo filamento")

    def _on_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        f = self._filaments[rows[0].row()]
        self._editing_id = f.id
        self._reload_brands(f.brand_name)
        self.new_brand_edit.clear()
        self.line_edit.setText(f.line)
        self.type_combo.setCurrentText(f.type)
        self.roll_grams_edit.setText(str(f.roll_grams))
        self.roll_price_edit.setText(str(f.roll_price).replace(".", ","))
        self.density_edit.setText("" if f.density is None
                                  else str(f.density).replace(".", ","))
        self.active_check.setChecked(f.active)
        self.message_label.clear()
        self.form_box.setTitle("Editar filamento")

    def prefill(self, data: dict) -> None:
        """Abre o formulário de novo filamento com os dados lidos do .3mf."""
        self.clear_form()
        brand = str(data.get("brand") or "").strip()
        index = self.brand_combo.findText(brand, Qt.MatchFlag.MatchFixedString)
        if brand and index >= 0 and brand != NEW_BRAND:
            self.brand_combo.setCurrentIndex(index)
        elif brand:
            self.brand_combo.setCurrentIndex(self.brand_combo.count() - 1)
            self.new_brand_edit.setText(brand)
        if data.get("type"):
            self.type_combo.setCurrentText(str(data["type"]))
        density = _optional_decimal(data.get("density"))
        if density is not None:
            self.density_edit.setText(str(density).replace(".", ","))
        price_kg = _optional_decimal(data.get("price_per_kg"))
        if price_kg is not None:
            self.roll_price_edit.setText(f"{price_kg:.2f}".replace(".", ","))
        self.form_box.setTitle("Novo filamento (dados do arquivo)")

    def save(self) -> None:
        try:
            filament, new_brand = self._read_form()
        except ValueError as error:
            self.message_label.setText(str(error))
            return
        try:
            if new_brand is not None:
                brand_id = self.catalog.add_brand(new_brand)
            else:
                brand_id = next(b.id for b in self.catalog.list_brands()
                                if b.name == self.brand_combo.currentText())
            saved_id = self.catalog.upsert_filament(Filament(
                self._editing_id, brand_id, "", filament.line, filament.type,
                filament.roll_grams, filament.roll_price, filament.density,
                filament.active))
        except Exception as error:  # ex.: marca duplicada
            self.message_label.setText(f"Não foi possível salvar: {error}")
            return
        self.message_label.clear()
        self._editing_id = saved_id
        self.form_box.setTitle("Editar filamento")
        self._reload_brands(new_brand)
        self.reload(select_id=saved_id)
        self.catalog_changed.emit()

    def _read_form(self) -> tuple[Filament, str | None]:
        new_brand = None
        if self.brand_combo.currentText() == NEW_BRAND:
            new_brand = self.new_brand_edit.text().strip()
            if not new_brand:
                raise ValueError("Informe o nome da marca.")
            if any(b.name.lower() == new_brand.lower() for b in self.catalog.list_brands()):
                raise ValueError("Essa marca já existe: escolha-a na lista.")
        line = self.line_edit.text().strip()
        if not line:
            raise ValueError("Informe a linha do filamento (ex.: PLA Basic).")
        type_ = self.type_combo.currentText().strip().upper()
        if not type_:
            raise ValueError("Informe o tipo do filamento.")
        try:
            roll_grams = parse_decimal(self.roll_grams_edit.text())
        except ValueError:
            raise ValueError("Peso do rolo inválido.") from None
        if roll_grams <= 0:
            raise ValueError("O peso do rolo deve ser maior que zero.")
        try:
            roll_price = parse_decimal(self.roll_price_edit.text())
        except ValueError:
            raise ValueError("Preço do rolo inválido.") from None
        density = None
        if self.density_edit.text().strip():
            try:
                density = parse_decimal(self.density_edit.text())
            except ValueError:
                raise ValueError("Densidade inválida.") from None
            if density == 0:
                raise ValueError("Densidade inválida.")
        return Filament(None, 0, "", line, type_, roll_grams, roll_price, density,
                        self.active_check.isChecked()), new_brand

    def delete_brand(self) -> None:
        name = self.brand_combo.currentText()
        brand = next((b for b in self.catalog.list_brands() if b.name == name), None)
        if brand is None:
            return
        answer = QMessageBox.question(
            self, "Excluir marca", f"Excluir a marca “{name}” do catálogo?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.catalog.delete_brand(brand.id)
        except ValueError as error:  # ainda há filamentos nessa marca
            self.message_label.setText(str(error))
            return
        except Exception as error:
            self.message_label.setText(f"Não foi possível excluir: {error}")
            return
        self.message_label.clear()
        self._reload_brands()
        self.catalog_changed.emit()

    def delete_selected(self) -> None:
        if self._editing_id is None:
            self.message_label.setText("Selecione um filamento para excluir.")
            return
        answer = QMessageBox.question(
            self, "Excluir filamento", "Excluir este filamento do catálogo?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.catalog.delete_filament(self._editing_id)
        except Exception as error:
            self.message_label.setText(f"Não foi possível excluir: {error}")
            return
        self.clear_form()
        self.reload()
        self.catalog_changed.emit()
