"""Painel de resultado: custo linha por linha e as faixas de preço, ou o bloqueio."""
from collections.abc import Sequence
from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from calculadora3d.core.pricing import CostBreakdown, PriceTier
from calculadora3d.ui.formatting import brl

BLOCKED_STYLE = ("background-color: #fff3b0; color: #4a3b00; padding: 8px;"
                 " border-radius: 3px; font-weight: bold;")
COST_LINES = (
    ("material", "Material"),
    ("energy", "Energia"),
    ("failure", "Falha"),
    ("labor", "Mão de obra"),
    ("extras", "Extras"),
    ("total", "Total"),
)
RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


def _percent(fraction: Decimal) -> str:
    return f"{(fraction * 100).normalize():f}".replace(".", ",") + "%"


def _copies_text(copies: int) -> str:
    return "1 cópia" if copies == 1 else f"{copies} cópias"


class CostPanel(QWidget):
    action_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(BLOCKED_STYLE)
        self.action_button = QPushButton()
        self.action_button.clicked.connect(self.action_requested.emit)

        self.result_widget = QWidget()
        result = QVBoxLayout(self.result_widget)
        result.setContentsMargins(0, 0, 0, 0)

        self.cost_title = QLabel()
        self.cost_title.setStyleSheet("font-weight: bold;")
        cost_grid = QGridLayout()
        self._cost_values: dict[str, QLabel] = {}
        for row, (field, title) in enumerate(COST_LINES):
            name = QLabel(title)
            value = QLabel()
            value.setAlignment(RIGHT)
            if field == "total":
                name.setStyleSheet("font-weight: bold;")
                value.setStyleSheet("font-weight: bold;")
            cost_grid.addWidget(name, row, 0)
            cost_grid.addWidget(value, row, 1)
            self._cost_values[field] = value
        cost_grid.setColumnStretch(0, 1)

        prices_title = QLabel("Preço sugerido")
        prices_title.setStyleSheet("font-weight: bold;")
        self._tiers_grid = QGridLayout()
        self._tiers_grid.setColumnStretch(0, 1)

        result.addWidget(self.cost_title)
        result.addLayout(cost_grid)
        result.addSpacing(8)
        result.addWidget(prices_title)
        result.addLayout(self._tiers_grid)

        box = QGroupBox("Resultado")
        inner = QVBoxLayout(box)
        inner.addWidget(self.message_label)
        inner.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignLeft)
        inner.addWidget(self.result_widget)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(box)
        self.clear()

    # API pública
    def show_result(self, breakdown: CostBreakdown, tiers: Sequence[PriceTier],
                    copies: int) -> None:
        self.message_label.hide()
        self.action_button.hide()
        self.cost_title.setText(f"Custo de produção ({_copies_text(copies)})")
        for field, label in self._cost_values.items():
            label.setText(brl(getattr(breakdown, field)))
        self._clear_tiers()
        headers = ("Faixa", "Por unidade", f"Total ({_copies_text(copies)})")
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setStyleSheet("color: gray;")
            if col:
                label.setAlignment(RIGHT)
            self._tiers_grid.addWidget(label, 0, col)
        for row, tier in enumerate(tiers, start=1):
            name = f"{tier.name} (margem {_percent(tier.margin)})"
            if tier.min_quantity is not None:
                name += f" — a partir de {tier.min_quantity} un."
            unit = QLabel(brl(tier.unit))
            unit.setAlignment(RIGHT)
            unit.setStyleSheet("font-weight: bold;")
            total = QLabel(brl(tier.total))
            total.setAlignment(RIGHT)
            self._tiers_grid.addWidget(QLabel(name), row, 0)
            self._tiers_grid.addWidget(unit, row, 1)
            self._tiers_grid.addWidget(total, row, 2)
        self.result_widget.show()
        self.show()

    def show_blocked(self, reason: str, action: str | None = None) -> None:
        """Mostra só o aviso: nenhum valor de custo ou preço fica na tela."""
        self._wipe_values()
        self.result_widget.hide()
        self.message_label.setText(reason)
        self.message_label.show()
        self.action_button.setText(action or "")
        self.action_button.setVisible(action is not None)
        self.show()

    def clear(self) -> None:
        self._wipe_values()
        self.result_widget.hide()
        self.message_label.hide()
        self.action_button.hide()
        self.hide()

    # Interno
    def _wipe_values(self) -> None:
        self.cost_title.clear()
        for label in self._cost_values.values():
            label.clear()
        self._clear_tiers()

    def _clear_tiers(self) -> None:
        grid = self._tiers_grid
        while grid.count():
            widget = grid.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
