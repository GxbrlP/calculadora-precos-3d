"""Painel de um produto: um arquivo, sua impressora, filamentos, acabamento e custo."""
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import (
    Catalog, Filament, Printer, Settings, TaskPreset, printer_for_model,
)
from calculadora3d.core.models import SlicedProject
from calculadora3d.core.pricing import (
    FinishingTask, PricingError, PricingInputs, TierConfig, compute_cost,
    suggest_prices,
)
from calculadora3d.core.quotes import build_product, snapshot_project
from calculadora3d.ui.formatting import brl, duration, grams
from calculadora3d.ui.widgets.slot_table import SlotTable, filament_label
from calculadora3d.ui.widgets.task_list import TaskList

NO_PRINTER = "— escolher —"
UNSLICED_TEXT = "Este arquivo não foi salvo depois de fatiar"
WARNING_STYLE = "background-color: #fff3b0; color: #4a3b00; padding: 4px; border-radius: 3px;"
# Sem cor própria: segue o tema do sistema (claro ou escuro).
BLOCKED_STYLE = "font-weight: bold;"
COPIES_TOOLTIP = "Quantos produtos vendáveis saem desta impressão; o custo é dividido entre eles"

CHOOSE_PRINTER_TEXT = "Escolha a impressora"
CHOOSE_FILAMENTS_TEXT = "Escolha o filamento de todos os slots"
MANUAL_INPUT_TEXT = "Informe o peso e o tempo de impressão"
SLICED_NO_DATA_TEXT = "O arquivo fatiado não traz peso ou tempo — confira o .3mf"
UNEXPECTED_ERROR_TEXT = "Não foi possível calcular o preço"


@dataclass(frozen=True)
class CatalogView:
    """Retrato do catálogo usado por todos os painéis num mesmo momento."""
    filaments: tuple[Filament, ...]
    printers: tuple[Printer, ...]
    settings: Settings
    presets: tuple[TaskPreset, ...]

    @classmethod
    def load(cls, catalog: Catalog) -> "CatalogView":
        return cls(tuple(catalog.list_filaments()), tuple(catalog.list_printers()),
                   catalog.get_settings(), tuple(catalog.list_task_presets()))

    @property
    def ready(self) -> bool:
        return bool(self.filaments) and bool(self.printers)


@dataclass(frozen=True)
class Blocked:
    """O produto não pode ser precificado agora; reason diz por quê."""
    reason: str


def tier_configs(settings: Settings) -> tuple[TierConfig, ...]:
    return (
        TierConfig("Varejo", settings.retail_margin, None),
        TierConfig("Atacado", settings.wholesale_margin, settings.wholesale_min_quantity),
        TierConfig("Mínimo", settings.minimum_margin, None),
    )


def build_pricing_inputs(filaments: Mapping[int, Filament], grams_by_slot: Mapping[int, Decimal],
                         seconds: int, copies: int, printer: Printer, settings: Settings,
                         tasks: Sequence[FinishingTask],
                         extra_materials: Decimal) -> PricingInputs:
    """Só monta as entradas; toda conta de custo fica em core.pricing."""
    lines = tuple(
        filament.as_filament_line(grams_by_slot[slot])
        for slot, filament in sorted(filaments.items())
        if grams_by_slot.get(slot, Decimal(0)) > 0
    )
    return PricingInputs(
        filaments=lines, seconds=seconds, copies=copies,
        printer=printer.as_printer_costs(), kwh_price=settings.kwh_price,
        failure_rate=settings.failure_rate, labor_hourly=settings.labor_hourly,
        tasks=tuple(tasks), extra_materials=extra_materials,
        packaging=settings.packaging,
    )


def _cost_line(breakdown: dict) -> str:
    def money(key: str) -> str:
        return brl(Decimal(str(breakdown[key])))
    return (f"Custo: material {money('material')} · energia {money('energy')}"
            f" · falha {money('failure')} · mão de obra {money('labor')}"
            f" · extras {money('extras')} = {money('total')}")


class ProductPanel(QWidget):
    changed = Signal()
    remove_requested = Signal()
    register_filament_requested = Signal(dict)

    def __init__(self, project: SlicedProject, view: CatalogView, *,
                 path: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.path = path
        self.project = project
        self._view = view
        self._saved: dict | None = None  # produto de origem (Duplicar)
        self._chosen_printer_id: int | None = None
        self._weight_boxes: dict[int, QDoubleSpinBox] = {}
        self.hours_spin: QSpinBox | None = None
        self.minutes_spin: QSpinBox | None = None
        self._outcome: dict | Blocked = Blocked(CHOOSE_PRINTER_TEXT)
        self._loading = True

        self.box = QGroupBox(self.title())
        self.remove_button = QPushButton("Remover")
        self.remove_button.clicked.connect(self.remove_requested.emit)

        self.printer_combo = QComboBox()
        self._detected_label = QLabel()
        printer_row = QHBoxLayout()
        printer_row.addWidget(self.printer_combo, 1)
        printer_row.addWidget(self._detected_label)
        self.printer_combo.currentIndexChanged.connect(self._on_printer_changed)

        self.copies_spin = QSpinBox()
        self.copies_spin.setMinimum(1)
        self.copies_spin.setMaximum(100000)
        self.copies_spin.setToolTip(COPIES_TOOLTIP)
        self.copies_spin.setValue(project.copies)
        self.copies_spin.valueChanged.connect(self._on_copies_changed)

        sliced = project.is_sliced
        form = QFormLayout()
        form.addRow("Projeto", QLabel(project.name))
        form.addRow("Impressora", printer_row)
        form.addRow("Placas", QLabel(
            str(len([p for p in project.plates if not p.skipped])) if sliced else "—"))
        form.addRow("Tempo", QLabel(duration(project.total_seconds) if sliced else "—"))
        form.addRow("Peso", QLabel(grams(project.total_grams) if sliced else "—"))
        form.addRow("Produtos", self.copies_spin)

        self.slot_table = SlotTable()
        self.slot_table.changed.connect(self._recalculate)
        self.slot_table.register_requested.connect(self.register_filament_requested.emit)
        self.task_list = TaskList()
        self.task_list.changed.connect(self._recalculate)
        self.task_list.set_copies(self.copies())

        self.cost_label = QLabel()
        self.cost_label.setWordWrap(True)

        header = QHBoxLayout()
        header.addStretch(1)
        header.addWidget(self.remove_button)
        inner = QVBoxLayout(self.box)
        inner.addLayout(header)
        inner.addLayout(form)
        if not sliced:
            unsliced = QLabel(UNSLICED_TEXT)
            unsliced.setStyleSheet("font-weight: bold;")
            inner.addWidget(unsliced)
            inner.addWidget(self._build_manual())
        for text in project.warnings:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(WARNING_STYLE)
            inner.addWidget(label)
        inner.addWidget(self.slot_table)
        inner.addWidget(self.task_list)
        inner.addWidget(self.cost_label)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.box)

        self._apply_view()
        self._loading = False
        self._recalculate()

    @classmethod
    def from_product(cls, product: dict, view: CatalogView, parent=None) -> "ProductPanel":
        """Reconstrói um produto salvo e o recalcula com o catálogo atual."""
        panel = cls(snapshot_project(product), view, parent=parent)
        panel._loading = True
        panel._saved = product
        panel.box.setTitle(panel.title())
        known = {f.id for f in view.filaments}
        panel.slot_table.set_choices({
            int(row["slot"]): row.get("filament_id") if row.get("filament_id") in known else None
            for row in product["usage"]})
        panel._chosen_printer_id = product.get("printer_id")
        for task in product.get("tasks", []):
            panel.task_list.add_task(task["name"], int(task["minutes"]))
        panel.task_list.extras_spin.setValue(
            float(Decimal(str(product.get("extra_materials", "0")))))
        panel._apply_view()
        panel._loading = False
        panel._recalculate()
        return panel

    # API pública
    def title(self) -> str:
        if self.path is not None:
            return f"Arquivo ({self.path.name})"
        saved = self._saved or {}
        return f"Arquivo ({saved.get('source_file') or saved.get('project_name') or self.project.name})"

    def copies(self) -> int:
        return self.copies_spin.value()

    def effective_seconds(self) -> int:
        if self.project.is_sliced:
            return self.project.total_seconds
        if self.hours_spin is None:
            return 0
        return self.hours_spin.value() * 3600 + self.minutes_spin.value() * 60

    def effective_grams(self) -> dict[int, Decimal]:
        if self.project.is_sliced:
            return {u.slot: u.grams for u in self.project.usage}
        return {slot: Decimal(str(round(box.value(), 2)))
                for slot, box in self._weight_boxes.items()}

    def refresh_catalog(self, view: CatalogView) -> None:
        self._view = view
        self._loading = True
        self._apply_view()
        self._loading = False
        self._recalculate()

    def outcome(self) -> dict | Blocked:
        return self._outcome

    def selected_printer(self) -> Printer | None:
        index = self.printer_combo.currentIndex()
        printers = self._view.printers
        if index <= 0 or index > len(printers):
            return None
        return printers[index - 1]

    # Interno
    def _build_manual(self) -> QWidget:
        box = QWidget()
        form = QFormLayout(box)
        form.setContentsMargins(0, 0, 0, 0)
        for usage in self.project.usage:
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(0, 100000)
            spin.setSuffix(" g")
            spin.valueChanged.connect(lambda _v: self._recalculate())
            self._weight_boxes[usage.slot] = spin
            label = f"Peso do slot {usage.slot}"
            if usage.type:
                label += f" ({usage.type})"
            form.addRow(label, spin)
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 9999)
        self.hours_spin.setSuffix(" h")
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setSuffix(" min")
        for spin in (self.hours_spin, self.minutes_spin):
            spin.valueChanged.connect(lambda _v: self._recalculate())
        time_row = QWidget()
        row = QHBoxLayout(time_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.hours_spin)
        row.addWidget(self.minutes_spin)
        row.addStretch(1)
        form.addRow("Tempo", time_row)
        return box

    def _apply_view(self) -> None:
        """Recarrega impressoras, slots e presets mantendo as escolhas ainda válidas."""
        view = self._view
        self._reload_printers()
        self.slot_table.set_slots(self.project.usage, view.filaments)
        self.task_list.set_presets(view.presets)

    def _reload_printers(self) -> None:
        printers = self._view.printers
        combo = self.printer_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(NO_PRINTER)
        for printer in printers:
            combo.addItem(printer.name)
        wanted = self._chosen_printer_id
        if wanted is None or not any(p.id == wanted for p in printers):
            by_id = sorted(printers, key=lambda p: p.id)
            match = printer_for_model(by_id, self.project.printer_model)
            wanted = match.id if match is not None else None
        index = next((i for i, p in enumerate(printers, start=1) if p.id == wanted), 0)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)
        model = self.project.printer_model
        self._detected_label.setText(
            f"Modelo detectado: {model}" if index == 0 and model else "")

    def _on_printer_changed(self, _index: int) -> None:
        printer = self.selected_printer()
        self._chosen_printer_id = printer.id if printer else None
        self._recalculate()

    def _on_copies_changed(self, value: int) -> None:
        self.task_list.set_copies(value)
        self._recalculate()

    def _recalculate(self) -> None:
        if self._loading:
            return
        self.slot_table.set_grams(self.effective_grams())
        try:
            self._outcome = self._price()
        except PricingError as exc:
            self._outcome = Blocked(str(exc))
        except Exception as exc:  # nunca deixar um preço antigo parecendo válido
            traceback.print_exc()
            self._outcome = Blocked(f"{UNEXPECTED_ERROR_TEXT}: {exc}")
        outcome = self._outcome
        if isinstance(outcome, Blocked):
            self.cost_label.setText(outcome.reason)
            self.cost_label.setStyleSheet(BLOCKED_STYLE)
        else:
            self.cost_label.setText(_cost_line(outcome["breakdown"]))
            self.cost_label.setStyleSheet("")
        self.changed.emit()

    def _price(self) -> dict | Blocked:
        project = self.project
        printer = self.selected_printer()
        if printer is None:
            return Blocked(CHOOSE_PRINTER_TEXT)
        selected = self.slot_table.selected_filaments()
        if any(f is None for f in selected.values()):
            return Blocked(CHOOSE_FILAMENTS_TEXT)
        grams_by_slot = self.effective_grams()
        seconds = self.effective_seconds()
        if not project.is_sliced and (
                seconds == 0 or all(g == 0 for g in grams_by_slot.values())):
            return Blocked(MANUAL_INPUT_TEXT)
        if project.is_sliced and (project.total_seconds == 0 or project.total_grams == 0):
            return Blocked(SLICED_NO_DATA_TEXT)
        settings = self._view.settings
        inputs = build_pricing_inputs(
            selected, grams_by_slot, seconds, self.copies(), printer, settings,
            self.task_list.tasks(), self.task_list.extra_materials())
        breakdown = compute_cost(inputs)
        tiers = suggest_prices(breakdown.total, tier_configs(settings),
                               inputs.copies, settings.rounding_step)
        rows = []
        for usage in project.usage:
            filament = selected.get(usage.slot)
            rows.append({
                "slot": usage.slot, "color": usage.color, "type": usage.type,
                "grams": grams_by_slot.get(usage.slot, Decimal(0)),
                "filament_id": filament.id if filament else None,
                "filament_label": filament_label(filament) if filament else None,
                "roll_price": filament.roll_price if filament else None,
                "roll_grams": filament.roll_grams if filament else None,
            })
        if self.path is not None:
            source = self.path.name
        else:
            source = (self._saved or {}).get("source_file", "")
        return build_product(
            project.name, source, rows, inputs.tasks, breakdown, tiers,
            inputs.copies, seconds, printer_id=printer.id,
            extra_materials=inputs.extra_materials)
