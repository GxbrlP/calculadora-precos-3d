import json
import os.path
import re
import zipfile
import zlib
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from collections.abc import Sequence
from pathlib import Path
from xml.etree import ElementTree

from calculadora3d.core.models import FilamentUsage, Plate, SlicedProject

MODEL = "3D/3dmodel.model"
PROJECT_SETTINGS = "Metadata/project_settings.config"
SLICE_INFO = "Metadata/slice_info.config"
MODEL_SETTINGS = "Metadata/model_settings.config"

DIVERGENCE_LIMIT = Decimal("0.02")


class ThreeMFError(Exception):
    pass


def _read_entry(zf: zipfile.ZipFile, name: str, required: bool = False) -> bytes | None:
    try:
        return zf.read(name)
    except KeyError:
        if required:
            raise ThreeMFError(f"entrada obrigatória ausente no .3mf: {name}") from None
        return None
    except (zipfile.BadZipFile, OSError, RuntimeError, zipfile.LargeZipFile,
            zlib.error, EOFError) as exc:
        raise ThreeMFError(f"não foi possível ler {name}: {exc}") from exc


def _parse_xml(zf: zipfile.ZipFile, name: str) -> ElementTree.Element | None:
    data = _read_entry(zf, name)
    if data is None:
        return None
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ThreeMFError(f"XML inválido em {name}: {exc}") from exc


def _parse_json(zf: zipfile.ZipFile, name: str) -> dict:
    data = _read_entry(zf, name)
    if data is None:
        return {}
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ThreeMFError(f"JSON inválido em {name}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ThreeMFError(f"JSON inválido em {name}: esperado um objeto")
    return parsed


def _decimal(value: str | None, entry: str, what: str) -> Decimal:
    try:
        result = Decimal((value or "").strip())
    except InvalidOperation:
        raise ThreeMFError(f"valor inválido para {what} em {entry}: {value!r}") from None
    if not result.is_finite():
        raise ThreeMFError(f"valor inválido para {what} em {entry}: {value!r}")
    return result


def _int(value: str | None, entry: str, what: str) -> int:
    try:
        return int(Decimal((value or "").strip()))
    except (InvalidOperation, ValueError, OverflowError):
        raise ThreeMFError(f"valor inválido para {what} em {entry}: {value!r}") from None


def _meta(node: ElementTree.Element) -> dict[str, str]:
    return {m.get("key", ""): m.get("value", "") for m in node.findall("metadata")}


def _array_at(settings: dict, key: str, slot: int) -> str | None:
    values = settings.get(key)
    if isinstance(values, list) and 0 < slot <= len(values):
        item = values[slot - 1]
        return None if item is None else str(item)
    return None


def _optional_decimal_at(settings: dict, key: str, slot: int) -> Decimal | None:
    raw = _array_at(settings, key, slot)
    try:
        value = Decimal((raw or "").strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _default_name(path: Path) -> str:
    name = path.name
    for suffix in (".gcode.3mf", ".3mf"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _project_name(model_settings: ElementTree.Element | None, path: Path) -> str:
    if model_settings is not None:
        for obj in model_settings.findall("object"):
            name = _meta(obj).get("name", "").strip()
            if name:
                return name
    return _default_name(path)


def _plates_from_slice_info(root: ElementTree.Element) -> tuple[list[Plate], list[FilamentUsage], list[str]]:
    plates: list[Plate] = []
    usage_by_slot: dict[int, FilamentUsage] = {}
    warnings: list[str] = []
    for position, plate_node in enumerate(root.findall("plate"), start=1):
        meta = _meta(plate_node)
        index = _int(meta.get("index", str(position)), SLICE_INFO, "index da placa")
        weight = _decimal(meta.get("weight", "0"), SLICE_INFO, "weight")
        instances = sum(
            1 for o in plate_node.findall("object") if o.get("skipped", "false").lower() != "true"
        )
        seconds = _int(meta.get("prediction", "0"), SLICE_INFO, "prediction")
        plates.append(Plate(
            index=index,
            seconds=seconds,
            weight_grams=weight,
            instances=instances,
            skipped=False,
        ))
        if seconds <= 0:
            warnings.append(f"placa {index}: o arquivo não informa o tempo de impressão")
        plate_sum = Decimal(0)
        for f in plate_node.findall("filament"):
            grams = _decimal(f.get("used_g", "0"), SLICE_INFO, "used_g")
            plate_sum += grams
            if grams <= 0:
                continue
            slot = _int(f.get("id"), SLICE_INFO, "id do filamento")
            meters = _decimal(f.get("used_m", "0"), SLICE_INFO, "used_m")
            previous = usage_by_slot.get(slot)
            if previous:
                grams += previous.grams
                meters += previous.meters
            usage_by_slot[slot] = FilamentUsage(
                slot=slot, type=f.get("type", ""), color=f.get("color", ""),
                grams=grams, meters=meters, vendor=None, settings_id=None,
            )
        if plate_sum <= 0:
            warnings.append(f"placa {index}: o arquivo não informa o peso do filamento")
        elif weight > 0 and abs(plate_sum - weight) / weight > DIVERGENCE_LIMIT:
            warnings.append(
                f"placa {index}: a soma do filamento ({plate_sum} g) diverge do peso "
                f"informado pelo fatiador ({weight} g)"
            )
    return plates, [usage_by_slot[s] for s in sorted(usage_by_slot)], warnings


def _enrich(usage: FilamentUsage, settings: dict) -> FilamentUsage:
    slot = usage.slot
    return FilamentUsage(
        slot=slot,
        type=usage.type or _array_at(settings, "filament_type", slot) or "",
        color=usage.color or _array_at(settings, "filament_colour", slot) or "",
        grams=usage.grams,
        meters=usage.meters,
        vendor=_array_at(settings, "filament_vendor", slot),
        settings_id=_array_at(settings, "filament_settings_id", slot),
        density=_optional_decimal_at(settings, "filament_density", slot),
        cost_per_kg=_optional_decimal_at(settings, "filament_cost", slot),
    )


def _extruders(model_settings: ElementTree.Element | None) -> list[int]:
    found: set[int] = set()
    if model_settings is not None:
        for obj in model_settings.findall("object"):
            for node in [obj, *obj.findall("part")]:
                value = _meta(node).get("extruder", "").strip()
                if value.isdigit() and int(value) > 0:
                    found.add(int(value))
    return sorted(found)


def _unsliced_warning(index: int) -> str:
    return f"a placa {index} não foi fatiada e não entra na soma"


def _unsliced_plates(model_settings: ElementTree.Element | None,
                     sliced_indexes: set[int]) -> list[int]:
    unsliced = []
    if model_settings is None:
        return unsliced
    for position, plate in enumerate(model_settings.findall("plate"), start=1):
        meta = _meta(plate)
        index = _int(meta.get("plater_id", str(position)), MODEL_SETTINGS, "plater_id")
        if not meta.get("gcode_file", "").strip() or index not in sliced_indexes:
            unsliced.append(index)
    return unsliced


def read_project(path: Path) -> SlicedProject:
    path = Path(path)
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ThreeMFError(f"arquivo .3mf inválido ({path.name}): {exc}") from exc
    with zf:
        _read_entry(zf, MODEL, required=True)
        settings = _parse_json(zf, PROJECT_SETTINGS)
        slice_info = _parse_xml(zf, SLICE_INFO)
        model_settings = _parse_xml(zf, MODEL_SETTINGS)

    printer = settings.get("printer_model")
    printer_model = str(printer) if printer else None
    name = _project_name(model_settings, path)

    plates: list[Plate] = []
    warnings: list[str] = []
    usage: list[FilamentUsage] = []
    if slice_info is not None:
        plates, usage, warnings = _plates_from_slice_info(slice_info)

    if plates:
        usage = [_enrich(u, settings) for u in usage]
        unsliced = _unsliced_plates(model_settings, {p.index for p in plates})
        warnings += [_unsliced_warning(i) for i in unsliced]
        return SlicedProject(
            name=name, source_path=path, printer_model=printer_model,
            plates=tuple(plates), usage=tuple(usage), is_sliced=True,
            warnings=tuple(warnings), sources=(path,), unsliced_plates=tuple(unsliced),
        )

    slots = _extruders(model_settings) or [1]
    usage = [
        _enrich(FilamentUsage(s, "", "", Decimal(0), Decimal(0), None, None), settings)
        for s in slots
    ]
    instances = len(model_settings.findall(".//model_instance")) if model_settings is not None else 0
    return SlicedProject(
        name=name, source_path=path, printer_model=printer_model,
        plates=(), usage=tuple(usage), is_sliced=False,
        warnings=tuple(warnings), sources=(path,), model_instances=instances,
    )


_PLATE_SUFFIX = re.compile(r"[_\-\s]*plate[_\-\s]*\d+$", re.IGNORECASE)
_SEPARATORS = "_- ."


def _common_name(projects: list[SlicedProject]) -> str:
    names = [p.name for p in projects]
    if len(set(names)) == 1:
        return names[0]
    stems = [_PLATE_SUFFIX.sub("", _default_name(p.source_path)) for p in projects]
    prefix = os.path.commonprefix(stems).strip(_SEPARATORS)
    return prefix or names[0]


def _merge_usage(projects: list[SlicedProject]) -> list[FilamentUsage]:
    merged: dict[int, FilamentUsage] = {}
    for project in projects:
        for u in project.usage:
            previous = merged.get(u.slot)
            if previous is None:
                merged[u.slot] = u
            else:
                merged[u.slot] = replace(
                    previous, grams=previous.grams + u.grams,
                    meters=previous.meters + u.meters)
    return [merged[s] for s in sorted(merged)]


def read_projects(paths: Sequence[Path]) -> SlicedProject:
    unique: list[Path] = []
    seen: set[Path] = set()
    warnings: list[str] = []
    for raw in paths:
        path = Path(raw)
        key = path.resolve()
        if key in seen:
            warnings.append(f"arquivo repetido ignorado: {path.name}")
            continue
        seen.add(key)
        unique.append(path)
    if not unique:
        raise ThreeMFError("nenhum arquivo .3mf informado")

    projects = [read_project(p) for p in unique]
    first = projects[0]
    # índices originais das placas, antes da renumeração abaixo
    covered = {pl.index for p in projects for pl in p.plates}
    any_sliced = any(p.is_sliced for p in projects)
    for project in projects:
        name = project.source_path.name
        summed_elsewhere = {_unsliced_warning(i) for i in project.unsliced_plates
                            if i in covered}
        for w in project.warnings:
            if w not in summed_elsewhere:
                warnings.append(f"{name}: {w}")
        if any_sliced and not project.is_sliced:
            warnings.append(f"{name} não foi fatiado: some o peso e o tempo dele"
                            " aos valores pré-preenchidos")
        if project.printer_model != first.printer_model:
            warnings.append(
                f"{project.source_path.name}: impressora diferente "
                f"({project.printer_model or 'desconhecida'}) da do primeiro arquivo "
                f"({first.printer_model or 'desconhecida'})")

    plates = [
        replace(plate, index=i)
        for i, plate in enumerate((pl for p in projects for pl in p.plates), start=1)
    ]
    return SlicedProject(
        name=_common_name(projects), source_path=first.source_path,
        printer_model=first.printer_model, plates=tuple(plates),
        usage=tuple(_merge_usage(projects)),
        is_sliced=all(p.is_sliced for p in projects),
        warnings=tuple(warnings), sources=tuple(unique),
        model_instances=sum(p.model_instances for p in projects),
        unsliced_plates=tuple(sorted(
            {i for p in projects for i in p.unsliced_plates} - covered)),
    )
