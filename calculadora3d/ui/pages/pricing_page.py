"""Página Precificar: um painel por arquivo, o resumo e o resultado do pedido."""
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from calculadora3d.core.catalog import Catalog
from calculadora3d.core.quotes import (
    build_order, normalize_order, save_quote, snapshot_project, snapshot_result,
    snapshot_thumbnails,
)
from calculadora3d.core.threemf import ThreeMFError, read_project
from calculadora3d.ui.formatting import brl, date_time, duration, grams
from calculadora3d.ui.pdf_export import export_quotes_pdf
from calculadora3d.ui.widgets.drop_area import DropArea
from calculadora3d.ui.widgets.order_result import OrderResult, ResultRow
from calculadora3d.ui.widgets.plate_thumbnails import PlateThumbnails
from calculadora3d.ui.widgets.product_panel import (
    Blocked, CatalogView, ProductPanel, cost_line,
)

SAVED_STYLE = ("background-color: #dbeafe; color: #1e3a5f; padding: 6px;"
               " border-radius: 3px; font-weight: bold;")

FILAMENTS_PAGE = "Filamentos"
EMPTY_CATALOG_TEXT = "Cadastre pelo menos um filamento e uma impressora"
EMPTY_CATALOG_ACTION = "Ir para o cadastro de filamentos"
SAVE_TEXT = "Salvar no histórico"
EXPORT_TEXT = "Exportar orçamento"
FILES_TITLE = "Arquivos"


def _saved_details(product: dict) -> str:
    lines = [f"Projeto: {product['project_name']}"]
    if product.get("source_file"):
        lines.append(f"Arquivos: {product['source_file']}")
    lines.append(f"Tempo de impressão: {duration(int(product['seconds']))}"
                 f" · Produtos: {product['copies']}")
    for row in product.get("usage", []):
        text = (f"Slot {row['slot']} — {row.get('type') or '—'} {row.get('color') or ''}"
                f" — {grams(Decimal(str(row.get('grams', '0'))))}")
        if row.get("filament_label"):
            text += f" — {row['filament_label']}"
        if row.get("roll_price") is not None and row.get("roll_grams") is not None:
            text += (f" (rolo de {grams(Decimal(str(row['roll_grams'])))}"
                     f" a {brl(Decimal(str(row['roll_price'])))})")
        lines.append(text)
    tasks = product.get("tasks", [])
    if tasks:
        lines.append("Acabamento: " + ", ".join(
            f"{t['name']} ({t['minutes']} min)" for t in tasks))
    extras = Decimal(str(product.get("extra_materials", "0")))
    if extras:
        lines.append(f"Materiais extras: {brl(extras)}")
    lines.append(cost_line(product["breakdown"]))
    return "\n".join(lines)


def _read_error(path: Path, exc: Exception) -> str:
    if isinstance(exc, ThreeMFError):
        message = str(exc)
        return message if path.name in message else f"{path.name}: {message}"
    return f"Não foi possível ler {path.name}: {exc}"


class PricingPage(QWidget):
    register_filament_requested = Signal(dict)
    go_to_page = Signal(str)
    quote_saved = Signal(int)

    def __init__(self, catalog: Catalog, parent=None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self._view = CatalogView.load(catalog)
        self._panels: list[ProductPanel] = []
        self._saved_order: dict | None = None  # orçamento reaberto (somente leitura)

        self.saved_box = QGroupBox("Orçamento salvo")
        self.saved_banner = QLabel()
        self.saved_banner.setWordWrap(True)
        self.saved_banner.setStyleSheet(SAVED_STYLE)
        self._saved_products_layout = QVBoxLayout()
        self._saved_products_layout.setContentsMargins(0, 0, 0, 0)
        self.new_calc_button = QPushButton("Novo cálculo")
        self.new_calc_button.clicked.connect(self.clear)
        self.saved_export_button = QPushButton(EXPORT_TEXT)
        self.saved_export_button.clicked.connect(self.export_current_quote)
        saved_buttons = QHBoxLayout()
        saved_buttons.addWidget(self.new_calc_button)
        saved_buttons.addWidget(self.saved_export_button)
        saved_buttons.addStretch(1)
        saved_layout = QVBoxLayout(self.saved_box)
        saved_layout.addWidget(self.saved_banner)
        saved_layout.addLayout(self._saved_products_layout)
        saved_layout.addLayout(saved_buttons)
        self.saved_box.hide()

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.load_projects)

        self.based_on_label = QLabel()
        self.based_on_label.setStyleSheet("font-style: italic;")
        self.based_on_label.hide()

        self._panels_layout = QVBoxLayout()
        self._panels_layout.setContentsMargins(0, 0, 0, 0)

        self.summary_box = QGroupBox("Resumo")
        self._files_label = QLabel()
        self._plates_label = QLabel()
        self._time_label = QLabel()
        self._weight_label = QLabel()
        self._copies_label = QLabel()
        form = QFormLayout(self.summary_box)
        form.addRow("Arquivos", self._files_label)
        form.addRow("Placas", self._plates_label)
        form.addRow("Tempo", self._time_label)
        form.addRow("Peso", self._weight_label)
        form.addRow("Produtos", self._copies_label)

        self.order_result = OrderResult()
        self.order_result.action_requested.connect(
            lambda: self.go_to_page.emit(FILAMENTS_PAGE))

        self.save_button = QPushButton(SAVE_TEXT)
        self.save_button.clicked.connect(self.save_current_quote)
        self.export_button = QPushButton(EXPORT_TEXT)
        self.export_button.clicked.connect(self.export_current_quote)
        self.save_status = QLabel()
        self.save_row = QWidget()
        save_layout = QHBoxLayout(self.save_row)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.addWidget(self.save_button)
        save_layout.addWidget(self.export_button)
        save_layout.addWidget(self.save_status, 1)

        content = QWidget()
        col = QVBoxLayout(content)
        col.addWidget(self.saved_box)
        col.addWidget(self.drop_area)
        col.addWidget(self.based_on_label)
        col.addLayout(self._panels_layout)
        col.addWidget(self.summary_box)
        col.addWidget(self.order_result)
        col.addWidget(self.save_row)
        col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._update()

    # API pública
    def panels(self) -> list[ProductPanel]:
        return list(self._panels)

    def load_projects(self, paths: list[Path]) -> None:
        """Um painel por arquivo novo; inválidos e repetidos são avisados juntos."""
        known = {p.path.resolve() for p in self._panels if p.path is not None}
        problems: list[str] = []
        added: list[ProductPanel] = []
        for raw in paths:
            path = Path(raw)
            key = path.resolve()
            if key in known:
                problems.append(f"{path.name} já está na lista")
                continue
            known.add(key)
            try:
                added.append(ProductPanel(read_project(path), self._view, path=path))
            except Exception as exc:  # arquivo de terceiro: nunca derrubar o app
                problems.append(_read_error(path, exc))
        if added and self._saved_order is not None:
            self.clear()  # sai do orçamento reaberto só se algum arquivo entrou
        for panel in added:
            self._add_panel(panel)
        if added:
            self._update()
        if problems:
            QMessageBox.warning(self, FILES_TITLE, "\n".join(problems))

    def clear(self) -> None:
        self._leave_snapshot()
        for panel in self._panels:
            self._discard(panel)
        self._panels = []
        self._update()

    def save_current_quote(self) -> int | None:
        """Pede um nome e grava o pedido (todos os produtos precificados) no histórico."""
        products = self._current_products()
        if products is None:
            return None
        name, ok = QInputDialog.getText(
            self, SAVE_TEXT, "Nome do orçamento:", text=self._panels[0].project.name)
        name = name.strip()
        if not ok or not name:
            return None
        try:
            quote_id = save_quote(self.catalog, build_order(name, products))
        except Exception as exc:
            QMessageBox.warning(self, SAVE_TEXT,
                                f"Não foi possível salvar o orçamento: {exc}")
            return None
        self.save_status.setText(f"Salvo no histórico como “{name}”.")
        self.quote_saved.emit(quote_id)
        return quote_id

    def export_current_quote(self) -> Path | None:
        """Gera o PDF do pedido mostrado (cálculo atual ou orçamento reaberto)."""
        if self._saved_order is not None:
            products = self._saved_order["products"]
        else:
            products = self._current_products()
        if not products:
            return None
        return export_quotes_pdf(self, self.catalog, products)

    def load_snapshot(self, snapshot: dict, *, recalculate: bool = False) -> None:
        """Reabre um orçamento salvo.

        recalculate=False mostra os valores gravados, sem recalcular nada;
        recalculate=True usa o orçamento como base e recalcula com o catálogo atual.
        Tudo é validado antes de mexer na tela: se o snapshot estiver malformado,
        a exceção sobe e a tela fica como estava.
        """
        order = normalize_order(snapshot)
        products = order["products"]
        if not products:
            raise ValueError("o orçamento não tem produtos")
        for product in products:
            snapshot_result(product)
            snapshot_project(product)
        if recalculate:
            name = str(order["name"])
            panels = [ProductPanel.from_product(p, self._view) for p in products]
            self.clear()
            for panel in panels:
                self._add_panel(panel)
            self.based_on_label.setText(f"Baseado no orçamento {name}")
            self.based_on_label.show()
            self._update()
            return
        created = datetime.fromisoformat(order["created_at"])
        rows = [ResultRow(str(p["project_name"]), int(p["copies"]), p) for p in products]
        details = [_saved_details(p) for p in products]
        self.clear()
        self._saved_order = order
        self.saved_banner.setText(
            f"Orçamento salvo em {date_time(created)} — valores do momento em que foi salvo")
        for product, text in zip(products, details):
            label = QLabel(text)
            label.setWordWrap(True)
            self._saved_products_layout.addWidget(label)
            self._saved_products_layout.addWidget(
                PlateThumbnails(snapshot_thumbnails(product)))
        self.saved_box.show()
        self.summary_box.hide()
        self.save_row.hide()
        self.order_result.show_rows(rows)

    def refresh_catalog(self) -> None:
        """Relê filamentos, impressoras, ajustes e presets e recalcula cada painel."""
        self._view = CatalogView.load(self.catalog)
        for panel in self._panels:
            panel.refresh_catalog(self._view)
        self._update()

    # Interno
    def _current_products(self) -> list[dict] | None:
        outcomes = [p.outcome() for p in self._panels]
        if not outcomes or any(isinstance(o, Blocked) for o in outcomes):
            return None
        return outcomes

    def _leave_snapshot(self) -> None:
        self._saved_order = None
        while self._saved_products_layout.count():
            widget = self._saved_products_layout.takeAt(0).widget()
            widget.setParent(None)
            widget.deleteLater()
        self.saved_box.hide()
        self.based_on_label.hide()

    def _add_panel(self, panel: ProductPanel) -> None:
        panel.changed.connect(self._update)
        panel.remove_requested.connect(lambda p=panel: self._remove_panel(p))
        panel.register_filament_requested.connect(self.register_filament_requested.emit)
        self._panels.append(panel)
        self._panels_layout.addWidget(panel)

    def _remove_panel(self, panel: ProductPanel) -> None:
        if panel not in self._panels:
            return
        if len(self._panels) == 1:
            self.clear()
            return
        self._panels.remove(panel)
        self._discard(panel)
        self._update()

    @staticmethod
    def _discard(panel: ProductPanel) -> None:
        panel.changed.disconnect()
        panel.setParent(None)
        panel.deleteLater()

    def _update(self) -> None:
        if self._saved_order is not None:
            return  # orçamento reaberto: os valores salvos não mudam
        panels = self._panels
        self.save_status.clear()
        self.summary_box.setVisible(bool(panels))
        self.save_row.setVisible(bool(panels))
        if panels:
            plates = sum(len([pl for pl in p.project.plates if not pl.skipped])
                         for p in panels if p.project.is_sliced)
            seconds = sum(p.effective_seconds() for p in panels)
            weight = sum((sum(p.effective_grams().values(), Decimal(0)) for p in panels),
                         Decimal(0))
            self._files_label.setText(str(len(panels)))
            self._plates_label.setText(str(plates))
            self._time_label.setText(duration(seconds))
            self._weight_label.setText(grams(weight))
            self._copies_label.setText(str(sum(p.copies() for p in panels)))
        if not self._view.ready:
            self.order_result.show_blocked(EMPTY_CATALOG_TEXT, EMPTY_CATALOG_ACTION)
        elif not panels:
            self.order_result.clear()
        else:
            self.order_result.show_rows(
                [ResultRow(p.project.name, p.copies(), p.outcome()) for p in panels])
        ready = self._current_products() is not None
        self.save_button.setEnabled(ready)
        self.export_button.setEnabled(ready)
