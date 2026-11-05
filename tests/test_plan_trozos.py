import json
from pathlib import Path

from herramientas.plan_trozos import cuadros_por_escena, trozos

EJEMPLO = json.loads((Path(__file__).resolve().parents[1] / "escenas" / "ejemplo_lapiz.json").read_text(encoding="utf-8"))


def _sb(duraciones, fps=24):
    return {"fps": fps, "escenas": [{"id": f"e{i + 1:02d}", "duracion": d} for i, d in enumerate(duraciones)]}


def test_cuadros_suman_la_duracion_total_sin_desfase():
    duraciones = [3.33, 4.17, 2.91, 5.05, 3.62, 4.48, 3.71, 2.88, 4.02, 3.95, 4.44, 3.81]
    total = sum(n for _, n in cuadros_por_escena(_sb(duraciones)))
    assert total == round(sum(duraciones) * 24)


def test_cuadros_del_ejemplo():
    assert cuadros_por_escena(EJEMPLO) == [("e01", 101), ("e02", 91)]


def test_trozos_cubren_cada_escena_sin_huecos_ni_solapes():
    lista = trozos(_sb([10.0, 1.0, 7.3]), tamano=72)
    for id_escena, total in cuadros_por_escena(_sb([10.0, 1.0, 7.3])):
        mios = sorted((t["desde"], t["hasta"]) for t in lista if t["escena"] == id_escena)
        assert mios[0][0] == 1 and mios[-1][1] == total
        for (a, b), (c, _d) in zip(mios, mios[1:]):
            assert c == b + 1
        assert all(b - a + 1 <= 72 for a, b in mios)
        assert all(t["total"] == total for t in lista if t["escena"] == id_escena)


def test_nombres_ordenan_en_orden_de_reproduccion():
    lista = trozos(_sb([10.0, 7.3]), tamano=72)
    nombres = [t["nombre"] for t in lista]
    assert nombres == sorted(nombres)
