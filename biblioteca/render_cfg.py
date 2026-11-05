"""Configuración de render común: Eevee Next (Blender 4.2+), calidad, color y salida."""
import os

import bpy

CALIDADES = {
    # muestras TAA, % de resolución
    "rapida": (8, 50),
    "completa": (24, 100),
}


def configurar_render(ancho: int, alto: int, calidad: str = "rapida", fps: int = 24) -> None:
    scene = bpy.context.scene
    motores = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in motores else "BLENDER_EEVEE"
    muestras, porcentaje = CALIDADES[calidad]
    scene.eevee.taa_render_samples = muestras
    for nombre, valor in (("use_shadows", True), ("use_raytracing", False), ("use_gtao", True),
                          ("gtao_distance", 0.3), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
        if hasattr(scene.eevee, nombre):
            try:
                setattr(scene.eevee, nombre, valor)
            except Exception:
                pass
    scene.render.resolution_x, scene.render.resolution_y = ancho, alto
    scene.render.resolution_percentage = porcentaje
    scene.render.fps = fps
    scene.render.hair_type = "STRIP"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Punchy"
    except Exception:
        scene.view_settings.view_transform = "Filmic"
    scene.render.image_settings.file_format = "PNG"


def hilos() -> int:
    return int(os.environ.get("HILOS", "0")) or os.cpu_count() or 2
