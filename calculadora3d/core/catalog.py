"""Catálogo persistente (SQLite): marcas, filamentos, impressoras, ajustes e histórico."""
import sqlite3
from dataclasses import dataclass, fields
from decimal import Decimal
from pathlib import Path

from calculadora3d.core.pricing import FilamentLine, PrinterCosts

# Valores monetários e decimais ficam em TEXT para guardar Decimal sem perda.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS filaments (
    id INTEGER PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES brands(id),
    line TEXT NOT NULL,
    type TEXT NOT NULL,
    roll_grams TEXT NOT NULL,
    roll_price TEXT NOT NULL,
    density TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS printers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    model_id TEXT NOT NULL DEFAULT '',
    average_watts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS task_presets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    minutes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_file TEXT NOT NULL DEFAULT '',
    total_cost TEXT NOT NULL,
    retail_price TEXT NOT NULL,
    snapshot_json TEXT NOT NULL
);
"""

# Colunas da impressora que deixaram de existir (só a energia entra no custo).
_DROPPED_PRINTER_COLUMNS = ("purchase_price", "lifetime_hours", "maintenance_per_hour")


@dataclass(frozen=True)
class Brand:
    id: int | None
    name: str


@dataclass(frozen=True)
class Filament:
    id: int | None
    brand_id: int
    brand_name: str
    line: str
    type: str
    roll_grams: Decimal
    roll_price: Decimal
    density: Decimal | None
    active: bool

    @property
    def price_per_kg(self) -> Decimal:
        if self.roll_grams == 0:
            return Decimal("0")
        return self.roll_price / self.roll_grams * 1000

    def as_filament_line(self, grams: Decimal) -> FilamentLine:
        return FilamentLine(grams, self.roll_price, self.roll_grams)


@dataclass(frozen=True)
class Printer:
    id: int | None
    name: str
    model_id: str
    average_watts: Decimal

    def as_printer_costs(self) -> PrinterCosts:
        return PrinterCosts(self.average_watts)


@dataclass(frozen=True)
class TaskPreset:
    id: int | None
    name: str
    minutes: int


@dataclass(frozen=True)
class Settings:
    kwh_price: Decimal = Decimal("0.95")
    failure_rate: Decimal = Decimal("0.05")
    labor_hourly: Decimal = Decimal("25.00")
    packaging: Decimal = Decimal("1.50")
    retail_margin: Decimal = Decimal("0.6")
    wholesale_margin: Decimal = Decimal("0.4")
    wholesale_min_quantity: int = 10
    minimum_margin: Decimal = Decimal("0.2")
    rounding_step: Decimal = Decimal("0.50")


@dataclass(frozen=True)
class CompanyInfo:
    """Dados da empresa impressos no orçamento do cliente; só nome e endereço são obrigatórios."""
    name: str = ""
    address: str = ""
    phone: str = ""
    site: str = ""
    email: str = ""
    social: str = ""


_COMPANY_PREFIX = "company_"
_LAST_QUOTE_NUMBER = "last_quote_number"

_MARGIN_FIELDS = ("retail_margin", "wholesale_margin", "minimum_margin")
_NON_NEGATIVE_FIELDS = ("kwh_price", "labor_hourly", "packaging",
                        "rounding_step", "wholesale_min_quantity")


def _validate_settings(s: Settings) -> None:
    for name in _MARGIN_FIELDS:
        if not 0 <= getattr(s, name) < 1:
            raise ValueError(f"A margem ({name}) deve estar entre 0 e 1 (exclusive).")
    if not 0 <= s.failure_rate < 1:
        raise ValueError("A taxa de falha deve estar entre 0 e 1 (exclusive).")
    for name in _NON_NEGATIVE_FIELDS:
        if getattr(s, name) < 0:
            raise ValueError(f"O valor de {name} não pode ser negativo.")


def _filament_from_row(r: sqlite3.Row) -> Filament:
    return Filament(r["id"], r["brand_id"], r["brand_name"], r["line"], r["type"],
                    Decimal(r["roll_grams"]), Decimal(r["roll_price"]),
                    Decimal(r["density"]) if r["density"] else None,
                    bool(r["active"]))


def _printer_from_row(r: sqlite3.Row) -> Printer:
    return Printer(r["id"], r["name"], r["model_id"], Decimal(r["average_watts"]))


class Catalog:
    def __init__(self, db_path: Path) -> None:
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def migrate(self) -> None:
        with self.connection:
            self.connection.executescript(_SCHEMA)
            existing = {r["name"] for r in
                        self.connection.execute("PRAGMA table_info(printers)")}
            for column in _DROPPED_PRINTER_COLUMNS:
                if column in existing:
                    self.connection.execute(f"ALTER TABLE printers DROP COLUMN {column}")

    def close(self) -> None:
        self.connection.close()

    def _insert_or_update(self, table: str, row_id: int | None,
                          values: dict[str, object]) -> int:
        with self.connection:
            if row_id is None:
                cols = ", ".join(values)
                marks = ", ".join("?" for _ in values)
                cur = self.connection.execute(
                    f"INSERT INTO {table} ({cols}) VALUES ({marks})",
                    tuple(values.values()))
                return int(cur.lastrowid)
            sets = ", ".join(f"{c} = ?" for c in values)
            self.connection.execute(f"UPDATE {table} SET {sets} WHERE id = ?",
                                    (*values.values(), row_id))
            return row_id

    # Marcas
    def add_brand(self, name: str) -> int:
        with self.connection:
            cur = self.connection.execute(
                "INSERT INTO brands (name) VALUES (?)", (name.strip(),))
        return int(cur.lastrowid)

    def list_brands(self) -> list[Brand]:
        rows = self.connection.execute("SELECT id, name FROM brands ORDER BY name")
        return [Brand(r["id"], r["name"]) for r in rows]

    def delete_brand(self, brand_id: int) -> None:
        in_use = self.connection.execute(
            "SELECT COUNT(*) FROM filaments WHERE brand_id = ?", (brand_id,)
        ).fetchone()[0]
        if in_use:
            raise ValueError(
                "Não é possível excluir a marca: ainda há filamentos cadastrados nela.")
        with self.connection:
            self.connection.execute("DELETE FROM brands WHERE id = ?", (brand_id,))

    # Filamentos
    def upsert_filament(self, f: Filament) -> int:
        return self._insert_or_update("filaments", f.id, {
            "brand_id": f.brand_id, "line": f.line, "type": f.type,
            "roll_grams": str(f.roll_grams), "roll_price": str(f.roll_price),
            "density": "" if f.density is None else str(f.density),
            "active": int(f.active)})

    def list_filaments(self, active_only: bool = True) -> list[Filament]:
        where = "WHERE f.active = 1" if active_only else ""
        rows = self.connection.execute(
            "SELECT f.*, b.name AS brand_name FROM filaments f"
            f" JOIN brands b ON b.id = f.brand_id {where}"
            " ORDER BY b.name, f.line")
        return [_filament_from_row(r) for r in rows]

    def delete_filament(self, filament_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM filaments WHERE id = ?",
                                    (filament_id,))

    # Impressoras
    def upsert_printer(self, p: Printer) -> int:
        return self._insert_or_update("printers", p.id, {
            "name": p.name, "model_id": p.model_id,
            "average_watts": str(p.average_watts)})

    def list_printers(self) -> list[Printer]:
        rows = self.connection.execute("SELECT * FROM printers ORDER BY name, id")
        return [_printer_from_row(r) for r in rows]

    def delete_printer(self, printer_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM printers WHERE id = ?",
                                    (printer_id,))

    def find_printer_by_model(self, model_id: str) -> Printer | None:
        wanted = model_id.strip().lower()
        if not wanted:
            return None
        row = self.connection.execute(
            "SELECT * FROM printers WHERE lower(trim(model_id)) = ? ORDER BY id",
            (wanted,)).fetchone()
        return _printer_from_row(row) if row else None

    # Configurações
    def get_settings(self) -> Settings:
        stored = {r["key"]: r["value"] for r in
                  self.connection.execute("SELECT key, value FROM settings")}
        defaults = Settings()
        values = {}
        for fld in fields(Settings):
            raw = stored.get(fld.name)
            default = getattr(defaults, fld.name)
            if raw is None:
                values[fld.name] = default
            elif fld.name == "wholesale_min_quantity":
                values[fld.name] = int(raw)
            else:
                values[fld.name] = Decimal(raw)
        return Settings(**values)

    def save_settings(self, settings: Settings) -> None:
        _validate_settings(settings)
        with self.connection:
            self.connection.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [(f.name, str(getattr(settings, f.name))) for f in fields(Settings)])

    # Dados da empresa e numeração do orçamento (mesma tabela settings, chaves próprias)
    def _setting(self, key: str) -> str | None:
        row = self.connection.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return None if row is None else row["value"]

    def _put_settings(self, items: list[tuple[str, str]]) -> None:
        with self.connection:
            self.connection.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value", items)

    def get_company(self) -> CompanyInfo:
        return CompanyInfo(**{
            f.name: self._setting(_COMPANY_PREFIX + f.name) or ""
            for f in fields(CompanyInfo)})

    def save_company(self, info: CompanyInfo) -> None:
        self._put_settings([(_COMPANY_PREFIX + f.name, getattr(info, f.name).strip())
                            for f in fields(CompanyInfo)])

    def next_quote_number(self) -> int:
        """Número que o próximo orçamento exportado vai receber (não reserva)."""
        return int(self._setting(_LAST_QUOTE_NUMBER) or 0) + 1

    def confirm_quote_number(self, number: int) -> None:
        """Registra que o orçamento `number` foi exportado; o contador nunca volta."""
        last = int(self._setting(_LAST_QUOTE_NUMBER) or 0)
        self._put_settings([(_LAST_QUOTE_NUMBER, str(max(last, number)))])

    # Presets de tarefa
    def list_task_presets(self) -> list[TaskPreset]:
        rows = self.connection.execute(
            "SELECT id, name, minutes FROM task_presets ORDER BY name, id")
        return [TaskPreset(r["id"], r["name"], int(r["minutes"])) for r in rows]

    def upsert_task_preset(self, t: TaskPreset) -> int:
        return self._insert_or_update("task_presets", t.id, {
            "name": t.name, "minutes": str(t.minutes)})

    def delete_task_preset(self, preset_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM task_presets WHERE id = ?",
                                    (preset_id,))
