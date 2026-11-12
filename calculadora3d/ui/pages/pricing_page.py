"""Página Precificar: arquivos, resumo, slots, acabamento e resultado."""
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox, QComboBox, QFormLayout, QFrame, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import Catalog, Filament, Printer, Settings
from calculadora3d.core.models import SlicedProject
from calculadora3d.core.pricing import (
    CostBreakdown, FinishingTask, PriceTier, PricingError, PricingInputs,
    TierConfig, compute_cost, suggest_prices,
)
from calculadora3d.core.quotes import (
    build_snapshot, save_quote, snapshot_project, snapshot_result,
)
from calculadora3d.core.threemf import ThreeMFError, read_project, read_projects
from calculadora3d.ui.formatting import brl, date_time, duration, grams
from calculadora3d.ui.pdf_export import export_quotes_pdf
from calculadora3d.ui.widgets.cost_panel import CostPanel
from calculadora3d.ui.widgets.drop_area import DropArea
from calculadora3d.ui.widgets.slot_table import SlotTable, filament_label
from calculadora3d.ui.widgets.task_list import TaskList

NO_PRINTER = "— escolher —"
UNSLICED_TEXT = "Este arquivo não foi salvo depois de fatiar"
WARNING_STYLE = "background-color: #fff3b0; color: #4a3b00; padding: 4px; border-radius: 3px;"
SAVED_STYLE = ("background-color: #dbeafe; color: #1e3a5f; padding: 6px;"
               " border-radius: 3px; font-weight: bold;")

FILAMENTS_PAGE = "Filamentos"
EMPTY_CATALOG_TEXT = "Cadastre pelo menos um filamento e uma impressora"
EMPTY_CATALOG_ACTION = "Ir para o cadastro de filamentos"
CHOOSE_PRINTER_TEXT = "Escolha a impressora"
CHOOSE_FILAMENTS_TEXT = "Escolha o filamento de todos os slots"
MANUAL_INPUT_TEXT = "Informe o peso e o tempo de impressão"
SLICED_NO_DATA_TEXT = "O arquivo fatiado não traz peso ou tempo — confira o .3mf"
UNEXPECTED_ERROR_TEXT = "Não foi possível calcular o preço"
SAVE_TEXT = "Salvar no histórico"
EXPORT_TEXT = "Exportar orçamento"


@dataclass(frozen=True)
class _Priced:
    """Entradas e resultado do último cálculo válido, para salvar no histórico."""
    filaments: Mapping[int, Filament]
    grams_by_slot: Mapping[int, Decimal]
    seconds: int
    copies: int
    printer: Printer
    tasks: tuple[FinishingTask, ...]
    extra_materials: Decimal
    breakdown: CostBreakdown
    tiers: tuple[PriceTier, ...]


def _saved_details(snapshot: dict) -> str:
    lines = [f"Projeto: {snapshot['project_name']}"]
    if snapshot.get("source_file"):
        lines.append(f"Arquivos: {snapshot['source_file']}")
    lines.append(f"Tempo de impressão: {duration(int(snapshot['seconds']))}"
                 f" · Produtos: {snapshot['copies']}")
    for row in snapshot.get("usage", []):
        text = (f"Slot {row['slot']} — {row.get('type') or '—'} {row.get('color') or ''}"
                f" — {grams(Decimal(str(row.get('grams', '0'))))}")
        if row.get("filament_label"):
            text += f" — {row['filament_label']}"
        if row.get("roll_price") is not None and row.get("roll_grams") is not None:
            text += (f" (rolo de {grams(Decimal(str(row['roll_grams'])))}"
                     f" a {brl(Decimal(str(row['roll_price'])))})")
        lines.append(text)
    tasks = snapshot.get("tasks", [])
    if tasks:
        lines.append("Acabamento: " + ", ".join(
            f"{t['name']} ({t['minutes']} min)" for t in tasks))
    extras = Decimal(str(snapshot.get("extra_materials", "0")))
    if extras:
        lines.append(f"Materiais extras: {brl(extras)}")
    return "\n".join(lines)


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


class PricingPage(QWidget):
    inputs_changed = Signal()
    register_filament_requested = Signal(dict)
    go_to_page = Signal(str)
    quote_saved = Signal(int)

    def __init__(self, catalog: Catalog, parent=None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self._paths: list[Path] = []
        self._single: dict[Path, SlicedProject] = {}
        self._project: SlicedProject | None = None
        self._weight_boxes: dict[int, QDoubleSpinBox] = {}
        self._printers: list[Printer] = []
        self._chosen_printer_id: int | None = None
        self._manual_weights: dict[int, float] = {}
        self._manual_minutes: int | None = None
        self._priced: _Priced | None = None
        self._saved_snapshot: dict | None = None
        self._base_snapshot: dict | None = None

        self.saved_box = QGroupBox("Orçamento salvo")
        self.saved_banner = QLabel()
        self.saved_banner.setWordWrap(True)
        self.saved_banner.setStyleSheet(SAVED_STYLE)
        self.saved_details = QLabel()
        self.saved_details.setWordWrap(True)
        self.new_calc_button = QPushButton("Novo cálculo")
        self.new_calc_button.clicked.connect(self.clear)
        saved_layout = QVBoxLayout(self.saved_box)
        saved_layout.addWidget(self.saved_banner)
        saved_layout.addWidget(self.saved_details)
        self.saved_export_button = QPushButton(EXPORT_TEXT)
        self.saved_export_button.clicked.connect(self.export_current_quote)
        saved_buttons = QHBoxLayout()
        saved_buttons.addWidget(self.new_calc_button)
        saved_buttons.addWidget(self.saved_export_button)
        saved_buttons.addStretch(1)
        saved_layout.addLayout(saved_buttons)
        self.saved_box.hide()

        self.based_on_label = QLabel()
        self.based_on_label.setStyleSheet("font-style: italic;")
        self.based_on_label.hide()

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.load_projects)

        self._files_layout = QVBoxLayout()
        self.files_box = QGroupBox("Arquivos carregados")
        self.files_box.setLayout(self._files_layout)

        self.summary_box = QGroupBox("Resumo")
        self._build_summary()

        self._warnings_layout = QVBoxLayout()
        self.details_layout = QVBoxLayout()
        self.slot_table = SlotTable()
        self.task_list = TaskList()
        self.cost_panel = CostPanel()
        self.save_button = QPushButton(SAVE_TEXT)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_current_quote)
        self.export_button = QPushButton(EXPORT_TEXT)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_current_quote)
        self.save_status = QLabel()
        self.save_row = QWidget()
        save_layout = QHBoxLayout(self.save_row)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.addWidget(self.save_button)
        save_layout.addWidget(self.export_button)
        save_layout.addWidget(self.save_status, 1)
        for widget in (self.slot_table, self.task_list, self.cost_panel, self.save_row):
            self.details_layout.addWidget(widget)
        self.slot_table.changed.connect(self._recalculate)
        self.slot_table.register_requested.connect(self.register_filament_requested.emit)
        self.task_list.changed.connect(self._recalculate)
        self.cost_panel.action_requested.connect(
            lambda: self.go_to_page.emit(FILAMENTS_PAGE))
        self.inputs_changed.connect(self._recalculate)
        self.inputs_changed.connect(lambda: self.task_list.set_copies(self.copies()))
        self._load_catalog()

        content = QWidget()
        col = QVBoxLayout(content)
        col.addWidget(self.saved_box)
        col.addWidget(self.drop_area)
        col.addWidget(self.based_on_label)
        col.addWidget(self.files_box)
        col.addWidget(self.summary_box)
        col.addLayout(self._warnings_layout)
        col.addLayout(self.details_layout)
        col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._refresh()

    def _build_summary(self) -> None:
        self._name_label = QLabel()
        self._plates_label = QLabel()
        self._time_label = QLabel()
        self._weight_label = QLabel()

        self.printer_combo = QComboBox()
        self._detected_label = QLabel()
        printer_row = QHBoxLayout()
        printer_row.addWidget(self.printer_combo, 1)
        printer_row.addWidget(self._detected_label)
        self.printer_combo.currentIndexChanged.connect(self._on_printer_changed)

        self.copies_spin = QSpinBox()
        self.copies_spin.setMinimum(1)
        self.copies_spin.setMaximum(100000)
        self.copies_spin.setToolTip(
            "Quantos produtos vendáveis saem desta impressão; o custo é dividido entre eles")
        self.copies_spin.valueChanged.connect(lambda _v: self.inputs_changed.emit())

        self._unsliced_label = QLabel(UNSLICED_TEXT)
        self._unsliced_label.setStyleSheet("font-weight: bold;")
        self._manual_box = QWidget()
        self._manual_form = QFormLayout(self._manual_box)
        self._manual_form.setContentsMargins(0, 0, 0, 0)
        self.hours_spin = self.minutes_spin = None

        form = QFormLayout()
        form.addRow("Projeto", self._name_label)
        form.addRow("Impressora", printer_row)
        form.addRow("Placas", self._plates_label)
        form.addRow("Tempo total", self._time_label)
        form.addRow("Peso total", self._weight_label)
        form.addRow("Produtos", self.copies_spin)
        layout = QVBoxLayout(self.summary_box)
        layout.addLayout(form)
        layout.addWidget(self._unsliced_label)
        layout.addWidget(self._manual_box)

    # API pública
    def load_projects(self, paths: list[Path]) -> None:
        new: list[Path] = []
        known = {p.resolve() for p in self._paths}
        for raw in paths:
            path = Path(raw)
            key = path.resolve()
            if key in known:
                continue
            known.add(key)
            new.append(path)
        if not new:
            return
        singles: dict[Path, SlicedProject] = {}
        for path in new:
            try:
                singles[path] = read_project(path)
            except ThreeMFError as exc:
                QMessageBox.warning(self, "Arquivo inválido", str(exc))
                return
            except Exception as exc:  # arquivo de terceiro: nunca derrubar o app
                QMessageBox.warning(
                    self, "Arquivo inválido",
                    f"Não foi possível ler {path.name}: {exc}")
                return
        candidate = self._paths + new
        try:
            project = read_projects(candidate)
        except Exception as exc:
            message = str(exc) if isinstance(exc, ThreeMFError) else (
                f"Não foi possível ler {new[0].name}: {exc}")
            QMessageBox.warning(self, "Arquivo inválido", message)
            return
        self._leave_snapshot()
        self._paths = candidate
        self._single.update(singles)
        self._project = project
        self._refresh()

    def clear(self) -> None:
        self._leave_snapshot()
        self._paths = []
        self._single = {}
        self._project = None
        self._chosen_printer_id = None
        self._manual_weights = {}
        self._manual_minutes = None
        self.slot_table.reset_choices()
        self.task_list.clear()
        self._refresh()

    def save_current_quote(self) -> int | None:
        """Pede um nome e grava o último cálculo válido no histórico."""
        priced, project = self._priced, self._project
        if priced is None or project is None:
            return None
        name, ok = QInputDialog.getText(
            self, SAVE_TEXT, "Nome do orçamento:", text=project.name)
        name = name.strip()
        if not ok or not name:
            return None
        snapshot = self._current_snapshot(name)
        if snapshot is None:
            return None
        try:
            quote_id = save_quote(self.catalog, snapshot)
        except Exception as exc:
            QMessageBox.warning(self, SAVE_TEXT,
                                f"Não foi possível salvar o orçamento: {exc}")
            return None
        self.save_status.setText(f"Salvo no histórico como “{name}”.")
        self.quote_saved.emit(quote_id)
        return quote_id

    def export_current_quote(self) -> Path | None:
        """Gera o PDF do orçamento mostrado (cálculo atual ou orçamento reaberto)."""
        snapshot = self._saved_snapshot
        if snapshot is None and self._project is not None:
            snapshot = self._current_snapshot(self._project.name)
        if snapshot is None:
            return None
        return export_quotes_pdf(self, self.catalog, [snapshot])

    def _current_snapshot(self, name: str) -> dict | None:
        priced, project = self._priced, self._project
        if priced is None or project is None:
            return None
        rows = []
        for usage in project.usage:
            filament = priced.filaments.get(usage.slot)
            rows.append({
                "slot": usage.slot, "color": usage.color, "type": usage.type,
                "grams": priced.grams_by_slot.get(usage.slot, Decimal(0)),
                "filament_id": filament.id if filament else None,
                "filament_label": filament_label(filament) if filament else None,
                "roll_price": filament.roll_price if filament else None,
                "roll_grams": filament.roll_grams if filament else None,
            })
        if self._paths:
            source = ", ".join(p.name for p in self._paths)
        else:
            source = (self._base_snapshot or {}).get("source_file", "")
        snapshot = build_snapshot(
            name, source, rows, priced.tasks, priced.breakdown, priced.tiers,
            priced.copies, priced.seconds, printer_id=priced.printer.id,
            extra_materials=priced.extra_materials)
        return snapshot

    def load_snapshot(self, snapshot: dict, *, recalculate: bool = False) -> None:
        """Reabre um orçamento salvo.

        recalculate=False mostra os valores gravados, sem recalcular nada;
        recalculate=True usa o orçamento como base e recalcula com o catálogo atual.
        """
        self.clear()
        if recalculate:
            self._start_from_snapshot(snapshot)
        else:
            self._show_saved(snapshot)

    def refresh_catalog(self) -> None:
        """Relê filamentos, impressoras, ajustes e presets e recalcula."""
        self._load_catalog()
        project = self._project
        if project is not None:
            self._reload_printers(project)
            self.slot_table.set_slots(project.usage, self._filaments)
        self._recalculate()

    def selected_printer(self) -> Printer | None:
        index = self.printer_combo.currentIndex()
        if index <= 0 or index > len(self._printers):
            return None
        return self._printers[index - 1]

    def copies(self) -> int:
        return self.copies_spin.value()

    def project(self) -> SlicedProject | None:
        return self._project

    def effective_seconds(self) -> int:
        project = self._project
        if project is None:
            return 0
        if project.is_sliced:
            return project.total_seconds
        if self.hours_spin is None:
            return 0
        return self.hours_spin.value() * 3600 + self.minutes_spin.value() * 60

    def effective_grams(self) -> dict[int, Decimal]:
        project = self._project
        if project is None:
            return {}
        if project.is_sliced:
            return {u.slot: u.grams for u in project.usage}
        return {slot: Decimal(str(round(box.value(), 2)))
                for slot, box in self._weight_boxes.items()}

    # Interno
    def _leave_snapshot(self) -> None:
        self._saved_snapshot = None
        self._base_snapshot = None
        self.saved_box.hide()
        self.based_on_label.hide()

    def _show_saved(self, snapshot: dict) -> None:
        breakdown, tiers = snapshot_result(snapshot)
        created = datetime.fromisoformat(snapshot["created_at"])
        self._saved_snapshot = snapshot
        self.saved_banner.setText(
            f"Orçamento salvo em {date_time(created)} — valores do momento em que foi salvo")
        self.saved_details.setText(_saved_details(snapshot))
        self.saved_box.show()
        self.cost_panel.show_result(breakdown, tiers, int(snapshot["copies"]))

    def _start_from_snapshot(self, snapshot: dict) -> None:
        project = snapshot_project(snapshot)
        known = {f.id for f in self._filaments}
        self.slot_table.set_choices({
            int(row["slot"]): row.get("filament_id") if row.get("filament_id") in known else None
            for row in snapshot["usage"]})
        self._chosen_printer_id = snapshot.get("printer_id")
        for task in snapshot.get("tasks", []):
            self.task_list.add_task(task["name"], int(task["minutes"]))
        self.task_list.extras_spin.setValue(
            float(Decimal(str(snapshot.get("extra_materials", "0")))))
        self._base_snapshot = snapshot
        self.based_on_label.setText(f"Baseado no orçamento {snapshot['project_name']}")
        self.based_on_label.show()
        self._project = project
        self._refresh()

    def _remove(self, path: Path) -> None:
        remaining = [p for p in self._paths if p != path]
        if not remaining:
            self.clear()
            return
        try:
            project = read_projects(remaining)
        except Exception as exc:
            QMessageBox.warning(self, "Arquivo inválido",
                                f"Não foi possível reler os arquivos: {exc}")
            return
        self._paths = remaining
        self._single.pop(path, None)
        self._project = project
        self._refresh()

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _refresh(self) -> None:
        project = self._project
        self._clear_layout(self._files_layout)
        self._clear_layout(self._warnings_layout)
        self.files_box.setVisible(bool(self._paths))
        self.summary_box.setVisible(project is not None)
        self.slot_table.setVisible(project is not None)
        self.task_list.setVisible(project is not None)
        self.save_row.setVisible(project is not None)
        if project is None:
            self._weight_boxes = {}
            self._rebuild_manual(None)
            self.slot_table.set_slots((), self._filaments)
            self.inputs_changed.emit()
            return

        for path in self._paths:
            single = self._single[path]
            if single.is_sliced:
                detail = f"{grams(single.total_grams)} · {duration(single.total_seconds)}"
            else:
                detail = "não fatiado"
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QLabel(path.name), 1)
            h.addWidget(QLabel(detail))
            button = QPushButton("Remover")
            button.clicked.connect(lambda _c=False, p=path: self._remove(p))
            h.addWidget(button)
            self._files_layout.addWidget(row)

        self._name_label.setText(project.name)
        sliced = project.is_sliced
        self._plates_label.setText(str(len([p for p in project.plates if not p.skipped])) if sliced else "—")
        self._time_label.setText(duration(project.total_seconds) if sliced else "—")
        self._weight_label.setText(grams(project.total_grams) if sliced else "—")

        self._reload_printers(project)
        self.copies_spin.blockSignals(True)
        self.copies_spin.setValue(project.copies)
        self.copies_spin.blockSignals(False)

        self._rebuild_manual(project)
        self.slot_table.set_slots(project.usage, self._filaments)
        for text in project.warnings:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(WARNING_STYLE)
            self._warnings_layout.addWidget(label)
        self.inputs_changed.emit()

    def _load_catalog(self) -> None:
        self._filaments = self.catalog.list_filaments()
        self._settings = self.catalog.get_settings()
        self._catalog_ready = bool(self._filaments) and bool(self.catalog.list_printers())
        self.task_list.set_presets(self.catalog.list_task_presets())

    def _recalculate(self) -> None:
        if self._saved_snapshot is not None:
            return  # orçamento reaberto: os valores salvos não mudam
        self._priced = None
        self.save_status.clear()
        try:
            self._price_current()
        finally:
            self.save_button.setEnabled(self._priced is not None)
            self.export_button.setEnabled(self._priced is not None)

    def _price_current(self) -> None:
        project = self._project
        panel = self.cost_panel
        if project is not None:
            self.slot_table.set_grams(self.effective_grams())
        if not self._catalog_ready:
            panel.show_blocked(EMPTY_CATALOG_TEXT, EMPTY_CATALOG_ACTION)
            return
        if project is None:
            panel.clear()
            return
        printer = self.selected_printer()
        if printer is None:
            panel.show_blocked(CHOOSE_PRINTER_TEXT)
            return
        selected = self.slot_table.selected_filaments()
        if any(f is None for f in selected.values()):
            panel.show_blocked(CHOOSE_FILAMENTS_TEXT)
            return
        grams_by_slot = self.effective_grams()
        seconds = self.effective_seconds()
        if not project.is_sliced and (
                seconds == 0 or all(g == 0 for g in grams_by_slot.values())):
            panel.show_blocked(MANUAL_INPUT_TEXT)
            return
        if project.is_sliced and (
                project.total_seconds == 0 or project.total_grams == 0):
            panel.show_blocked(SLICED_NO_DATA_TEXT)
            return
        settings = self._settings
        try:
            inputs = build_pricing_inputs(
                selected, grams_by_slot, seconds, self.copies(), printer, settings,
                self.task_list.tasks(), self.task_list.extra_materials())
            breakdown = compute_cost(inputs)
            tiers = suggest_prices(breakdown.total, tier_configs(settings),
                                   inputs.copies, settings.rounding_step)
            panel.show_result(breakdown, tiers, inputs.copies)
            self._priced = _Priced(
                dict(selected), dict(grams_by_slot), seconds, inputs.copies, printer,
                inputs.tasks, inputs.extra_materials, breakdown, tuple(tiers))
        except PricingError as exc:
            panel.show_blocked(str(exc))
        except Exception as exc:  # nunca deixar um preço antigo parecendo válido
            traceback.print_exc()
            panel.show_blocked(f"{UNEXPECTED_ERROR_TEXT}: {exc}")

    def _on_printer_changed(self, _index: int) -> None:
        printer = self.selected_printer()
        self._chosen_printer_id = printer.id if printer else None
        self.inputs_changed.emit()

    def _reload_printers(self, project: SlicedProject) -> None:
        self._printers = self.catalog.list_printers()
        combo = self.printer_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(NO_PRINTER)
        for printer in self._printers:
            combo.addItem(printer.name)
        wanted = self._chosen_printer_id
        if wanted is None or not any(p.id == wanted for p in self._printers):
            match = (self.catalog.find_printer_by_model(project.printer_model)
                     if project.printer_model else None)
            wanted = match.id if match is not None else None
        index = next((i for i, p in enumerate(self._printers, start=1)
                      if p.id == wanted), 0)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)
        if index == 0 and project.printer_model:
            self._detected_label.setText(f"Modelo detectado: {project.printer_model}")
        else:
            self._detected_label.setText("")

    def _on_weight_changed(self, slot: int, value: float) -> None:
        self._manual_weights[slot] = value
        self.inputs_changed.emit()

    def _on_time_changed(self, _value: int) -> None:
        self._manual_minutes = self.hours_spin.value() * 60 + self.minutes_spin.value()
        self.inputs_changed.emit()

    def _sliced_contribution(self) -> tuple[dict[int, Decimal], int]:
        """Gramas por slot e segundos dos arquivos fatiados, para pré-preencher."""
        grams_by_slot: dict[int, Decimal] = {}
        seconds = 0
        for path in self._paths:
            single = self._single[path]
            if not single.is_sliced:
                continue
            seconds += single.total_seconds
            for usage in single.usage:
                grams_by_slot[usage.slot] = grams_by_slot.get(usage.slot, Decimal(0)) + usage.grams
        return grams_by_slot, seconds

    def _rebuild_manual(self, project: SlicedProject | None) -> None:
        while self._manual_form.rowCount():
            self._manual_form.removeRow(0)
        self._weight_boxes = {}
        unsliced = project is not None and not project.is_sliced
        self._unsliced_label.setVisible(unsliced)
        self._manual_box.setVisible(unsliced)
        if not unsliced:
            return
        sliced_grams, sliced_seconds = self._sliced_contribution()
        for usage in project.usage:
            box = QDoubleSpinBox()
            box.setDecimals(2)
            box.setRange(0, 100000)
            box.setSuffix(" g")
            box.setValue(self._manual_weights.get(
                usage.slot, float(sliced_grams.get(usage.slot, Decimal(0)))))
            box.valueChanged.connect(
                lambda v, slot=usage.slot: self._on_weight_changed(slot, v))
            self._weight_boxes[usage.slot] = box
            label = f"Peso do slot {usage.slot}"
            if usage.type:
                label += f" ({usage.type})"
            self._manual_form.addRow(label, box)
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 9999)
        self.hours_spin.setSuffix(" h")
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setSuffix(" min")
        minutes = self._manual_minutes
        if minutes is None:
            minutes = (sliced_seconds + 30) // 60
        self.hours_spin.setValue(minutes // 60)
        self.minutes_spin.setValue(minutes % 60)
        for spin in (self.hours_spin, self.minutes_spin):
            spin.valueChanged.connect(self._on_time_changed)
        time_row = QWidget()
        row = QHBoxLayout(time_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.hours_spin)
        row.addWidget(self.minutes_spin)
        row.addStretch(1)
        self._manual_form.addRow("Tempo total", time_row)
