"""Resultado do pedido: uma linha por produto e a linha Pedido, ou o bloqueio."""
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QGroupBox, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from calculadora3d.core.export import price_options
from calculadora3d.core.quotes import order_totals
from calculadora3d.ui.formatting import brl
from calculadora3d.ui.widgets.product_panel import Blocked

# Sem cor própria: segue o tema do sistema (claro ou escuro).
BLOCKED_STYLE = "padding: 8px 0; font-weight: bold;"
DEFAULT_TIERS = ("Varejo", "Atacado", "Mínimo")
ORDER_ROW = "Pedido"
DASH = "—"
RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


@dataclass(frozen=True)
class ResultRow:
    name: str
    copies: int
    outcome: dict | Blocked


class OrderResult(QWidget):
    action_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(BLOCKED_STYLE)
        self.action_button = QPushButton()
        self.action_button.clicked.connect(self.action_requested.emit)

        self.table = QTableWidget(0, 0)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setWordWrap(True)

        box = QGroupBox("Resultado")
        inner = QVBoxLayout(box)
        inner.addWidget(self.message_label)
        inner.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignLeft)
        inner.addWidget(self.table)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(box)
        self.clear()

    # API pública
    def show_rows(self, rows: Sequence[ResultRow]) -> None:
        priced = [r.outcome for r in rows if not isinstance(r.outcome, Blocked)]
        tier_names = ([str(t["name"]) for t in priced[0].get("tiers", [])]
                      if priced else list(DEFAULT_TIERS))
        headers = ["Produto", "Qt.", "Custo"] + [f"{name} (un.)" for name in tier_names]
        table = self.table
        table.clearSpans()
        table.clearContents()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        all_priced = bool(rows) and len(priced) == len(rows)
        table.setRowCount(len(rows) + (1 if all_priced else 0))
        for row, result in enumerate(rows):
            table.setItem(row, 0, self._item(result.name, LEFT))
            table.setItem(row, 1, self._item(str(result.copies)))
            outcome = result.outcome
            if isinstance(outcome, Blocked):
                table.setItem(row, 2, self._item(outcome.reason, LEFT, bold=True))
                table.setSpan(row, 2, 1, len(headers) - 2)
                continue
            table.setItem(row, 2, self._item(brl(Decimal(str(outcome["breakdown"]["total"])))))
            units = {o.name: o.unit for o in price_options(outcome)}
            for col, name in enumerate(tier_names, start=3):
                unit = units.get(name)
                table.setItem(row, col, self._item(DASH if unit is None else brl(unit)))
        if all_priced:
            totals = order_totals(priced)
            last = len(rows)
            table.setItem(last, 0, self._item(ORDER_ROW, LEFT, bold=True))
            table.setItem(last, 1, self._item(str(totals.quantity), bold=True))
            table.setItem(last, 2, self._item(brl(totals.cost), bold=True))
            for col, name in enumerate(tier_names, start=3):
                value = totals.tiers.get(name)
                table.setItem(last, col, self._item(
                    DASH if value is None else brl(value), bold=True))
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(headers)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.message_label.hide()
        self.action_button.hide()
        table.show()
        self._fit_height()
        self.show()

    def show_blocked(self, reason: str, action: str | None = None) -> None:
        """Mostra só o aviso: nenhum valor de custo ou preço fica na tela."""
        self._wipe()
        self.table.hide()
        self.message_label.setText(reason)
        self.message_label.show()
        self.action_button.setText(action or "")
        self.action_button.setVisible(action is not None)
        self.show()

    def clear(self) -> None:
        self._wipe()
        self.table.hide()
        self.message_label.hide()
        self.action_button.hide()
        self.hide()

    # Interno
    def _wipe(self) -> None:
        self.table.clearSpans()
        self.table.setRowCount(0)

    @staticmethod
    def _item(text: str, align=RIGHT, *, bold: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        if bold:
            font = QFont(item.font())
            font.setBold(True)
            item.setFont(font)
        return item

    def _fit_height(self) -> None:
        self.table.resizeRowsToContents()
        header = self.table.horizontalHeader().sizeHint().height()
        rows = self.table.verticalHeader().length()
        frame = 2 * self.table.frameWidth()
        self.table.setFixedHeight(header + rows + frame + 2)
