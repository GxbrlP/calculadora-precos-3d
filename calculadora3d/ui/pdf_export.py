"""Escrita do orçamento em PDF (A4) e diálogo de salvar, compartilhados pelas páginas."""
import re
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from calculadora3d.core.export import quote_to_html

TITLE = "Exportar orçamento"


def write_pdf(html: str, path: Path | str) -> None:
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
    document = QTextDocument()
    document.setHtml(html)
    document.print_(writer)


def export_quote_pdf(parent: QWidget, snapshot: dict) -> Path | None:
    """Pergunta onde salvar e grava o PDF; devolve o caminho ou None."""
    base = re.sub(r'[\\/:*?"<>|]+', "_", str(snapshot["project_name"])).strip() or "orcamento"
    path, _filter = QFileDialog.getSaveFileName(
        parent, TITLE, f"{base}.pdf", "PDF (*.pdf)")
    if not path:
        return None
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    try:
        write_pdf(quote_to_html(snapshot), path)
    except Exception as exc:
        QMessageBox.warning(parent, TITLE, f"Não foi possível gravar o PDF: {exc}")
        return None
    return Path(path)
