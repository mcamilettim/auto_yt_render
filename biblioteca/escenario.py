"""Escenarios, luces y props del catálogo. Todos con geometría procedural (sin assets externos).

Convenciones: los actores se paran cerca del origen (|x|,|y| <= 3); la cámara mira desde -y; el fondo está en +y.
Cada set devuelve un dict con al menos {"mesa": (x, y, z_superficie)} cuando trae una mesa.
"""
import math

import bpy

from biblioteca.base import box, col, cyl, empty, light, mat, meadow, noisy, sky_world, sphere, torus, wood, world


def _piso(nombre, c1, c2, escala=3.0, tam=40):
    bpy.ops.mesh.primitive_plane_add(size=tam, location=(0, 0, 0))
    o = bpy.context.object
    o.name = nombre
    o.data.materials.append(noisy(nombre + "_m", c1, c2, escala, 0.85))
    return o


def _pared(nombre, loc, tam, c1, c2, escala=4.0, rot=(0, 0, 0)):
    return box(loc, tam, noisy(nombre + "_m", c1, c2, escala, 0.9), bevel=0, rot=rot)


def _ventana(loc, ancho, alto, emision=4.0, color=(255, 240, 210)):
    marco = mat("marco_ventana", (90, 60, 40), 0.6)
    box(loc, (ancho + 0.1, 0.06, alto + 0.1), marco, bevel=0.01)
    box((loc[0], loc[1] - 0.04, loc[2]), (ancho, 0.02, alto), mat("vidrio_" + str(emision), color, 0.1, emit=emision), bevel=0)
    box((loc[0], loc[1] - 0.06, loc[2]), (0.04, 0.02, alto), marco, bevel=0)


def _mesa(x, y, alto=0.62, ancho=1.0, fondo=0.6, m=None):
    m = m or wood("madera_mesa", (150, 100, 60), (120, 78, 44), scale=4)
    box((x, y, alto - 0.03), (ancho, fondo, 0.06), m, bevel=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box((x + sx * (ancho / 2 - 0.05), y + sy * (fondo / 2 - 0.05), (alto - 0.06) / 2), (0.06, 0.06, alto - 0.06), m, bevel=0.005)
    return (x, y, alto)


def taller_1890():
    _piso("piso_taller", (120, 85, 55), (95, 65, 40), 1.5)
    _pared("pared_fondo", (0, 3.2, 2.0), (12, 0.2, 4), (150, 80, 60), (120, 62, 48), 8)
    _pared("pared_izq", (-4.5, 0, 2.0), (0.2, 7, 4), (150, 80, 60), (120, 62, 48), 8)
    _ventana((1.6, 3.08, 2.0), 1.4, 1.6)
    banco = _mesa(1.2, 1.0, 0.85, 2.2, 0.8)
    acero = mat("acero", (150, 150, 160), 0.35, metal=0.8)
    for i in range(5):
        cyl((-1.8 + i * 0.35, 3.05, 1.6), 0.03, 0.5, acero, rot=(math.pi / 2 * 0, 0, 0))
    estante = wood("madera_estante", (110, 72, 40), (90, 58, 32))
    for z in (1.1, 1.7, 2.3):
        box((-2.4, 3.0, z), (1.6, 0.35, 0.05), estante, bevel=0.005)
        for i in range(4):
            box((-3.0 + i * 0.4, 3.0, z + 0.14), (0.25, 0.25, 0.25), mat(f"caja_estante_{i}", (160 - 20 * i, 120, 80), 0.7), bevel=0.01)
    return {"mesa": banco}


def puerto_1890():
    sky_world((120, 165, 215), (230, 215, 190), 1.0)
    _piso("muelle", (130, 100, 70), (100, 75, 50), 6, tam=12)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.4))
    bpy.context.object.data.materials.append(mat("mar", (40, 90, 120), 0.15, spec=0.8))
    madera = wood("madera_caja", (170, 120, 70), (140, 95, 55), scale=5)
    for x, y, h in [(-2.0, 1.8, 0.6), (-1.4, 2.1, 0.6), (-1.7, 1.9, 1.2), (2.3, 1.5, 0.5)]:
        box((x, y, h - 0.3), (0.6, 0.6, 0.6), madera, bevel=0.02)
    casco = sphere((0, 9, 0.5), 3.0, mat("casco_barco", (60, 35, 25), 0.6), sc=(3.0, 0.8, 0.6))
    for x in (-3, 0, 3):
        cyl((x, 9, 5), 0.1, 8, wood("mastil", (120, 85, 50), (100, 70, 40)))
    for x in (-5, -2.5, 2.5, 5):
        cyl((x, -0.3 + 6, 0.6), 0.12, 1.2, wood("pilote", (90, 65, 40), (70, 50, 30)))
    return {"mesa": _mesa(1.6, 1.0, 0.7, 1.2, 0.7)}


def calle_victoriana():
    sky_world((160, 175, 195), (220, 210, 195), 0.9)
    _piso("adoquines", (110, 105, 100), (80, 78, 76), 18)
    ladrillo = noisy("ladrillo", (140, 75, 55), (110, 58, 44), 10, 0.9)
    for i, x in enumerate((-4.5, -1.5, 1.5, 4.5)):
        alto = 5 + (i % 2) * 1.2
        box((x, 4.0, alto / 2), (2.9, 2.0, alto), ladrillo, bevel=0)
        for vz in (1.6, 3.4):
            _ventana((x, 2.98, vz), 0.9, 1.1, emision=1.5)
    farol = mat("farol", (30, 30, 34), 0.4, metal=0.6)
    for x in (-2.5, 2.5):
        cyl((x, 2.4, 1.6), 0.05, 3.2, farol)
        sphere((x, 2.4, 3.25), 0.16, mat("luz_farol", (255, 220, 160), 0.2, emit=6))
    return {"mesa": _mesa(1.8, 1.2, 0.8, 1.0, 0.6)}


def fabrica_1890():
    world((40, 38, 36), 0.4)
    _piso("piso_fabrica", (95, 92, 88), (70, 68, 64), 4)
    _pared("pared_fabrica", (0, 4.0, 3.0), (14, 0.3, 6), (120, 70, 55), (95, 55, 42), 10)
    for x in (-3, 0, 3):
        _ventana((x, 3.84, 3.6), 1.6, 1.8, emision=3)
    hierro = mat("hierro", (70, 72, 78), 0.45, metal=0.7)
    for x in (-2.5, 2.5):
        box((x, 2.4, 0.7), (1.4, 1.0, 1.4), hierro, bevel=0.03)
        cyl((x, 2.4, 1.6), 0.35, 0.4, hierro, rot=(math.pi / 2, 0, 0))
    box((0, 2.6, 2.6), (8, 0.15, 0.08), mat("correa", (40, 30, 25), 0.8), bevel=0)
    return {"mesa": _mesa(1.0, 1.3, 0.85, 1.6, 0.7)}


def palacio_chino():
    sky_world((150, 185, 220), (235, 225, 205), 1.0)
    _piso("piedra", (170, 165, 155), (140, 135, 128), 6)
    rojo = mat("columna_roja", (170, 30, 30), 0.5)
    for x in (-3.0, -1.0, 1.0, 3.0):
        cyl((x, 3.2, 1.8), 0.2, 3.6, rojo)
    box((0, 3.2, 3.8), (8.5, 2.4, 0.4), mat("viga", (60, 90, 70), 0.6), bevel=0.02)
    techo = box((0, 3.4, 4.4), (9.5, 3.4, 0.25), mat("tejas", (40, 40, 45), 0.6), bevel=0.02)
    techo.rotation_euler = (math.radians(-12), 0, 0)
    box((0, 4.4, 1.8), (8.5, 0.2, 3.6), mat("muro_palacio", (190, 60, 50), 0.7), bevel=0)
    for i in range(3):
        box((0, 1.9 + i * 0.25, 0.08 + i * 0.16), (4.0, 0.3, 0.16), mat("escalon", (190, 185, 175), 0.8), bevel=0.01)
    return {"mesa": _mesa(-1.6, 1.0, 0.7, 1.0, 0.6, wood("laca", (120, 30, 25), (100, 22, 18)))}


def sala_moderna():
    world((200, 200, 205), 0.6)
    _piso("piso_sala", (175, 140, 105), (150, 118, 88), 2)
    _pared("pared_sala", (0, 3.2, 1.6), (10, 0.2, 3.2), (225, 220, 210), (215, 210, 200), 3)
    _ventana((1.8, 3.08, 1.6), 1.6, 1.4, emision=5)
    tela = mat("sofa", (70, 110, 140), 0.85)
    box((-1.5, 2.5, 0.25), (2.2, 0.9, 0.5), tela, bevel=0.06)
    box((-1.5, 2.9, 0.65), (2.2, 0.25, 0.8), tela, bevel=0.06)
    bpy.ops.mesh.primitive_cylinder_add(radius=1.4, depth=0.01, location=(0, 0.6, 0.006))
    bpy.context.object.data.materials.append(mat("alfombra", (180, 150, 120), 0.95))
    return {"mesa": _mesa(1.3, 1.2, 0.45, 1.0, 0.6)}


def escritorio_estudio():
    world((60, 55, 50), 0.5)
    _piso("piso_estudio", (110, 75, 50), (90, 60, 40), 2)
    _pared("pared_estudio", (0, 3.0, 1.8), (10, 0.2, 3.6), (120, 95, 70), (100, 80, 60), 3)
    estante = wood("biblioteca", (90, 60, 35), (70, 46, 26))
    box((-1.8, 2.75, 1.4), (2.4, 0.4, 2.8), estante, bevel=0.01)
    colores = [(140, 40, 40), (40, 70, 120), (60, 100, 60), (150, 120, 60), (90, 50, 90)]
    for fila, z in enumerate((0.5, 1.2, 1.9, 2.6)):
        x = -2.9
        i = 0
        while x < -0.75:
            ancho = 0.06 + ((i * 7 + fila * 3) % 5) * 0.012
            box((x + ancho / 2, 2.55, z), (ancho, 0.3, 0.42), mat(f"lomo_{(i + fila) % 5}", colores[(i + fila) % 5], 0.6), bevel=0.004)
            x += ancho + 0.01
            i += 1
    mesa = _mesa(0.4, 0.6, 0.75, 1.6, 0.8)
    return {"mesa": mesa}


def campo_abierto():
    meadow()
    for o in list(bpy.data.objects):            # meadow trae luces propias: las reemplaza la luz de la escena
        if o.type == "LIGHT":
            bpy.data.objects.remove(o)
    return {"mesa": _mesa(1.4, 1.0, 0.7, 1.0, 0.6)}


SETS = {f.__name__: f for f in (taller_1890, puerto_1890, calle_victoriana, fabrica_1890, palacio_chino, sala_moderna,
                               escritorio_estudio, campo_abierto)}

INTERIORES = {"taller_1890", "fabrica_1890", "sala_moderna", "escritorio_estudio"}


def luz(nombre: str, set_nombre: str) -> None:
    interior = set_nombre in INTERIORES
    if nombre == "dia":
        light("SUN", (0, 0, 10), 3.5, (1.0, 0.95, 0.88), size=2.5, rot=(math.radians(50), math.radians(10), math.radians(-30)), name="sol")
        light("AREA", (3, -5, 3), 400, (0.85, 0.9, 1.0), size=6, rot=(math.radians(60), 0, math.radians(30)), name="relleno")
    elif nombre == "atardecer":
        light("SUN", (0, 0, 10), 3.0, (1.0, 0.62, 0.35), size=3, rot=(math.radians(75), 0, math.radians(-60)), name="sol")
        light("AREA", (-3, -4, 2.5), 300, (0.55, 0.6, 0.95), size=6, rot=(math.radians(65), 0, math.radians(-35)), name="relleno")
    elif nombre == "noche_velas":
        if not interior:
            world((10, 12, 22), 0.3)
        for x in (-1.2, 1.4):
            l = bpy.data.lights.new("vela", "POINT")
            l.energy, l.color, l.shadow_soft_size = 120, (1.0, 0.62, 0.3), 0.15
            o = bpy.data.objects.new("vela", l)
            col.objects.link(o)
            o.location = (x, -0.6, 1.2)
        light("AREA", (0, -5, 3), 60, (0.4, 0.5, 0.9), size=6, rot=(math.radians(60), 0, 0), name="relleno")
    elif nombre == "interior_calido":
        light("AREA", (1.5, 2.5, 3.2), 600, (1.0, 0.85, 0.65), size=3, rot=(math.radians(-35), 0, 0), name="ventana")
        light("AREA", (-2.5, -3.5, 2.6), 300, (1.0, 0.8, 0.6), size=5, rot=(math.radians(60), 0, math.radians(-35)), name="relleno")
    else:  # interior_frio
        light("AREA", (1.5, 2.5, 3.2), 600, (0.75, 0.85, 1.0), size=3, rot=(math.radians(-35), 0, 0), name="ventana")
        light("AREA", (-2.5, -3.5, 2.6), 250, (0.8, 0.88, 1.0), size=5, rot=(math.radians(60), 0, math.radians(-35)), name="relleno")
    light("AREA", (0, 3.5, 2.8), 500, (1.0, 0.95, 0.9), size=5, rot=(math.radians(-60), 0, 0), name="contra")


# ---------------- props (tamaño exagerado ~1.6x para que se lean en pantalla) ----------------

def _hex(h, defecto):
    if not h:
        return defecto
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def lapiz(color=None):
    raiz = empty("lapiz")
    c = _hex(color, (242, 194, 0))
    cyl((0, 0, 0), 0.012, 0.26, mat("lapiz_cuerpo_" + str(c), c, 0.45), raiz, verts=6, rot=(0, math.pi / 2, 0))
    cyl((0.15, 0, 0), 0.012, 0.04, mat("madera_punta", (225, 190, 140), 0.7), raiz, r2=0.003, rot=(0, math.pi / 2, 0), verts=12)
    cyl((-0.14, 0, 0), 0.0125, 0.02, mat("ferrula", (190, 180, 150), 0.3, metal=0.8), raiz, rot=(0, math.pi / 2, 0))
    cyl((-0.16, 0, 0), 0.012, 0.025, mat("goma", (235, 130, 140), 0.8), raiz, rot=(0, math.pi / 2, 0))
    return raiz, 0.012


def libro(color=None):
    raiz = empty("libro")
    c = _hex(color, (120, 40, 35))
    box((0, 0, 0.025), (0.26, 0.19, 0.05), mat("tapa_" + str(c), c, 0.6), raiz, bevel=0.005)
    box((0.005, 0, 0.025), (0.25, 0.18, 0.042), mat("paginas", (240, 230, 205), 0.9), raiz, bevel=0)
    return raiz, 0.0


def lampara_aceite(color=None):
    raiz = empty("lampara")
    laton = mat("laton", (200, 160, 80), 0.3, metal=0.9)
    cyl((0, 0, 0.03), 0.07, 0.06, laton, raiz)
    sphere((0, 0, 0.12), 0.07, mat("vidrio_lampara", (255, 210, 140), 0.1, emit=3), raiz)
    cyl((0, 0, 0.22), 0.03, 0.08, laton, raiz)
    return raiz, 0.0


def caja_madera(color=None):
    raiz = empty("caja")
    box((0, 0, 0.12), (0.3, 0.3, 0.24), wood("madera_caja_p", (170, 120, 70), (140, 95, 55), scale=6), raiz, bevel=0.01)
    return raiz, 0.0


def taza(color=None):
    raiz = empty("taza")
    c = _hex(color, (240, 240, 235))
    m = mat("taza_" + str(c), c, 0.25)
    cyl((0, 0, 0.05), 0.045, 0.1, m, raiz)
    torus((0.05, 0, 0.05), 0.028, 0.008, m, raiz, rot=(math.pi / 2, 0, 0))
    return raiz, 0.0


PROPS = {"lapiz": lapiz, "libro": libro, "lampara_aceite": lampara_aceite, "caja_madera": caja_madera, "taza": taza}
