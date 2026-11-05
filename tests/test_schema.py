"""Tests del validador de storyboard (storyboard/schema.py)."""

import copy
import json
from pathlib import Path

import pytest

from storyboard.schema import (
    ajustar_duraciones,
    cargar_catalogo,
    extender_catalogo,
    validar_storyboard,
)

RAIZ = Path(__file__).resolve().parent.parent


def _storyboard_valido() -> dict:
    return {
        "version": 1,
        "trabajo_id": "lapiz_001",
        "formato": "short",
        "fps": 24,
        "resolucion": [1080, 1920],
        "calidad": "rapida",
        "elenco": {
            "trader": {
                "tipo": "persona",
                "params": {
                    "edad": "adulto",
                    "complexion": "media",
                    "ropa": "comerciante_1890",
                    "pelo": "corto_castano",
                    "barba": "bigote",
                    "piel": "#c68642",
                },
            },
            "lapiz": {
                "tipo": "prop",
                "nombre": "lapiz",
                "params": {"color": "#f2c200"},
            },
        },
        "escenas": [
            {
                "id": "e01",
                "duracion": 4.2,
                "set": "taller_1890",
                "luz": "interior_calido",
                "camara": {
                    "movimiento": "dolly_in",
                    "desde": "plano_general",
                    "hasta": "plano_medio",
                    "objetivo": "trader",
                },
                "actores": [
                    {
                        "ref": "trader",
                        "pos": [-1.0, 0.0],
                        "mira_a": "camara",
                        "acciones": [
                            {"t": 0.0, "accion": "idle", "expresion": "neutral"},
                            {"t": 0.5, "accion": "caminar_hasta", "pos": [0.5, 0.2]},
                            {"t": 2.0, "accion": "levantar", "objeto": "lapiz"},
                            {"t": 3.0, "expresion": "sorpresa"},
                        ],
                    }
                ],
                "props": [{"ref": "lapiz", "pos": [0.6, 0.3], "sobre": "mesa"}],
                "texto_narracion": "In 1890 a humble pencil changed how merchants kept their books.",
            },
            {
                "id": "e02",
                "duracion": 3.8,
                "set": "escritorio_estudio",
                "luz": "dia",
                "camara": {
                    "movimiento": "fijo",
                    "desde": "plano_medio",
                    "hasta": "primer_plano",
                    "objetivo": "trader",
                },
                "actores": [
                    {
                        "ref": "trader",
                        "pos": [0.0, 0.0],
                        "mira_a": "lapiz",
                        "acciones": [
                            {"t": 0.0, "accion": "hablar", "expresion": "feliz"},
                            {"t": 1.5, "accion": "senalar", "objetivo": "lapiz"},
                        ],
                    }
                ],
                "props": [{"ref": "lapiz", "pos": [0.3, 0.1], "sobre": "mesa"}],
                "texto_narracion": "It was cheap, portable and never spilled.",
            },
        ],
        "assets_nuevos": [],
    }


@pytest.fixture
def catalogo() -> dict:
    return cargar_catalogo()


@pytest.fixture
def sb() -> dict:
    return _storyboard_valido()


def _hay_error(errores: list[str], fragmento: str) -> bool:
    return any(fragmento in e for e in errores)


# ---------------------------------------------------------------- catálogo


def test_cargar_catalogo_por_defecto(catalogo):
    assert catalogo["version"] == 1
    assert "taller_1890" in catalogo["sets"]
    assert catalogo["formatos"]["short"] == [1080, 1920]


def test_cargar_catalogo_ruta_explicita(tmp_path):
    ruta = tmp_path / "c.json"
    ruta.write_text(json.dumps({"version": 1, "sets": {}}), encoding="utf-8")
    assert cargar_catalogo(ruta) == {"version": 1, "sets": {}}


def test_extender_catalogo_no_muta_original(catalogo):
    original = copy.deepcopy(catalogo)
    ext = extender_catalogo(
        catalogo,
        [
            {"nombre": "imprenta_gutenberg", "tipo": "set", "descripcion": "Printing shop", "codigo": "x"},
            {"nombre": "pluma_ganso", "tipo": "prop", "descripcion": "Quill", "codigo": "y"},
        ],
    )
    assert ext["sets"]["imprenta_gutenberg"] == "Printing shop"
    assert ext["props"]["pluma_ganso"] == {}
    assert catalogo == original


def test_extender_catalogo_ignora_entradas_invalidas_sin_lanzar(catalogo):
    ext = extender_catalogo(catalogo, [None, {"nombre": "X"}, {"nombre": "abc", "tipo": "otro"}, "basura"])
    assert ext["sets"] == catalogo["sets"]
    assert ext["props"] == catalogo["props"]


# ---------------------------------------------------------------- válido


def test_storyboard_valido_pasa(sb, catalogo):
    assert validar_storyboard(sb, catalogo) == []


def test_ejemplo_en_disco_valida_con_catalogo_real():
    ruta = RAIZ / "escenas" / "ejemplo_lapiz.json"
    d = json.loads(ruta.read_text(encoding="utf-8"))
    cat = cargar_catalogo(RAIZ / "catalogo.json")
    assert validar_storyboard(d, cat) == []
    assert d == _storyboard_valido()


# ---------------------------------------------------------------- mutaciones


def _set(ruta, valor):
    def mutar(d):
        obj = d
        for k in ruta[:-1]:
            obj = obj[k]
        obj[ruta[-1]] = valor

    return mutar


def _del(ruta):
    def mutar(d):
        obj = d
        for k in ruta[:-1]:
            obj = obj[k]
        del obj[ruta[-1]]

    return mutar


def _append_accion_desordenada(d):
    d["escenas"][0]["actores"][0]["acciones"].append({"t": 1.0, "accion": "asentir"})


def _actor_duplicado(d):
    esc = d["escenas"][0]
    esc["actores"].append(copy.deepcopy(esc["actores"][0]))


def _demasiados_actores(d):
    for ref in ("bb", "cc"):
        d["elenco"][ref] = copy.deepcopy(d["elenco"]["trader"])
        d["escenas"][0]["actores"].append(
            {"ref": ref, "pos": [0, 0], "acciones": [{"t": 0, "accion": "idle"}]}
        )


def _id_duplicado(d):
    d["escenas"][1]["id"] = "e01"


E0 = ["escenas", 0]
A0 = E0 + ["actores", 0]
AC = A0 + ["acciones"]

CASOS = [
    ("version", _set(["version"], 2), "version"),
    ("trabajo_id", _set(["trabajo_id"], ""), "trabajo_id"),
    ("formato", _set(["formato"], "cuadrado"), "formato"),
    ("fps", _set(["fps"], 30), "fps"),
    ("resolucion", _set(["resolucion"], [1920, 1080]), "resolucion"),
    ("calidad", _set(["calidad"], "ultra"), "calidad"),
    ("assets_nuevos", _del(["assets_nuevos"]), "assets_nuevos"),
    ("elenco_clave", lambda d: d["elenco"].update({"Mal-Nombre": d["elenco"]["trader"]}), "elenco['Mal-Nombre']"),
    ("elenco_tipo", _set(["elenco", "trader", "tipo"], "animal"), "elenco['trader'].tipo"),
    ("persona_param_falta", _del(["elenco", "trader", "params", "barba"]), "elenco['trader'].params.barba"),
    ("persona_param_invalido", _set(["elenco", "trader", "params", "ropa"], "astronauta"), "elenco['trader'].params.ropa"),
    ("persona_piel", _set(["elenco", "trader", "params", "piel"], "marron"), "elenco['trader'].params.piel"),
    ("prop_nombre", _set(["elenco", "lapiz", "nombre"], "espada"), "elenco['lapiz'].nombre"),
    ("prop_color", _set(["elenco", "lapiz", "params", "color"], "amarillo"), "elenco['lapiz'].params.color"),
    ("escena_id", _set(E0 + ["id"], "escena1"), "escenas[0].id"),
    ("escena_id_dup", _id_duplicado, "escenas[1].id"),
    ("duracion_alta", _set(E0 + ["duracion"], 25.0), "escenas[0].duracion"),
    ("duracion_baja", _set(E0 + ["duracion"], 0.5), "escenas[0].duracion"),
    ("set", _set(E0 + ["set"], "luna"), "escenas[0].set"),
    ("luz", _set(E0 + ["luz"], "neon"), "escenas[0].luz"),
    ("camara_mov", _set(E0 + ["camara", "movimiento"], "zoom"), "escenas[0].camara.movimiento"),
    ("camara_plano", _set(E0 + ["camara", "hasta"], "gran_angular"), "escenas[0].camara.hasta"),
    ("camara_objetivo", _set(E0 + ["camara", "objetivo"], "lapiz"), "escenas[0].camara.objetivo"),
    ("demasiados_actores", _demasiados_actores, "escenas[0].actores"),
    ("actor_ref", _set(A0 + ["ref"], "fantasma"), "escenas[0].actores[0].ref"),
    ("actor_ref_prop", _set(A0 + ["ref"], "lapiz"), "escenas[0].actores[0].ref"),
    ("actor_dup", _actor_duplicado, "escenas[0].actores[1].ref"),
    ("actor_pos", _set(A0 + ["pos"], [5.0, 0.0]), "escenas[0].actores[0].pos"),
    ("mira_a", _set(A0 + ["mira_a"], "nadie"), "escenas[0].actores[0].mira_a"),
    ("acciones_vacias", _set(A0 + ["acciones"], []), "escenas[0].actores[0].acciones"),
    ("acciones_orden", _append_accion_desordenada, "escenas[0].actores[0].acciones[4]"),
    ("accion_t_fuera", _set(AC + [3, "t"], 4.2), "escenas[0].actores[0].acciones[3].t"),
    ("accion_desconocida", _set(AC + [0, "accion"], "bailar"), "escenas[0].actores[0].acciones[0]: accion 'bailar'"),
    ("expresion", _set(AC + [3, "expresion"], "asco"), "escenas[0].actores[0].acciones[3]: expresion 'asco'"),
    ("accion_sin_nada", _set(AC + [3], {"t": 3.0}), "escenas[0].actores[0].acciones[3]"),
    ("param_xy", _set(AC + [1, "pos"], [9, 9]), "escenas[0].actores[0].acciones[1].pos"),
    ("param_xy_falta", _del(AC + [1, "pos"]), "escenas[0].actores[0].acciones[1].pos"),
    ("param_prop", _set(AC + [2, "objeto"], "trader"), "escenas[0].actores[0].acciones[2].objeto"),
    ("param_ref", _set(["escenas", 1, "actores", 0, "acciones", 1, "objetivo"], "fantasma"), "escenas[1].actores[0].acciones[1].objetivo"),
    ("prop_ref", _set(E0 + ["props", 0, "ref"], "trader"), "escenas[0].props[0].ref"),
    ("prop_sobre", _set(E0 + ["props", 0, "sobre"], "techo"), "escenas[0].props[0].sobre"),
    ("prop_pos", _set(E0 + ["props", 0, "pos"], [0, "a"]), "escenas[0].props[0].pos"),
    ("narracion", _set(E0 + ["texto_narracion"], ""), "escenas[0].texto_narracion"),
]


@pytest.mark.parametrize("nombre,mutar,fragmento", CASOS, ids=[c[0] for c in CASOS])
def test_violacion_reporta_ubicacion(sb, catalogo, nombre, mutar, fragmento):
    mutar(sb)
    errores = validar_storyboard(sb, catalogo)
    assert errores, f"{nombre}: expected errors"
    assert _hay_error(errores, fragmento), errores


def test_mensaje_lista_opciones_validas(sb, catalogo):
    sb["escenas"][0]["actores"][0]["acciones"][0]["accion"] = "bailar"
    errores = validar_storyboard(sb, catalogo)
    assert any("valid:" in e and "caminar_hasta" in e for e in errores), errores


# ---------------------------------------------------------------- malformados


@pytest.mark.parametrize(
    "mutar,fragmento",
    [
        (_set(["escenas"], "no-lista"), "escenas"),
        (_set(["elenco"], None), "elenco"),
        (_del(A0 + ["pos"]), "escenas[0].actores[0].pos"),
        (_set(E0 + ["camara"], 7), "escenas[0].camara"),
        (_set(E0 + ["actores"], [None]), "escenas[0].actores[0]"),
        (_set(AC, [{"t": "cero", "accion": "idle"}]), "escenas[0].actores[0].acciones[0].t"),
        (_set(E0 + ["duracion"], "mucho"), "escenas[0].duracion"),
        (_set(["escenas"], [42]), "escenas[0]"),
        (_set(["assets_nuevos"], [None]), "assets_nuevos[0]"),
    ],
)
def test_malformado_no_lanza(sb, catalogo, mutar, fragmento):
    mutar(sb)
    errores = validar_storyboard(sb, catalogo)
    assert _hay_error(errores, fragmento), errores


@pytest.mark.parametrize("entrada", [None, [], "x", 3, {}])
def test_entrada_no_dict_no_lanza(catalogo, entrada):
    assert validar_storyboard(entrada, catalogo)


# ---------------------------------------------------------------- assets_nuevos


def test_set_nuevo_requiere_asset_declarado(sb, catalogo):
    sb["escenas"][0]["set"] = "imprenta_gutenberg"
    assert _hay_error(validar_storyboard(sb, catalogo), "escenas[0].set")

    sb["assets_nuevos"] = [
        {"nombre": "imprenta_gutenberg", "tipo": "set", "descripcion": "Gutenberg press shop", "codigo": "def construir(): pass"}
    ]
    assert validar_storyboard(sb, catalogo) == []


def test_prop_nuevo_declarado(sb, catalogo):
    sb["elenco"]["pluma"] = {"tipo": "prop", "nombre": "pluma_ganso"}
    assert _hay_error(validar_storyboard(sb, catalogo), "elenco['pluma'].nombre")
    sb["assets_nuevos"] = [{"nombre": "pluma_ganso", "tipo": "prop", "descripcion": "Quill", "codigo": "pass"}]
    assert validar_storyboard(sb, catalogo) == []


@pytest.mark.parametrize(
    "asset,fragmento",
    [
        ({"nombre": "Imprenta!", "tipo": "set", "descripcion": "d", "codigo": "c"}, "assets_nuevos[0].nombre"),
        ({"nombre": "imprenta", "tipo": "vehiculo", "descripcion": "d", "codigo": "c"}, "assets_nuevos[0].tipo"),
        ({"nombre": "imprenta", "tipo": "set", "descripcion": "d"}, "assets_nuevos[0].codigo"),
    ],
)
def test_asset_invalido_da_error(sb, catalogo, asset, fragmento):
    sb["assets_nuevos"] = [asset]
    assert _hay_error(validar_storyboard(sb, catalogo), fragmento)


# ---------------------------------------------------------------- audio


def test_duracion_audio_coincide(sb, catalogo):
    assert validar_storyboard(sb, catalogo, duracion_audio=8.03) == []


def test_duracion_audio_no_coincide(sb, catalogo):
    errores = validar_storyboard(sb, catalogo, duracion_audio=9.5)
    assert any("8.0" in e and "9.5" in e for e in errores), errores


# ---------------------------------------------------------------- ajustar_duraciones


def test_ajustar_duraciones_redondea_y_recorta_t(sb):
    nuevo = ajustar_duraciones(sb, [2.5, 4.12345])
    assert nuevo["escenas"][0]["duracion"] == 2.5
    assert nuevo["escenas"][1]["duracion"] == 4.123
    ts = [a["t"] for a in nuevo["escenas"][0]["actores"][0]["acciones"]]
    assert ts == [0.0, 0.5, 2.0, 2.3]
    # el original no se modifica
    assert sb["escenas"][0]["duracion"] == 4.2
    assert sb["escenas"][0]["actores"][0]["acciones"][3]["t"] == 3.0


def test_ajustar_duraciones_resultado_valida(sb, catalogo):
    nuevo = ajustar_duraciones(sb, [2.5, 4.0])
    assert validar_storyboard(nuevo, catalogo, duracion_audio=6.5) == []


def test_ajustar_duraciones_clamp_no_negativo(sb):
    nuevo = ajustar_duraciones(sb, [0.1, 3.8])
    ts = [a["t"] for a in nuevo["escenas"][0]["actores"][0]["acciones"]]
    assert all(t == 0.0 for t in ts)


def test_ajustar_duraciones_largo_distinto(sb):
    with pytest.raises(ValueError):
        ajustar_duraciones(sb, [1.0])


def test_estilo_opcional_valido_e_invalido():
    import copy
    cat = cargar_catalogo()
    base = json.loads((Path(__file__).resolve().parents[1] / "escenas" / "ejemplo_lapiz.json").read_text(encoding="utf-8"))
    for estilo in ("caricatura", "realista", "plano"):
        d = copy.deepcopy(base)
        d["estilo"] = estilo
        assert validar_storyboard(d, cat) == []
    d = copy.deepcopy(base)
    d["estilo"] = "anime"
    errores = validar_storyboard(d, cat)
    assert any(e.startswith("estilo:") and "anime" in e for e in errores)
