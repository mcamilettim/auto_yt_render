"""Lámina de estilos: los mismos 3 personajes en caricatura, realista y plano.

    herramientas/blender.sh -P herramientas/lamina_estilos.py -- salida/lamina_estilos.png
"""
import math
import os
import sys
import time

import bpy

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
bpy.ops.wm.read_factory_settings(use_empty=True)

from biblioteca.base import col, light, noisy, scene, sky_world  # noqa: E402
from biblioteca.persona import colocar, persona  # noqa: E402
from biblioteca.render_cfg import configurar_render  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
salida = os.path.abspath(args[0] if args else os.path.join(RAIZ, "salida", "lamina_estilos.png"))
t0 = time.time()

sky_world((150, 185, 220), (235, 225, 205), 0.9)
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
bpy.context.object.data.materials.append(noisy("suelo", (196, 178, 150), (176, 158, 130), 2, 0.9))

ELENCO = [
    dict(edad="adulto", complexion="media", piel="#d9a77c", pelo="corto_negro", barba="bigote", ropa="obrero_1890"),
    dict(edad="mayor", complexion="robusta", piel="#e8bf9a", pelo="canoso", barba="completa", ropa="comerciante_1890"),
    dict(edad="adulto", complexion="media", piel="#d6a477", pelo="calvo", barba="bigote", ropa="funcionario_chino_qing"),
]
for gi, estilo in enumerate(("caricatura", "realista", "plano")):
    for pi, params in enumerate(ELENCO):
        x = (gi - 1) * 2.7 + (pi - 1) * 0.8
        R = persona(nombre=f"{estilo}_{pi}", estilo=estilo, **params)
        colocar(R, (x, 0, 0), 0.0)
        print("PERSONA", estilo, pi, round(time.time() - t0, 1), flush=True)

light("SUN", (0, 0, 10), 3.5, (1.0, 0.94, 0.85), size=2.5, rot=(math.radians(50), math.radians(10), math.radians(-30)), name="sol")
light("AREA", (3.0, -6.0, 3.0), 500, (0.8, 0.88, 1.0), size=8, rot=(math.radians(65), 0, math.radians(30)), name="relleno")
light("AREA", (0.0, 4.0, 3.0), 900, (1.0, 0.92, 0.85), size=8, rot=(math.radians(-60), 0, 0), name="contra")

cd = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cd)
col.objects.link(cam)
scene.camera = cam
cam.location = (0, -9.5, 1.0)
cam.rotation_euler = (math.radians(88), 0, 0)
cd.lens = 38
configurar_render(1920, 1080, "rapida")
scene.render.resolution_percentage = 75
os.makedirs(os.path.dirname(salida), exist_ok=True)
scene.render.filepath = salida
print("CONSTRUCCION", round(time.time() - t0, 1), flush=True)
bpy.ops.render.render(write_still=True)
print("LAMINA OK", salida, round(time.time() - t0, 1), "s", flush=True)
