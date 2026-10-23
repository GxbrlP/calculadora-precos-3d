"""Gera calculadora3d/resources/icon.png e icon.ico com QPainter."""
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPolygonF

OUT = Path(__file__).resolve().parent.parent / "calculadora3d" / "resources"


def draw(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#1f3a5f"))
    p.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 52 * s, 52 * s)

    cx, cy, r = 128 * s, 128 * s, 78 * s
    top = [(0, -1), (0.866, -0.5), (0, 0), (-0.866, -0.5)]
    left = [(-0.866, -0.5), (0, 0), (0, 1), (-0.866, 0.5)]
    right = [(0.866, -0.5), (0.866, 0.5), (0, 1), (0, 0)]

    def face(pts, color):
        poly = QPolygonF([QPointF(cx + x * r, cy + y * r) for x, y in pts])
        p.setBrush(QColor(color))
        p.setPen(QPen(QColor("#1f3a5f"), max(1.0, 5 * s), Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPolygon(poly)

    face(top, "#f4f7fb")
    face(left, "#7fb4e8")
    face(right, "#3f86d0")
    p.end()
    return img


def write_ico(path: Path, sizes=(16, 32, 48, 64, 128, 256)) -> None:
    """ICO multi-tamanho com entradas PNG (aceito pelo Windows Vista+)."""
    blobs = []
    for size in sizes:
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        draw(size).save(buf, "PNG")
        blobs.append(bytes(data))
    out = bytearray(struct.pack("<HHH", 0, 1, len(sizes)))
    offset = 6 + 16 * len(sizes)
    for size, blob in zip(sizes, blobs):
        dim = 0 if size >= 256 else size
        out += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    for blob in blobs:
        out += blob
    path.write_bytes(bytes(out))


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    OUT.mkdir(parents=True, exist_ok=True)
    draw(256).save(str(OUT / "icon.png"))
    write_ico(OUT / "icon.ico")
    del app


if __name__ == "__main__":
    main()
