"""Tabela de slots do .3mf com a escolha do filamento do catálogo."""
from collections.abc import Mapping, Sequence
from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import Filament
from calculadora3d.core.matching import Confidence, match_slot
from calculadora3d.core.models import FilamentUsage
from calculadora3d.ui.formatting import grams

NO_FILAMENT = "— escolher —"
PURGE_TEXT = "peso inclui a purga das trocas de cor"
REGISTER_TEXT = "cadastrar este filamento"
HIGHLIGHT = "#fff3b0"
PRESELECTED = (Confidence.HIGH, Confidence.MEDIUM)

COL_SLOT, COL_COLOR, COL_TYPE, COL_GRAMS, COL_FILAMENT, COL_ACTION = range(6)
HEADERS = ("Slot", "Cor", "Tipo", "Gramas", "Filamento", "")


def _qt_color(text: str) -> QColor:
    # O Bambu grava #RRGGBBAA; o Qt leria isso como #AARRGGBB.
    text = (text or "").strip()
    if len(text) == 9 and text.startswith("#"):
        text = text[:7]
    return QColor(text)


def filament_label(f: Filament) -> str:
    return f"{f.brand_name} {f.line} ({f.type})"


class SlotTable(QWidget):
    changed = Signal()
    register_requested = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._usage: tuple[FilamentUsage, ...] = ()
        self._filaments: list[Filament] = []
        self._combos: dict[int, QComboBox] = {}
        self._buttons: dict[int, QPushButton] = {}
        self._rows: dict[int, int] = {}
        # Escolhas feitas à mão, por slot: id do filamento ou None (apagada).
        self._overrides: dict[int, int | None] = {}

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header = self.table.horizontalHeader()
        for col in (COL_SLOT, COL_COLOR, COL_TYPE, COL_GRAMS, COL_ACTION):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_FILAMENT, QHeaderView.ResizeMode.Stretch)

        self.purge_label = QLabel(PURGE_TEXT)
        self.purge_label.setStyleSheet("font-style: italic;")

        box = QGroupBox("Filamentos por slot")
        inner = QVBoxLayout(box)
        inner.addWidget(self.table)
        inner.addWidget(self.purge_label)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(box)
        self.set_slots((), ())

    # API pública
    def set_slots(self, usage: Sequence[FilamentUsage],
                  filaments: Sequence[Filament]) -> None:
        """Reconstrói a tabela; escolhas manuais por slot sobrevivem se ainda válidas."""
        self._usage = tuple(usage)
        self._filaments = list(filaments)
        ids = {f.id for f in self._filaments}
        self._combos = {}
        self._buttons = {}
        self._rows = {}
        self.table.setRowCount(0)
        self.table.setRowCount(len(self._usage))
        for row, u in enumerate(self._usage):
            self._rows[u.slot] = row
            self.table.setItem(row, COL_SLOT, self._item(str(u.slot)))
            self.table.setItem(row, COL_COLOR, self._color_item(u.color))
            self.table.setItem(row, COL_TYPE, self._item(u.type or "—"))
            self.table.setItem(row, COL_GRAMS, self._item(grams(u.grams)))
            self.table.setItem(row, COL_FILAMENT, QTableWidgetItem())
            self.table.setItem(row, COL_ACTION, QTableWidgetItem())

            combo = QComboBox()
            combo.addItem(NO_FILAMENT, None)
            for f in self._filaments:
                combo.addItem(filament_label(f), f.id)
            override = self._overrides.get(u.slot, ...)
            if override is not ... and (override is None or override in ids):
                wanted = override
            else:
                match = match_slot(u, self._filaments)
                wanted = (match.filament.id if match.confidence in PRESELECTED
                          else None)
            combo.setCurrentIndex(0 if wanted is None else max(combo.findData(wanted), 0))
            combo.currentIndexChanged.connect(
                lambda _i, slot=u.slot: self._on_choice(slot))
            self.table.setCellWidget(row, COL_FILAMENT, combo)
            self._combos[u.slot] = combo

            button = QPushButton(REGISTER_TEXT)
            button.clicked.connect(lambda _c=False, usage=u: self._request_register(usage))
            # A view reexibe os cell widgets; o botão vai num contêiner para poder sumir.
            holder = QWidget()
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.addWidget(button)
            self.table.setCellWidget(row, COL_ACTION, holder)
            self._buttons[u.slot] = button
            self._update_row(u.slot)
        self.purge_label.setVisible(len(self._usage) > 1)
        self._fit_height()

    def set_grams(self, values: Mapping[int, Decimal]) -> None:
        for slot, row in self._rows.items():
            item = self.table.item(row, COL_GRAMS)
            item.setText(grams(values.get(slot, Decimal(0))))

    def selected_filaments(self) -> dict[int, Filament | None]:
        by_id = {f.id: f for f in self._filaments}
        return {slot: by_id.get(combo.currentData())
                for slot, combo in self._combos.items()}

    def reset_choices(self) -> None:
        self._overrides = {}

    def set_choices(self, choices: Mapping[int, int | None]) -> None:
        """Fixa a escolha por slot (id do filamento ou None) para o próximo set_slots."""
        self._overrides = dict(choices)

    # Interno
    @staticmethod
    def _item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _color_item(self, color: str) -> QTableWidgetItem:
        item = self._item(color or "—")
        qcolor = _qt_color(color)
        if qcolor.isValid():
            item.setBackground(QBrush(qcolor))
            item.setForeground(QBrush(QColor("black" if qcolor.lightness() > 127
                                                else "white")))
        return item

    def _on_choice(self, slot: int) -> None:
        self._overrides[slot] = self._combos[slot].currentData()
        self._update_row(slot)
        self.changed.emit()

    def _update_row(self, slot: int) -> None:
        missing = self._combos[slot].currentData() is None
        self._buttons[slot].setVisible(missing)
        self.table.setColumnHidden(COL_ACTION, not any(
            c.currentData() is None for c in self._combos.values()))
        row = self._rows[slot]
        brush = QBrush(QColor(HIGHLIGHT)) if missing else QBrush()
        for col in (COL_SLOT, COL_TYPE, COL_GRAMS, COL_FILAMENT, COL_ACTION):
            self.table.item(row, col).setBackground(brush)
        self._combos[slot].setStyleSheet(
            f"QComboBox {{ background-color: {HIGHLIGHT}; color: #4a3b00; }}"
            if missing else "")

    def _request_register(self, usage: FilamentUsage) -> None:
        self.register_requested.emit({
            "type": usage.type,
            "brand": usage.vendor,
            "density": usage.density,
            "price_per_kg": usage.cost_per_kg,
            "color": usage.color,
        })

    def _fit_height(self) -> None:
        self.table.resizeRowsToContents()
        header = self.table.horizontalHeader().sizeHint().height()
        rows = self.table.verticalHeader().length()
        frame = 2 * self.table.frameWidth()
        self.table.setFixedHeight(header + rows + frame + 2)
