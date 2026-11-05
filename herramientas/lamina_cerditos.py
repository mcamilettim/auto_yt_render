"""Lámina de regresión: los cerditos y el lobo de la referencia, armados desde la biblioteca.

Ejecutar desde la raíz del repo:
    blender -b -P herramientas/lamina_cerditos.py -- salida.png [vertical|horizontal]
"""
import math
import os
import sys
import time

import bpy

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
bpy.ops.wm.read_factory_settings(use_empty=True)

from biblioteca.base import light, meadow, mat, col, scene  # noqa: E402
from biblioteca.rig import fur  # noqa: E402
from biblioteca.personajes_cerditos import iris_mat, pig2, place, pose, wolf2  # noqa: E402
from biblioteca.render_cfg import configurar_render  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
salida = os.path.abspath(args[0] if args else os.path.join(RAIZ, "salida", "lamina_cerditos.png"))
orient = args[1] if len(args) > 1 else "horizontal"
t0 = time.time()

meadow()
p1 = pig2((232, 196, 90), "straw", iris_mat("irisP1", (175, 120, 60), (110, 70, 35)))
place(p1, (-1.35, 0, 0), math.radians(12))
p2 = pig2((80, 140, 225), "cap", iris_mat("irisP2", (120, 185, 240), (45, 95, 175)))
place(p2, (-0.45, 0, 0), math.radians(4))
w = wolf2()
place(w, (1.0, 0.1, 0), math.radians(-30))
pose(p1, arm_L=(0, 0, 1.2), head=(0, 0, 0.12))
pose(w, head=(0.05, 0, -0.2))

cd = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cd)
col.objects.link(cam)
scene.camera = cam
cam.location = (-0.1, -5.0, 1.0)
cam.rotation_euler = (math.radians(86.5), 0, 0)
cd.lens = 42
if orient == "vertical":
    ancho, alto = 1080, 1920
    cd.sensor_fit = "VERTICAL"
    cd.lens = 30
    cam.location = (-0.1, -6.2, 1.15)
    cam.rotation_euler = (math.radians(85), 0, 0)
else:
    ancho, alto = 1920, 1080
configurar_render(ancho, alto, "rapida")
os.makedirs(os.path.dirname(salida), exist_ok=True)
scene.render.filepath = salida
print("CONSTRUCCION", round(time.time() - t0, 1), flush=True)
bpy.ops.render.render(write_still=True)
print("LAMINA OK", salida, round(time.time() - t0, 1), "s", flush=True)
