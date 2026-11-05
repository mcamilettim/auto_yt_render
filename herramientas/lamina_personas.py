"""Lámina de personas: una por cada ropa del catálogo, para aprobar el estilo.

Ejecutar desde la raíz del repo:
    herramientas/blender.sh -P herramientas/lamina_personas.py -- salida/lamina_personas.png [rapida|completa]
"""
import math
import os
import sys
import time

import bpy

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
bpy.ops.wm.read_factory_settings(use_empty=True)

from biblioteca.base import col, light, mat, noisy, scene, sky_world  # noqa: E402
from biblioteca.persona import colocar, persona, posar  # noqa: E402
from biblioteca.render_cfg import configurar_render  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
salida = os.path.abspath(args[0] if args else os.path.join(RAIZ, "salida", "lamina_personas.png"))
calidad = args[1] if len(args) > 1 else "rapida"
cerca = len(args) > 2 and args[2] == "cerca"
t0 = time.time()

sky_world((150, 185, 220), (235, 225, 205), 0.9)
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
suelo = bpy.context.object
suelo.data.materials.append(noisy("suelo", (196, 178, 150), (176, 158, 130), 2, 0.9))

ELENCO = [
    dict(nombre="obrero", edad="adulto", complexion="media", piel="#d9a77c", pelo="corto_negro", barba="bigote", ropa="obrero_1890"),
    dict(nombre="comerciante", edad="mayor", complexion="robusta", piel="#e8bf9a", pelo="canoso", barba="completa", ropa="comerciante_1890"),
    dict(nombre="noble", edad="joven", complexion="delgada", piel="#f0cfb0", pelo="largo_recogido", barba="ninguna", ropa="noble_europeo_1700"),
    dict(nombre="funcionario", edad="adulto", complexion="media", piel="#d6a477", pelo="calvo", barba="bigote", ropa="funcionario_chino_qing"),
    dict(nombre="nina", edad="nino", complexion="delgada", piel="#8d5a3b", pelo="corto_castano", barba="ninguna", ropa="moderno_casual"),
]
xs = [-2.0, -1.0, 0.0, 1.0, 2.0]
for params, x in zip(ELENCO, xs):
    R = persona(**params)
    colocar(R, (x, 0, 0), math.radians(-6 * x))
    print("PERSONA", params["nombre"], round(time.time() - t0, 1), flush=True)
    if params["nombre"] == "obrero":
        posar(R, upper_arm__L=(0, 0.3, 0.9))
    if params["nombre"] == "nina":
        posar(R, head=(0, 0, 0.2))

luz = light("SUN", (0, 0, 10), 3.5, (1.0, 0.94, 0.85), size=2.5, rot=(math.radians(50), math.radians(10), math.radians(-30)), name="sol")
light("AREA", (3.0, -4.0, 2.5), 300, (0.8, 0.88, 1.0), size=5, rot=(math.radians(65), 0, math.radians(40)), name="relleno")
light("AREA", (0.0, 3.5, 2.6), 700, (1.0, 0.92, 0.85), size=6, rot=(math.radians(-60), 0, 0), name="contra")

cd = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cd)
col.objects.link(cam)
scene.camera = cam
cam.location = (0, -6.0, 0.95)
cam.rotation_euler = (math.radians(88), 0, 0)
cd.lens = 40
if cerca:  # primer plano de las tres primeras caras
    cam.location = (-1.0, -3.2, 1.1)
    cam.rotation_euler = (math.radians(89), 0, 0)
    cd.lens = 55
configurar_render(1920, 1080, calidad)
os.makedirs(os.path.dirname(salida), exist_ok=True)
scene.render.filepath = salida
print("CONSTRUCCION", round(time.time() - t0, 1), flush=True)
bpy.ops.render.render(write_still=True)
print("LAMINA OK", salida, round(time.time() - t0, 1), "s", flush=True)
