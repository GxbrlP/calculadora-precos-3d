"""Tarefas de acabamento (minutos de mão de obra) e materiais extras em R$."""
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from PySide6.QtCore import QLocale, Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import TaskPreset
from calculadora3d.core.pricing import FinishingTask

PT_BR = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
CENTS = Decimal("0.01")


def _minutes_spin(value: int = 0) -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(0, 100000)
    spin.setSuffix(" min")
    spin.setValue(value)
    return spin


class TaskList(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._presets: list[TaskPreset] = []
        self._rows: list[tuple[QWidget, str, QSpinBox]] = []

        self.preset_combo = QComboBox()
        self.add_preset_button = QPushButton("Adicionar")
        self.add_preset_button.clicked.connect(self._add_from_preset)
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Predefinida"))
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(self.add_preset_button)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nome da tarefa")
        self.name_edit.textChanged.connect(self._update_free_button)
        self.name_edit.returnPressed.connect(self._add_free)
        self.minutes_edit = _minutes_spin()
        self.add_free_button = QPushButton("Adicionar")
        self.add_free_button.clicked.connect(self._add_free)
        free_row = QHBoxLayout()
        free_row.addWidget(QLabel("Livre"))
        free_row.addWidget(self.name_edit, 1)
        free_row.addWidget(self.minutes_edit)
        free_row.addWidget(self.add_free_button)

        self._rows_layout = QVBoxLayout()
        self._empty_label = QLabel("Nenhuma tarefa adicionada.")
        self._empty_label.setStyleSheet("color: gray;")

        self.extras_spin = QDoubleSpinBox()
        self.extras_spin.setLocale(PT_BR)
        self.extras_spin.setDecimals(2)
        self.extras_spin.setRange(0, 1_000_000)
        self.extras_spin.setPrefix("R$ ")
        self.extras_spin.valueChanged.connect(lambda _v: self.changed.emit())
        extras_form = QFormLayout()
        extras_form.addRow("Materiais extras (R$)", self.extras_spin)

        box = self.box = QGroupBox()
        inner = QVBoxLayout(box)
        inner.addLayout(preset_row)
        inner.addLayout(free_row)
        inner.addWidget(self._empty_label)
        inner.addLayout(self._rows_layout)
        inner.addLayout(extras_form)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(box)

        self.set_presets(())
        self.set_copies(1)
        self._update_free_button()

    # API pública
    def set_presets(self, presets: Sequence[TaskPreset]) -> None:
        self._presets = list(presets)
        self.preset_combo.clear()
        for preset in self._presets:
            self.preset_combo.addItem(f"{preset.name} ({preset.minutes} min)")
        if not self._presets:
            self.preset_combo.addItem("Nenhuma cadastrada")
        self.preset_combo.setEnabled(bool(self._presets))
        self.add_preset_button.setEnabled(bool(self._presets))

    def set_copies(self, copies: int) -> None:
        """Tarefas e materiais extras valem uma vez para o lote inteiro."""
        copies_text = "1 produto" if copies == 1 else f"{copies} produtos"
        self.box.setTitle(f"Acabamento — para o lote inteiro ({copies_text})")

    def tasks(self) -> tuple[FinishingTask, ...]:
        return tuple(FinishingTask(name, spin.value()) for _w, name, spin in self._rows)

    def extra_materials(self) -> Decimal:
        return Decimal(str(self.extras_spin.value())).quantize(CENTS, rounding=ROUND_HALF_UP)

    def add_task(self, name: str, minutes: int) -> None:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        spin = _minutes_spin(minutes)
        spin.valueChanged.connect(lambda _v: self.changed.emit())
        remove = QPushButton("Remover")
        h.addWidget(QLabel(name), 1)
        h.addWidget(spin)
        h.addWidget(remove)
        entry = (row, name, spin)
        remove.clicked.connect(lambda _c=False: self._remove(entry))
        self._rows.append(entry)
        self._rows_layout.addWidget(row)
        self._empty_label.setVisible(False)
        self.changed.emit()

    def clear(self) -> None:
        for row, _name, _spin in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows = []
        self._empty_label.setVisible(True)
        self.extras_spin.blockSignals(True)
        self.extras_spin.setValue(0)
        self.extras_spin.blockSignals(False)
        self.changed.emit()

    # Interno
    def _add_from_preset(self) -> None:
        index = self.preset_combo.currentIndex()
        if 0 <= index < len(self._presets):
            preset = self._presets[index]
            self.add_task(preset.name, preset.minutes)

    def _add_free(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            return
        self.add_task(name, self.minutes_edit.value())
        self.name_edit.clear()
        self.minutes_edit.setValue(0)

    def _update_free_button(self) -> None:
        self.add_free_button.setEnabled(bool(self.name_edit.text().strip()))

    def _remove(self, entry: tuple[QWidget, str, QSpinBox]) -> None:
        self._rows.remove(entry)
        row = entry[0]
        row.setParent(None)
        row.deleteLater()
        self._empty_label.setVisible(not self._rows)
        self.changed.emit()
