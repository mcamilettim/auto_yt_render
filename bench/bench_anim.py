"""Mide segundos por cuadro de una animación con los personajes v2 de referencia.

Variables:
  FRAMES=48  FPS=24  ORIENT=vertical|horizontal  FAST=1|0
  MOTOR=eevee|cycles   SIN_PELO=1 (pelaje casi apagado)   ETIQUETA=nombre de la variante
Ejecutar: FRAMES=48 ORIENT=vertical FAST=1 xvfb-run -a blender -b -P bench/bench_anim.py
Salida: bench/out/<etiqueta>/0001.png ... y una línea "BENCH ..." con los tiempos.
"""
import os
import time

import bpy

D = os.path.dirname(os.path.abspath(__file__))
ruta = os.path.join(D, "personajes_v2.py")
fuente = open(ruta, encoding="utf-8").read()


def reemplazar(texto, viejo, nuevo):
    if viejo not in texto:
        raise RuntimeError(f"No encontré en personajes_v2.py: {viejo[:60]}")
    return texto.replace(viejo, nuevo)


# 1) El render lo hacemos nosotros, después de animar.
fuente = reemplazar(fuente, "bpy.ops.render.render(write_still=True)", "pass  # el render lo hace bench_anim")
# 2) Variante sin pelaje: 1 pelo por sistema (mantiene el código intacto, cuesta ~0).
fuente = reemplazar(
    fuente,
    '    if os.environ.get("FAST", "0") == "1": count, child = count // 2, min(child, 4)\n',
    '    if os.environ.get("FAST", "0") == "1": count, child = count // 2, min(child, 4)\n'
    '    if os.environ.get("SIN_PELO", "0") == "1": count, child = 1, 0\n',
)
# 3) Compatibilidad con Blender 4.2 (EEVEE Next quitó varios ajustes del Eevee legacy).
fuente = reemplazar(fuente, 'm.shadow_method = "NONE"',
                    'setattr(m, "shadow_method", "NONE") if hasattr(m, "shadow_method") else None')
fuente = reemplazar(
    fuente,
    "    l = light(kind, loc, energy, color, size=size, rot=rot); l.use_contact_shadow = True; return l",
    "    l = light(kind, loc, energy, color, size=size, rot=rot)\n"
    "    if hasattr(l, 'use_contact_shadow'): l.use_contact_shadow = True\n"
    "    return l",
)
lineas = []
for linea in fuente.split("\n"):
    if linea.startswith(("e.", "e = scene.eevee", "scene.render.engine")):
        for sentencia in linea.split("; "):
            lineas.append(f"try: {sentencia}\nexcept Exception as _err: print('IGNORADO', {sentencia[:50]!r}, _err)")
    else:
        lineas.append(linea)
fuente = "\n".join(lineas)

ns = {"__file__": ruta, "__name__": "__main__"}
t0 = time.time()
exec(compile(fuente, ruta, "exec"), ns)
construccion = time.time() - t0

scene = bpy.context.scene
motor = os.environ.get("MOTOR", "eevee")
if motor == "cycles":
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(os.environ.get("SAMPLES", "16"))
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception as error:
        print("IGNORADO denoiser", error)
else:
    motores = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in motores else "BLENDER_EEVEE"
    if scene.render.engine == "BLENDER_EEVEE_NEXT":
        scene.eevee.taa_render_samples = 8 if os.environ.get("FAST") == "1" else 24

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

etiqueta = os.environ.get("ETIQUETA") or (
    f"{os.environ.get('ORIENT', 'horizontal')}_{'fast' if os.environ.get('FAST') == '1' else 'full'}_{frames}f")
carpeta = os.path.join(D, "out", etiqueta)
os.makedirs(carpeta, exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = carpeta + os.sep  # Blender agrega 0001.png, 0002.png...

t1 = time.time()
bpy.ops.render.render(animation=True)
render = time.time() - t1
print(f"BENCH {etiqueta} blender={bpy.app.version_string} motor={scene.render.engine} nproc={os.cpu_count()} "
      f"res={scene.render.resolution_x}x{scene.render.resolution_y}@{scene.render.resolution_percentage}% "
      f"construccion={construccion:.1f}s render={render:.1f}s s_por_cuadro={render / frames:.2f}", flush=True)
