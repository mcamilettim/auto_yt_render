"""Assets nuevos escritos por Claude: se ejecutan en un espacio de nombres acotado, con respaldo si fallan.

Contrato del código (lo valida `revisar_codigo` antes de ejecutarlo):
  set : def construir():            -> dict opcional {"mesa": (x, y, alto)}; arma piso, paredes y muebles
  prop: def construir(color=None):   -> (raiz, apoyo) ; raiz = empty padre de todas las piezas, apoyo = z del fondo
Solo puede usar los nombres de API_ASSETS (más math y builtins básicos). Sin imports, sin archivos, sin dunder.
"""
import math

import bpy

from biblioteca.base import box, cyl, empty, mat, noisy, sky_world, sphere, torus, wood, world
from biblioteca.escenario import _mesa, _pared, _piso, _ventana

API_ASSETS = {
    "math": math, "box": box, "cyl": cyl, "sphere": sphere, "torus": torus, "empty": empty,
    "mat": mat, "noisy": noisy, "wood": wood, "sky_world": sky_world, "world": world,
    "piso": _piso, "pared": _pared, "ventana": _ventana, "mesa": _mesa,
}
BUILTINS = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n)
            for n in ("range", "len", "min", "max", "abs", "round", "int", "float", "enumerate", "zip", "list", "tuple",
                      "dict", "sum", "sorted", "reversed", "isinstance", "str", "bool")}
from storyboard.codigo import AssetInvalido, revisar_codigo  # noqa: E402,F401


def ejecutar(codigo: str, tipo: str, params: dict | None = None):
    revisar_codigo(codigo)
    espacio = {"__builtins__": BUILTINS, **API_ASSETS}
    exec(compile(codigo, "<asset>", "exec"), espacio)
    construir = espacio["construir"]
    if tipo == "set":
        return construir() or {}
    resultado = construir(**({"color": params.get("color")} if params and params.get("color") else {}))
    raiz, apoyo = resultado
    if not isinstance(raiz, bpy.types.Object):
        raise AssetInvalido("construir() must return (root_empty, base_z)")
    return raiz, float(apoyo)


# ---------------- respaldos ----------------

def _tono(nombre: str) -> tuple[int, int, int]:
    h = sum(ord(c) * (i + 1) for i, c in enumerate(nombre))
    return 120 + h % 90, 100 + (h // 7) % 80, 80 + (h // 13) % 70


def set_respaldo(nombre: str) -> dict:
    """Sala neutra con el tono derivado del nombre: el video sale aunque el set nuevo falle."""
    c = _tono(nombre)
    world((70, 64, 58), 0.5)
    _piso("piso_" + nombre, (130, 110, 90), (110, 92, 74), 2)
    _pared("pared_" + nombre, (0, 3.2, 1.8), (12, 0.2, 3.6), c, tuple(int(v * 0.85) for v in c), 4)
    _ventana((1.6, 3.08, 1.9), 1.2, 1.4, emision=3)
    return {"mesa": _mesa(1.3, 1.0, 0.72, 1.1, 0.6)}


def prop_respaldo(nombre: str, color=None):
    raiz = empty(nombre)
    c = _tono(nombre)
    if color:
        h = color.lstrip("#")
        c = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    box((0, 0, 0.06), (0.14, 0.14, 0.12), mat("respaldo_" + nombre, c, 0.5), raiz, bevel=0.02)
    return raiz, 0.0
