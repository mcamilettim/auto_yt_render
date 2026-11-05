import pytest

from storyboard.codigo import AssetInvalido, revisar_codigo

BUENO = """
def construir(color=None):
    raiz = empty("anillo")
    torus((0, 0, 0.02), 0.05, 0.012, mat("anillo_m", (200, 170, 60), 0.3, metal=0.9), raiz, rot=(math.pi / 2, 0, 0))
    return raiz, 0.0
"""


def test_codigo_valido():
    revisar_codigo(BUENO)


@pytest.mark.parametrize("malo, pista", [
    ("", "empty"),
    ("def construir(:\n  pass", "syntax"),
    ("import os\ndef construir():\n    pass", "imports"),
    ("def construir():\n    open('x')", "open"),
    ("def construir():\n    x = ().__class__", "underscore"),
    ("def construir():\n    __import__('os')", "__import__"),
    ("def construir():\n    bpy.ops.wm.quit_blender()", "bpy"),
    ("def otra():\n    pass", "construir"),
    ("def construir():\n    global x", "global"),
    ("x = 1\n" * 3000 + "def construir():\n    pass", "max"),
])
def test_codigo_rechazado(malo, pista):
    with pytest.raises(AssetInvalido, match=pista):
        revisar_codigo(malo)
