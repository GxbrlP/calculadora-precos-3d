"""Página Configurações: custos, margens, arredondamento e presets de tarefas."""
from decimal import Decimal

from PySide6.QtCore import QLocale, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import Catalog, Settings, TaskPreset

PT_BR = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
HUNDRED = Decimal(100)


def _money_spin(maximum: float = 1_000_000) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setLocale(PT_BR)
    spin.setDecimals(2)
    spin.setRange(0, maximum)
    spin.setPrefix("R$ ")
    return spin


def _percent_spin() -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setLocale(PT_BR)
    spin.setDecimals(1)
    spin.setRange(0, 99.9)
    spin.setSuffix(" %")
    return spin


def _money(spin: QDoubleSpinBox) -> Decimal:
    return Decimal(str(round(spin.value(), 2)))


def _fraction(spin: QDoubleSpinBox) -> Decimal:
    return Decimal(str(round(spin.value(), 1))) / HUNDRED


def _to_percent(fraction: Decimal) -> float:
    return float(fraction * HUNDRED)


class SettingsPage(QWidget):
    settings_changed = Signal()

    def __init__(self, catalog: Catalog, parent=None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self._presets: list[TaskPreset] = []
        self._editing_id: int | None = None

        self.kwh_spin = _money_spin()
        self.kwh_spin.setSuffix(" /kWh")
        self.failure_spin = _percent_spin()
        self.labor_spin = _money_spin()
        self.labor_spin.setSuffix(" /h")
        self.packaging_spin = _money_spin()
        self.retail_spin = _percent_spin()
        self.wholesale_spin = _percent_spin()
        self.minimum_spin = _percent_spin()
        self.wholesale_qty_spin = QSpinBox()
        self.wholesale_qty_spin.setRange(1, 1_000_000)
        self.wholesale_qty_spin.setSuffix(" un.")
        self.rounding_spin = _money_spin()
        rounding_hint = QLabel(
            "Preço por unidade arredondado para cima em múltiplos deste valor; "
            "0 = sem arredondamento.")
        rounding_hint.setStyleSheet("color: gray;")
        rounding_hint.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Tarifa de energia", self.kwh_spin)
        form.addRow("Taxa de falha", self.failure_spin)
        form.addRow("Mão de obra", self.labor_spin)
        form.addRow("Embalagem padrão (por lote/orçamento)", self.packaging_spin)
        form.addRow("Margem de varejo", self.retail_spin)
        form.addRow("Margem de atacado", self.wholesale_spin)
        form.addRow("Margem mínima", self.minimum_spin)
        form.addRow("Atacado a partir de", self.wholesale_qty_spin)
        form.addRow("Passo de arredondamento", self.rounding_spin)
        form.addRow("", rounding_hint)
        self.save_button = QPushButton("Salvar")
        self.save_button.clicked.connect(self.save)
        self.status_label = QLabel()
        buttons = QHBoxLayout()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.status_label, 1)
        general_box = QGroupBox("Custos e preços")
        general_layout = QVBoxLayout(general_box)
        general_layout.addLayout(form)
        general_layout.addLayout(buttons)
        general_layout.addStretch(1)

        self.preset_table = QTableWidget(0, 2)
        self.preset_table.setHorizontalHeaderLabels(("Tarefa", "Minutos"))
        self.preset_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preset_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.preset_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection)
        self.preset_table.verticalHeader().setVisible(False)
        self.preset_table.horizontalHeader().setStretchLastSection(True)
        self.preset_table.itemSelectionChanged.connect(self._on_preset_selected)

        self.preset_name_edit = QLineEdit()
        self.preset_name_edit.setPlaceholderText("ex.: Lixar")
        self.preset_minutes_spin = QSpinBox()
        self.preset_minutes_spin.setRange(1, 100000)
        self.preset_minutes_spin.setSuffix(" min")
        self.preset_message = QLabel()
        self.preset_message.setStyleSheet("color: #b00020;")
        self.preset_message.setWordWrap(True)
        self.preset_save_button = QPushButton("Salvar tarefa")
        self.preset_save_button.clicked.connect(self.save_preset)
        self.preset_new_button = QPushButton("Nova")
        self.preset_new_button.clicked.connect(self.clear_preset_form)
        self.preset_delete_button = QPushButton("Excluir")
        self.preset_delete_button.clicked.connect(self.delete_preset)

        preset_form = QFormLayout()
        preset_form.addRow("Nome", self.preset_name_edit)
        preset_form.addRow("Minutos padrão", self.preset_minutes_spin)
        preset_buttons = QHBoxLayout()
        for b in (self.preset_save_button, self.preset_new_button,
                  self.preset_delete_button):
            preset_buttons.addWidget(b)
        preset_buttons.addStretch(1)
        self.preset_box = QGroupBox("Tarefas de acabamento")
        preset_layout = QVBoxLayout(self.preset_box)
        preset_layout.addWidget(self.preset_table)
        preset_layout.addLayout(preset_form)
        preset_layout.addWidget(self.preset_message)
        preset_layout.addLayout(preset_buttons)

        layout = QHBoxLayout(self)
        layout.addWidget(general_box, 1)
        layout.addWidget(self.preset_box, 1)

        self.load_form()
        self.reload_presets()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.load_form()

    def load_form(self) -> None:
        s = self.catalog.get_settings()
        self.kwh_spin.setValue(float(s.kwh_price))
        self.failure_spin.setValue(_to_percent(s.failure_rate))
        self.labor_spin.setValue(float(s.labor_hourly))
        self.packaging_spin.setValue(float(s.packaging))
        self.retail_spin.setValue(_to_percent(s.retail_margin))
        self.wholesale_spin.setValue(_to_percent(s.wholesale_margin))
        self.minimum_spin.setValue(_to_percent(s.minimum_margin))
        self.wholesale_qty_spin.setValue(s.wholesale_min_quantity)
        self.rounding_spin.setValue(float(s.rounding_step))

    def current_settings(self) -> Settings:
        return Settings(
            kwh_price=_money(self.kwh_spin),
            failure_rate=_fraction(self.failure_spin),
            labor_hourly=_money(self.labor_spin),
            packaging=_money(self.packaging_spin),
            retail_margin=_fraction(self.retail_spin),
            wholesale_margin=_fraction(self.wholesale_spin),
            wholesale_min_quantity=self.wholesale_qty_spin.value(),
            minimum_margin=_fraction(self.minimum_spin),
            rounding_step=_money(self.rounding_spin))

    def save(self) -> None:
        try:
            self.catalog.save_settings(self.current_settings())
        except ValueError as error:
            QMessageBox.warning(self, "Configurações inválidas", str(error))
            return
        self.load_form()
        self.status_label.setText("Configurações salvas.")
        self.settings_changed.emit()

    # Presets de tarefa
    def reload_presets(self, select_id: int | None = None) -> None:
        self._presets = self.catalog.list_task_presets()
        self.preset_table.blockSignals(True)
        self.preset_table.setRowCount(len(self._presets))
        for row, p in enumerate(self._presets):
            self.preset_table.setItem(row, 0, QTableWidgetItem(p.name))
            self.preset_table.setItem(row, 1, QTableWidgetItem(f"{p.minutes} min"))
            if p.id == select_id:
                self.preset_table.selectRow(row)
        self.preset_table.blockSignals(False)

    def clear_preset_form(self) -> None:
        self._editing_id = None
        self.preset_table.blockSignals(True)
        self.preset_table.clearSelection()
        self.preset_table.blockSignals(False)
        self.preset_name_edit.clear()
        self.preset_minutes_spin.setValue(self.preset_minutes_spin.minimum())
        self.preset_message.clear()

    def _on_preset_selected(self) -> None:
        rows = self.preset_table.selectionModel().selectedRows()
        if not rows:
            return
        preset = self._presets[rows[0].row()]
        self._editing_id = preset.id
        self.preset_name_edit.setText(preset.name)
        self.preset_minutes_spin.setValue(preset.minutes)
        self.preset_message.clear()

    def save_preset(self) -> None:
        name = self.preset_name_edit.text().strip()
        if not name:
            self.preset_message.setText("Informe o nome da tarefa.")
            return
        saved_id = self.catalog.upsert_task_preset(
            TaskPreset(self._editing_id, name, self.preset_minutes_spin.value()))
        self.preset_message.clear()
        self._editing_id = saved_id
        self.reload_presets(select_id=saved_id)
        self.settings_changed.emit()

    def delete_preset(self) -> None:
        if self._editing_id is None:
            self.preset_message.setText("Selecione uma tarefa para excluir.")
            return
        answer = QMessageBox.question(
            self, "Excluir tarefa", "Excluir esta tarefa predefinida?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.catalog.delete_task_preset(self._editing_id)
        self.clear_preset_form()
        self.reload_presets()
        self.settings_changed.emit()
