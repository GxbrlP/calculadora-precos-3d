"""Orçamento do cliente em PDF (A4), desenhado com QPainter, e o fluxo de exportação."""
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QFont, QFontMetricsF, QPageLayout, QPageSize, QPainter, QPdfWriter,
)
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from calculadora3d.core.catalog import Catalog
from calculadora3d.core.export import ClientQuote, build_client_quote
from calculadora3d.core.formatting import brl
from calculadora3d.ui.export_dialog import GO_TO_SETTINGS, ExportDialog

TITLE = "Exportar orçamento"
SETTINGS_PAGE = "Configurações"
FONT = "Segoe UI"
BLACK = QColor("#000000")
WHITE = QColor("#ffffff")
ROW_SHADE = QColor("#f7f7f7")
TEXT = QColor("#111111")

# Medidas em milímetros (A4 = 210 × 297).
LEFT, RIGHT = 20.0, 190.0
ROW_H, HEADER_H, TOTAL_H = 22.0, 10.0, 10.0
TABLE_BOTTOM = 262.0
FOOTER_Y = 272.0
# (título, x inicial, x final, alinhamento)
COLUMNS = (
    ("Nº", LEFT, 38.0, Qt.AlignmentFlag.AlignCenter),
    ("Descrição do Produto", 42.0, 112.0, Qt.AlignmentFlag.AlignLeft),
    ("Preço", 112.0, 140.0, Qt.AlignmentFlag.AlignCenter),
    ("Qt.", 140.0, 161.0, Qt.AlignmentFlag.AlignCenter),
    ("Total", 161.0, RIGHT, Qt.AlignmentFlag.AlignCenter),
)


class _QuotePainter:
    def __init__(self, painter: QPainter, writer: QPdfWriter, quote: ClientQuote) -> None:
        self.p = painter
        self.writer = writer
        self.quote = quote
        self.scale = writer.resolution() / 25.4  # px por mm

    # Utilitários
    def mm(self, value: float) -> float:
        return value * self.scale

    def rect(self, x: float, y: float, w: float, h: float) -> QRectF:
        return QRectF(self.mm(x), self.mm(y), self.mm(w), self.mm(h))

    @staticmethod
    def font(size: float, weight=QFont.Weight.Normal, italic=False,
             spacing_mm: float = 0.0, scale: float = 1.0) -> QFont:
        font = QFont(FONT)
        font.setPointSizeF(size)
        font.setWeight(weight)
        font.setItalic(italic)
        if spacing_mm:
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing_mm * scale)
        return font

    def text(self, rect: QRectF, flags, value: str, font: QFont, color=TEXT) -> None:
        self.p.setFont(font)
        self.p.setPen(color)
        self.p.drawText(rect, int(flags), value)

    def fill(self, rect: QRectF, color: QColor) -> None:
        self.p.fillRect(rect, color)

    # Página
    def draw(self) -> None:
        y = self._header()
        y = self._table_header(y)
        for index, item in enumerate(self.quote.items, start=1):
            if y + ROW_H > TABLE_BOTTOM:
                y = self._new_page()
            self._row(y, index, item)
            y += ROW_H
        if y + TOTAL_H > TABLE_BOTTOM:
            y = self._new_page(with_header=False)
        self._total(y)
        self._footer()

    def _new_page(self, with_header: bool = True) -> float:
        self._footer()
        self.writer.newPage()
        return self._table_header(20.0) if with_header else 20.0

    def _header(self) -> float:
        company = self.quote.company
        name_font = self.font(10, spacing_mm=0.45, scale=self.scale)
        name = company.name.upper()
        width = QFontMetricsF(name_font, self.writer).horizontalAdvance(name) / self.scale
        box = self.rect(LEFT, 20, width + 18, 9)
        self.fill(box, BLACK)
        self.text(box, Qt.AlignmentFlag.AlignCenter, name, name_font, WHITE)
        if company.social:
            self.text(self.rect(100, 20, RIGHT - 100, 9),
                      Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                      company.social.upper(),
                      self.font(10, QFont.Weight.Bold, italic=True, spacing_mm=0.35,
                                scale=self.scale))

        title_row = self.rect(LEFT, 52, RIGHT - LEFT, 22)
        self.text(title_row, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                  "Orçamento", self.font(32, QFont.Weight.Bold))
        self.text(title_row, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                  self.quote.date, self.font(17, QFont.Weight.DemiBold))

        contacts = [c for c in (company.email, company.site, company.phone) if c]
        top = 92.0
        for line in contacts:
            self.text(self.rect(LEFT, top, 110, 6.5),
                      Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                      line, self.font(11, QFont.Weight.Light))
            top += 6.5
        self.text(self.rect(130, 90, RIGHT - 130, 16),
                  Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                  f"nº {self.quote.number}", self.font(28, QFont.Weight.Light))
        return max(top, 106.0) + 10

    def _table_header(self, y: float) -> float:
        self.fill(self.rect(LEFT, y, RIGHT - LEFT, HEADER_H), BLACK)
        font = self.font(10.5, QFont.Weight.Light)
        for title, x0, x1, align in COLUMNS:
            self.text(self.rect(x0, y, x1 - x0, HEADER_H),
                      align | Qt.AlignmentFlag.AlignVCenter, title, font, WHITE)
        return y + HEADER_H

    def _row(self, y: float, index: int, item) -> None:
        if index % 2:
            self.fill(self.rect(LEFT, y, RIGHT - LEFT, ROW_H), ROW_SHADE)
        bold = self.font(11, QFont.Weight.DemiBold)
        regular = self.font(11, QFont.Weight.Light)
        values = (
            (str(index), bold),
            (item.description, regular),
            (brl(item.unit), bold),
            (str(item.quantity), regular),
            (brl(item.total), bold),
        )
        for (value, font), (_t, x0, x1, align) in zip(values, COLUMNS):
            flags = align | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap
            self.text(self.rect(x0, y + 1, x1 - x0, ROW_H - 2), flags, value, font)

    def _total(self, y: float) -> None:
        _t, x0, x1, _a = COLUMNS[-1]
        box = self.rect(x0, y, x1 - x0, TOTAL_H)
        self.fill(box, BLACK)
        self.text(box, Qt.AlignmentFlag.AlignCenter, brl(self.quote.total),
                  self.font(11, QFont.Weight.DemiBold), WHITE)

    def _footer(self) -> None:
        self.text(self.rect(LEFT, FOOTER_Y, RIGHT - LEFT, 8),
                  Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                  self.quote.company.address, self.font(11, QFont.Weight.DemiBold))


def write_pdf(quote: ClientQuote, path: Path | str) -> None:
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    writer.setResolution(300)
    writer.setTitle(f"Orçamento nº {quote.number}")
    writer.setCreator(quote.company.name)
    painter = QPainter()
    if not painter.begin(writer):
        raise OSError(f"não foi possível abrir {path} para escrita")
    try:
        _QuotePainter(painter, writer, quote).draw()
    finally:
        painter.end()


def _file_name(quote: ClientQuote) -> str:
    first = quote.items[0].description if quote.items else ""
    base = f"Orçamento {quote.number:03d} - {first}".strip(" -")
    return re.sub(r'[\\/:*?"<>|]+', "_", base) + ".pdf"


def export_quotes_pdf(parent: QWidget, catalog: Catalog,
                      snapshots: Sequence[dict]) -> Path | None:
    """Pergunta descrição e preço de cada produto, onde salvar, e grava o PDF."""
    if not snapshots:
        return None
    company = catalog.get_company()
    number = catalog.next_quote_number()
    dialog = ExportDialog(company, snapshots, number, parent)
    result = dialog.exec()
    if result == GO_TO_SETTINGS:
        show_page = getattr(parent.window(), "show_page", None)
        if show_page is not None:
            show_page(SETTINGS_PAGE)
        return None
    if result != QDialog.DialogCode.Accepted:
        return None
    try:
        quote = build_client_quote(company, number, date.today(), dialog.items())
    except ValueError as exc:
        QMessageBox.warning(parent, TITLE, str(exc))
        return None
    path, _filter = QFileDialog.getSaveFileName(
        parent, TITLE, _file_name(quote), "PDF (*.pdf)")
    if not path:
        return None
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    try:
        write_pdf(quote, path)
    except Exception as exc:
        QMessageBox.warning(parent, TITLE, f"Não foi possível gravar o PDF: {exc}")
        return None
    catalog.confirm_quote_number(number)
    return Path(path)
