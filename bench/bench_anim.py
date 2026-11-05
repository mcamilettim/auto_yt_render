"""Mide segundos por cuadro de una animación con los personajes v2 de referencia.

Ejecutar: FRAMES=48 ORIENT=vertical FAST=1 xvfb-run -a blender -b -P bench/bench_anim.py
Salida: bench/out/<etiqueta>/0001.png ... y una línea "BENCH ..." con los tiempos.
"""
import os
import time

import bpy

D = os.path.dirname(os.path.abspath(__file__))
ruta = os.path.join(D, "personajes_v2.py")
fuente = open(ruta, encoding="utf-8").read()
fuente = fuente.replace("bpy.ops.render.render(write_still=True)", "pass  # el render lo hace bench_anim")
ns = {"__file__": ruta, "__name__": "__main__"}
t0 = time.time()
exec(compile(fuente, ruta, "exec"), ns)
construccion = time.time() - t0

scene = bpy.context.scene
frames = int(os.environ.get("FRAMES", "48"))
fps = int(os.environ.get("FPS", "24"))
scene.render.fps = fps
scene.frame_start, scene.frame_end = 1, frames

# Cámara: dolly suave. Lobo: gira la cabeza. Cerdito 1: levanta el brazo. Prueba que el rig anima.
cam = scene.camera
x0, y0, z0 = cam.location
cam.keyframe_insert("location", frame=1)
cam.location = (x0 + 0.5, y0 + 1.0, z0 + 0.1)
cam.keyframe_insert("location", frame=frames)
for R, hueso, desde, hasta in [(ns["w"], "head", (0.05, 0, -0.2), (0.05, 0, 0.35)),
                               (ns["p1"], "arm.R", (0, 0, 0), (0, 0, -1.3))]:
    pb = R["arm"].pose.bones[hueso]
    pb.rotation_euler = desde
    pb.keyframe_insert("rotation_euler", frame=1)
    pb.rotation_euler = hasta
    pb.keyframe_insert("rotation_euler", frame=frames)

etiqueta = f"{os.environ.get('ORIENT', 'horizontal')}_{'fast' if os.environ.get('FAST') == '1' else 'full'}_{frames}f"
carpeta = os.path.join(D, "out", etiqueta)
os.makedirs(carpeta, exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = carpeta + os.sep  # Blender agrega 0001.png, 0002.png...

t1 = time.time()
bpy.ops.render.render(animation=True)
render = time.time() - t1
print(f"BENCH {etiqueta} nproc={os.cpu_count()} construccion={construccion:.1f}s render={render:.1f}s "
      f"s_por_cuadro={render / frames:.2f}", flush=True)
