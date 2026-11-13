"""Página Configurações: custos, margens, arredondamento, tarefas e dados da empresa."""
from decimal import Decimal

from PySide6.QtCore import QLocale, QTimer, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import Catalog, CompanyInfo, Settings, TaskPreset

PT_BR = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
HUNDRED = Decimal(100)
STATUS_TIMEOUT_MS = 4000


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


def _flash(label: QLabel, timer: QTimer, text: str) -> None:
    """Mostra `text` no rótulo e o apaga após STATUS_TIMEOUT_MS."""
    label.setText(text)
    timer.start(STATUS_TIMEOUT_MS)


def _status_timer(label: QLabel, parent: QWidget) -> QTimer:
    timer = QTimer(parent)
    timer.setSingleShot(True)
    timer.timeout.connect(label.clear)
    return timer


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
        self._status_timer = _status_timer(self.status_label, self)
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

        self.company_box = self._build_company_box()
        right = QVBoxLayout()
        right.addWidget(self.preset_box, 1)
        right.addWidget(self.company_box)

        layout = QHBoxLayout(self)
        layout.addWidget(general_box, 1)
        layout.addLayout(right, 1)

        self.load_form()
        self.reload_presets()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.load_form()

    def _build_company_box(self) -> QGroupBox:
        self.company_edits: dict[str, QLineEdit] = {}
        form = QFormLayout()
        for attr, label, placeholder in (
                ("name", "Nome da empresa *", "ex.: Borcelle"),
                ("address", "Endereço *", "ex.: Rua Alegre, 123 - Cidade"),
                ("phone", "Telefone", "opcional"),
                ("site", "Site", "opcional, ex.: www.seusite.com.br"),
                ("email", "E-mail", "opcional"),
                ("social", "Rede social", "opcional, ex.: @seuperfil")):
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            form.addRow(label, edit)
            self.company_edits[attr] = edit
        hint = QLabel("Aparecem no orçamento exportado. * obrigatórios para exportar; "
                      "os opcionais em branco não aparecem.")
        hint.setStyleSheet("color: gray;")
        hint.setWordWrap(True)
        self.company_save_button = QPushButton("Salvar dados da empresa")
        self.company_save_button.clicked.connect(self.save_company)
        self.company_status = QLabel()
        self._company_status_timer = _status_timer(self.company_status, self)
        buttons = QHBoxLayout()
        buttons.addWidget(self.company_save_button)
        buttons.addWidget(self.company_status, 1)
        box = QGroupBox("Dados da empresa (orçamento)")
        box_layout = QVBoxLayout(box)
        box_layout.addLayout(form)
        box_layout.addWidget(hint)
        box_layout.addLayout(buttons)
        return box

    def save_company(self) -> None:
        info = CompanyInfo(**{attr: edit.text() for attr, edit in self.company_edits.items()})
        try:
            self.catalog.save_company(info)
        except Exception as error:
            QMessageBox.warning(self, "Dados da empresa",
                                f"Não foi possível salvar: {error}")
            return
        self.load_form()
        _flash(self.company_status, self._company_status_timer, "Dados da empresa salvos.")

    def load_form(self) -> None:
        company = self.catalog.get_company()
        for attr, edit in self.company_edits.items():
            edit.setText(getattr(company, attr))
        self.company_status.clear()
        self.status_label.clear()
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
        _flash(self.status_label, self._status_timer, "Configurações salvas.")
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
