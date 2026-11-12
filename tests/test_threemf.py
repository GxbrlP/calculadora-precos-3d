import json
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

from calculadora3d.core.threemf import ThreeMFError, read_project

FIXTURES = Path(__file__).parent / "fixtures"

MODEL_XML = '<?xml version="1.0"?><model unit="millimeter"/>'


def _novo_caminho(nome: str) -> Path:
    return Path(tempfile.mkdtemp(prefix="calc3d_")) / nome


def _fixture_sintetica(*, weight="10", used_g=("10",), prediction="3600",
                       printer="Bambu Lab A1", objects=1, model_settings=None,
                       plate_index=1) -> Path:
    itens = used_g.items() if isinstance(used_g, dict) else enumerate(used_g, start=1)
    filaments = "".join(
        f'<filament id="{i}" type="PLA" color="#161616" used_m="1.0" used_g="{g}"/>'
        for i, g in itens
    )
    objs = '<object identify_id="1" name="x" skipped="false"/>' * objects
    prediction_meta = ("" if prediction is None
                       else f'<metadata key="prediction" value="{prediction}"/>')
    slice_info = (
        '<?xml version="1.0"?><config><plate>'
        f'<metadata key="index" value="{plate_index}"/>'
        f'{prediction_meta}'
        f'<metadata key="weight" value="{weight}"/>'
        f'{objs}{filaments}</plate></config>'
    )
    caminho = _novo_caminho("sintetica.gcode.3mf")
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("3D/3dmodel.model", MODEL_XML)
        z.writestr("Metadata/slice_info.config", slice_info)
        z.writestr("Metadata/project_settings.config", json.dumps({"printer_model": printer}))
        if model_settings is not None:
            z.writestr("Metadata/model_settings.config", model_settings)
    return caminho


def _model_settings_com_placas(total: int, fatiada: int) -> str:
    """Como o Ctrl+G do Bambu: lista todas as placas, só a exportada tem gcode."""
    placas = "".join(
        '<plate>'
        f'<metadata key="plater_id" value="{i}"/>'
        '<metadata key="gcode_file" value="'
        f'{f"Metadata/plate_{i}.gcode" if i == fatiada else ""}"/>'
        '</plate>'
        for i in range(1, total + 1))
    return f'<?xml version="1.0"?><config>{placas}</config>'


def _placa_exportada(indice: int, total: int = 2, **kwargs) -> Path:
    return _fixture_sintetica(plate_index=indice,
                              model_settings=_model_settings_com_placas(total, indice),
                              **kwargs)


def _arquivo_texto_qualquer() -> Path:
    caminho = _novo_caminho("texto.3mf")
    caminho.write_text("isto nao e um zip")
    return caminho


def _fixture_com_xml_quebrado() -> Path:
    caminho = _novo_caminho("quebrado.3mf")
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("3D/3dmodel.model", MODEL_XML)
        z.writestr("Metadata/slice_info.config", "<config><plate>")
    return caminho


def test_le_fixture_monocolor():
    p = read_project(FIXTURES / "sliced_mono_1plate.3mf")
    assert p.is_sliced is True
    assert p.color_count == 1
    assert p.total_seconds == 11037
    assert p.total_grams == Decimal("33.83")
    assert p.printer_model == "Bambu Lab A1"      # nao "N2S"
    u, = p.usage
    assert (u.slot, u.type, u.color) == (1, "PLA", "#161616")


def test_slots_carregados_mas_nao_usados_nao_contam():
    p = read_project(FIXTURES / "sliced_mono_1plate.3mf")
    assert len(p.usage) == 1


def test_copias_vem_dos_objects_do_slice_info():
    p = read_project(FIXTURES / "sliced_mono_1plate.3mf")
    assert p.copies == 12


def test_placa_sem_fatia_gera_aviso():
    p = read_project(FIXTURES / "sliced_mono_1plate.3mf")
    assert any("2" in w for w in p.warnings)
    assert len(p.plates) == 1


def test_divergencia_de_peso_gera_aviso_e_nao_excecao():
    p = read_project(_fixture_sintetica(weight="20", used_g=["10"]))
    assert p.warnings
    assert p.total_grams == Decimal("10")


def test_projeto_salvo_com_slice_info_vazio_degrada():
    p = read_project(FIXTURES / "saved_project_3colors.3mf")
    assert p.is_sliced is False
    assert p.color_count == 3
    assert p.copies == 1
    assert p.total_seconds == 0


def test_arquivo_so_de_modelo_degrada():
    p = read_project(FIXTURES / "model_only_3colors.3mf")
    assert p.is_sliced is False
    assert p.color_count == 3
    assert p.total_seconds == 0
    assert p.total_grams == Decimal("0")
    assert p.copies == 1


def test_zip_invalido_levanta_threemferror():
    with pytest.raises(ThreeMFError):
        read_project(_arquivo_texto_qualquer())


def test_xml_corrompido_nomeia_a_entrada():
    with pytest.raises(ThreeMFError, match="slice_info.config"):
        read_project(_fixture_com_xml_quebrado())


def test_le_fixture_multicolor():
    p = read_project(FIXTURES / "sliced_multicolor.gcode.3mf")
    assert p.color_count == 3
    assert p.total_seconds == 2181
    assert p.total_grams == Decimal("7.70")
    assert {u.slot: u.grams for u in p.usage} == {
        1: Decimal("3.33"), 2: Decimal("2.03"), 3: Decimal("2.34")}
    assert p.copies == 1


def test_modelo_so_de_modelo_com_pecas_distintas():
    p = read_project(FIXTURES / "model_only_assembly.3mf")
    assert p.is_sliced is False
    assert p.color_count >= 2
    assert p.copies >= 1


def test_zip_sem_modelo_levanta_threemferror():
    caminho = _novo_caminho("sem_modelo.3mf")
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("Metadata/slice_info.config", "<config/>")
    with pytest.raises(ThreeMFError, match="3dmodel.model"):
        read_project(caminho)


def test_fatiado_sem_objects_nao_gera_zero_copias():
    p = read_project(_fixture_sintetica(objects=0))
    assert p.copies == 1


def test_json_corrompido_nomeia_a_entrada():
    caminho = _novo_caminho("json_ruim.3mf")
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("3D/3dmodel.model", MODEL_XML)
        z.writestr("Metadata/project_settings.config", "{nao e json")
    with pytest.raises(ThreeMFError, match="project_settings.config"):
        read_project(caminho)


def test_helper_sintetico_gera_caminhos_distintos():
    assert _fixture_sintetica() != _fixture_sintetica()


def test_fluxo_comprimido_corrompido_nomeia_a_entrada():
    caminho = _novo_caminho("truncado.3mf")
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("3D/3dmodel.model", MODEL_XML * 200)
    dados = bytearray(caminho.read_bytes())
    inicio = 30 + len("3D/3dmodel.model")
    for i in range(inicio + 2, inicio + 12):
        dados[i] ^= 0xFF
    caminho.write_bytes(bytes(dados))
    with pytest.raises(ThreeMFError, match="3dmodel.model"):
        read_project(caminho)


@pytest.mark.parametrize("used_g", ["NaN", "Infinity"])
def test_valor_nao_finito_levanta_threemferror(used_g):
    with pytest.raises(ThreeMFError, match="slice_info.config"):
        read_project(_fixture_sintetica(used_g=[used_g]))


def test_prediction_infinito_levanta_threemferror():
    with pytest.raises(ThreeMFError, match="slice_info.config"):
        read_project(_fixture_sintetica(prediction="Infinity"))


def test_densidade_e_custo_do_slot_vem_do_project_settings():
    caminho = FIXTURES / "sliced_mono_1plate.3mf"
    with zipfile.ZipFile(caminho) as z:
        settings = json.loads(z.read("Metadata/project_settings.config"))
    u, = read_project(caminho).usage
    assert u.density == Decimal(settings["filament_density"][0]) == Decimal("1.24")
    assert u.cost_per_kg == Decimal(settings["filament_cost"][0]) == Decimal("20")


def test_densidade_e_custo_ausentes_ou_invalidos_viram_none():
    u, = read_project(_fixture_sintetica()).usage
    assert (u.density, u.cost_per_kg) == (None, None)

    caminho = _novo_caminho("lixo.gcode.3mf")
    with zipfile.ZipFile(_fixture_sintetica()) as origem, zipfile.ZipFile(caminho, "w") as z:
        for nome in origem.namelist():
            if nome != "Metadata/project_settings.config":
                z.writestr(nome, origem.read(nome))
        z.writestr("Metadata/project_settings.config", json.dumps(
            {"filament_density": ["abc"], "filament_cost": [""]}))
    u, = read_project(caminho).usage
    assert (u.density, u.cost_per_kg) == (None, None)


def test_placa_fatiada_sem_filamento_gera_aviso():
    p = read_project(_fixture_sintetica(weight="0", used_g=()))
    assert p.is_sliced is True
    assert p.total_grams == Decimal("0")
    assert any("placa 1" in w and "peso" in w for w in p.warnings)


def test_placa_fatiada_so_com_filamento_zerado_gera_aviso():
    p = read_project(_fixture_sintetica(weight="0", used_g=("0",)))
    assert any("placa 1" in w and "peso" in w for w in p.warnings)


def test_placa_fatiada_sem_tempo_gera_aviso():
    p = read_project(_fixture_sintetica(prediction=None))
    assert p.total_seconds == 0
    assert any("placa 1" in w and "tempo" in w for w in p.warnings)


def test_placa_fatiada_completa_nao_gera_aviso_de_dado_ausente():
    p = read_project(_fixture_sintetica())
    assert not any("não informa" in w for w in p.warnings)


def test_placa_nao_fatiada_de_um_arquivo_so_continua_avisando():
    p = read_project(_placa_exportada(1))
    assert any("placa 2 não foi fatiada" in w for w in p.warnings)
