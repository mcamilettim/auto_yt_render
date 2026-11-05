"""Persona estilizada (caricatura con cabeza grande) con esqueleto, ojos, boca, pelo, barba y ropa de época.

persona(nombre, edad, complexion, piel, pelo, barba, ropa) -> dict R con:
  R["arm"]   armature (huesos: hips, spine, head, upper_arm.L/R, forearm.L/R, thigh.L/R, shin.L/R)
  R["lids"]  empties de párpados [sup_izq, inf_izq, sup_der, inf_der]
  R["boca"]  objeto boca abierta (escala 0 = cerrada)
  R["cejas"] empties de cejas (rotación x = levantar/bajar)
  R["mano.L"/"mano.R"] empties en las manos para tomar props
Convenciones: z arriba, el personaje mira hacia -y, L = +x. Altura adulto ~1.2.
"""
import math

from mathutils import Vector

from biblioteca.base import box, cyl, empty, mat, noisy, sphere, torus, tube
from biblioteca.rig import (
    Surf, bone_parent, capsule, deform_copy, fabric, fuse, iris_mat, make_eye, make_rig, mix, paint, skin_mat,
    skin_to, sstep, surface_tube,
)

EDADES = {"nino": (0.72, 1.18), "joven": (0.94, 1.03), "adulto": (1.0, 1.0), "mayor": (0.97, 1.0)}  # (escala, cabeza)
COMPLEXION = {"delgada": 0.85, "media": 1.0, "robusta": 1.28}
PELOS = {
    "calvo": None, "corto_negro": (34, 28, 26), "corto_castano": (110, 72, 42),
    "largo_recogido": (78, 50, 32), "canoso": (205, 205, 208),
}
PIEL_POR_DEFECTO = "#e0ac80"

# Colores de ropa por época: camisa, pantalon, chaqueta (None = sin), zapatos, sombrero
ROPAS = {
    "obrero_1890": {"camisa": (214, 196, 160), "pantalon": (70, 62, 58), "chaqueta": (110, 84, 60), "zapatos": (50, 36, 30),
                    "sombrero": "gorra", "sombrero_color": (92, 80, 70), "largo_chaqueta": "chaleco", "tirantes": True},
    "comerciante_1890": {"camisa": (240, 236, 228), "pantalon": (50, 50, 58), "chaqueta": (38, 40, 52), "zapatos": (25, 22, 24),
                         "sombrero": "bombin", "sombrero_color": (28, 26, 28), "largo_chaqueta": "levita", "tirantes": False},
    "noble_europeo_1700": {"camisa": (245, 240, 230), "pantalon": (235, 225, 200), "chaqueta": (150, 30, 40), "zapatos": (30, 24, 24),
                           "sombrero": "tricornio", "sombrero_color": (30, 28, 30), "largo_chaqueta": "levita", "tirantes": False},
    "funcionario_chino_qing": {"camisa": (40, 70, 140), "pantalon": (40, 70, 140), "chaqueta": (30, 50, 110), "zapatos": (20, 20, 22),
                               "sombrero": "qing", "sombrero_color": (30, 30, 34), "largo_chaqueta": "tunica", "tirantes": False},
    "moderno_casual": {"camisa": (60, 130, 190), "pantalon": (52, 78, 120), "chaqueta": None, "zapatos": (235, 235, 235),
                       "sombrero": None, "sombrero_color": None, "largo_chaqueta": None, "tirantes": False},
}


def tubo_cara(S, puntos_xz, r, m, off=0.004):
    """Tubo pegado al frente de la cara: proyecta cada (x, z) con un rayo desde adelante (-y)."""
    puntos = []
    for x, z in puntos_xz:
        p, n = S.front(x, z)
        if p is None:
            continue
        puntos.append(tuple(p + n * off))
    return tube(puntos, r, m)


def hex_a_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def persona(nombre="persona", edad="adulto", complexion="media", piel=PIEL_POR_DEFECTO, pelo="corto_negro",
            barba="ninguna", ropa="moderno_casual", iris=((120, 85, 50), (70, 45, 25))):
    k, kc = EDADES[edad]
    g = COMPLEXION[complexion]
    PIEL = hex_a_rgb(piel)
    PIEL_OSC = tuple(int(v * 0.86) for v in PIEL)
    R_CAB = 0.2 * kc

    # ---------- cuerpo esculpido (todo en coordenadas de adulto; se escala al final con el armature) ----------
    z_cab = 1.0 + R_CAB * 0.55
    partes = [
        sphere((0, 0, z_cab), R_CAB, None, sc=(0.95, 0.92, 1.05)),                     # cabeza
        sphere((0, -R_CAB * 0.55, z_cab - R_CAB * 0.45), R_CAB * 0.55, None, sc=(1.2, 1, 0.75)),  # mandíbula/mejillas
        sphere((0, -R_CAB * 0.98, z_cab - R_CAB * 0.08), R_CAB * 0.16, None, sc=(0.8, 1, 1.1)),   # nariz
    ]
    for s in (-1, 1):
        partes.append(sphere((s * R_CAB * 0.93, 0, z_cab - R_CAB * 0.05), R_CAB * 0.2, None, sc=(0.5, 0.8, 1)))  # orejas
    partes += capsule((0, 0, z_cab - R_CAB), (0, 0, 0.84), 0.05)                                         # cuello
    partes += [sphere((0, 0, 0.74), 0.15 * g, None, sc=(1.15, 0.8, 0.9)),                                 # pecho
               sphere((0, -0.01 * g, 0.6), 0.15 * g, None, sc=(1.05, 0.85 + 0.15 * (g - 1), 0.9)),        # vientre
               sphere((0, 0, 0.5), 0.14 * g, None, sc=(1.1, 0.85, 0.7))]                                  # cadera
    for s in (-1, 1):
        hombro, codo, mano = (s * 0.17 * g, 0, 0.8), (s * 0.23 * g, 0.01, 0.6), (s * 0.25 * g, -0.02, 0.43)
        partes += capsule(hombro, codo, 0.048 * (0.8 + 0.2 * g), 0.042)
        partes += capsule(codo, mano, 0.042, 0.036)
        partes.append(sphere((mano[0], mano[1] - 0.005, mano[2] - 0.035), 0.05, None, sc=(0.8, 0.9, 1.1)))  # mano
        cadera, rodilla, tobillo = (s * 0.085 * g, 0, 0.5), (s * 0.09 * g, -0.005, 0.27), (s * 0.09 * g, 0, 0.07)
        partes += capsule(cadera, rodilla, 0.065 * (0.85 + 0.15 * g), 0.052)
        partes += capsule(rodilla, tobillo, 0.052, 0.042)
        partes.append(sphere((s * 0.09 * g, -0.045, 0.04), 0.06, None, sc=(0.85, 1.6, 0.6)))           # pie
    cuerpo = fuse(partes, nombre + "_cuerpo", voxel=0.008)

    def color_piel(c):
        mejilla = min(math.dist((c.x, c.y, c.z), (sx * R_CAB * 0.55, -R_CAB * 0.8, z_cab - R_CAB * 0.35)) for sx in (-1, 1))
        return mix(PIEL, (232, 140, 130), 0.35 * (1 - sstep(0.02, 0.07, mejilla)))
    paint(cuerpo, color_piel)
    m_piel = skin_mat(nombre + "_piel", (0.9, 0.4, 0.3), sss=0.25)
    cuerpo.data.materials.append(m_piel)

    arm = make_rig(nombre + "_rig", [
        ("hips", (0, 0, 0.45), (0, 0, 0.62), None),
        ("spine", (0, 0, 0.62), (0, 0, 0.86), "hips"),
        ("head", (0, 0, 0.86), (0, 0, z_cab + R_CAB), "spine"),
        ("upper_arm.L", (0.17 * g, 0, 0.8), (0.23 * g, 0.01, 0.6), "spine"),
        ("forearm.L", (0.23 * g, 0.01, 0.6), (0.25 * g, -0.02, 0.4), "upper_arm.L"),
        ("upper_arm.R", (-0.17 * g, 0, 0.8), (-0.23 * g, 0.01, 0.6), "spine"),
        ("forearm.R", (-0.23 * g, 0.01, 0.6), (-0.25 * g, -0.02, 0.4), "upper_arm.R"),
        ("thigh.L", (0.085 * g, 0, 0.5), (0.09 * g, -0.005, 0.27), "hips"),
        ("shin.L", (0.09 * g, -0.005, 0.27), (0.09 * g, 0, 0.05), "thigh.L"),
        ("thigh.R", (-0.085 * g, 0, 0.5), (-0.09 * g, -0.005, 0.27), "hips"),
        ("shin.R", (-0.09 * g, -0.005, 0.27), (-0.09 * g, 0, 0.05), "thigh.R"),
    ])
    skin_to(cuerpo, arm)
    S = Surf(cuerpo)
    R = {"arm": arm, "lids": [], "eyes": [], "cejas": [], "body": cuerpo}

    # ---------- ropa ----------
    r = ROPAS[ropa]
    zc = r["largo_chaqueta"]
    camisa = deform_copy(cuerpo, arm, nombre + "_camisa",
                         lambda c: 0.46 < c.z < 0.86 and not (abs(c.x) > 0.2 * g and c.z < 0.52 + 0.0), 0.012,
                         fabric(nombre + "_camisa_m", r["camisa"]))
    camisa.parent = arm
    largo_pierna = 0.03 if zc == "tunica" else 0.075
    pantalon = deform_copy(cuerpo, arm, nombre + "_pantalon",
                           lambda c: largo_pierna < c.z < 0.53 and abs(c.x) < 0.2 * g, 0.014,
                           fabric(nombre + "_pantalon_m", r["pantalon"], scale=120))
    pantalon.parent = arm
    zap = deform_copy(cuerpo, arm, nombre + "_zapatos", lambda c: c.z < 0.085 and abs(c.x) < 0.2 * g, 0.012,
                      mat(nombre + "_zapatos_m", r["zapatos"], 0.35))
    zap.parent = arm
    if r["chaqueta"]:
        if zc == "chaleco":
            keep = lambda c: 0.5 < c.z < 0.84 and abs(c.x) < 0.17 * g          # sin mangas
        elif zc == "levita":
            keep = lambda c: (0.36 < c.z < 0.85 and abs(c.x) < 0.2 * g and not (c.y < -0.02 and abs(c.x) < 0.03)) \
                or (abs(c.x) >= 0.15 * g and 0.47 < c.z < 0.85)
        else:  # tunica larga hasta los tobillos
            keep = lambda c: (0.06 < c.z < 0.85 and abs(c.x) < 0.2 * g) or (abs(c.x) >= 0.15 * g and 0.45 < c.z < 0.85)
        chaqueta = deform_copy(cuerpo, arm, nombre + "_chaqueta", keep, 0.024, fabric(nombre + "_chaqueta_m", r["chaqueta"], scale=90))
        chaqueta.parent = arm
    if r["tirantes"]:
        for s in (-1, 1):
            t = surface_tube(S, [(s * 0.07, -0.3, 0.52), (s * 0.08, -0.3, 0.66), (s * 0.09, -0.3, 0.8), (s * 0.09, 0.0, 0.86),
                                 (s * 0.08, 0.3, 0.7)], 0.011, mat(nombre + "_tirante", (60, 40, 30), 0.6), off=0.035)
            bone_parent(t, arm, "spine")

    # ---------- cara ----------
    m_iris = iris_mat(nombre + "_iris", *iris)
    for s in (-1, 1):
        E, lids = make_eye(S, s * R_CAB * 0.36, z_cab + R_CAB * 0.08, R_CAB * 0.23, m_piel, m_iris, s=s,
                           lidcol=PIEL_OSC, sink=0.5, upper=-0.5, lower=0.65)
        bone_parent(E, arm, "head")
        R["eyes"].append(E)
        R["lids"] += lids
        color_ceja = PELOS.get(pelo) or (90, 70, 60)
        ceja_pivote = empty(nombre + "_ceja", (s * R_CAB * 0.36, -R_CAB, z_cab + R_CAB * 0.38))
        ceja = tubo_cara(S, [(s * R_CAB * (0.36 + 0.2 * u), z_cab + R_CAB * (0.4 - 0.05 * abs(u) ** 1.5))
                             for u in [i / 4 - 0.5 for i in range(5)]], 0.011 * kc,
                         mat(nombre + "_ceja_m", color_ceja, 0.7), off=0.008)
        ceja.parent = ceja_pivote
        ceja.matrix_parent_inverse = ceja_pivote.matrix_world.inverted()
        bone_parent(ceja_pivote, arm, "head")
        R["cejas"].append(ceja_pivote)
    boca_puntos = [(R_CAB * 0.22 * u, z_cab - R_CAB * (0.45 + 0.06 * (1 - u * u))) for u in [i / 4 - 1 for i in range(9)]]
    boca = tubo_cara(S, boca_puntos, 0.008, mat(nombre + "_labios", (130, 50, 50), 0.4), off=0.002)
    bone_parent(boca, arm, "head")
    p, n = S.front(0, z_cab - R_CAB * 0.5)
    R["boca"] = sphere(tuple(p + n * 0.004), R_CAB * 0.16, mat(nombre + "_boca_m", (70, 25, 30), 0.5), sc=(1.2, 0.5, 0.7))
    bone_parent(R["boca"], arm, "head")
    R["boca_escala"] = R["boca"].scale.copy()
    R["boca"].scale = (0, 0, 0)

    # ---------- pelo y barba ----------
    color_pelo = PELOS[pelo]
    if color_pelo:
        m_pelo = noisy(nombre + "_pelo_m", color_pelo, tuple(int(v * 0.8) for v in color_pelo), 40, 0.6)
        casco = sphere((0, R_CAB * 0.16, z_cab + R_CAB * 0.2), R_CAB * 1.02, m_pelo, sc=(0.98, 0.98, 0.9))
        # recorta la frente: aplana la parte delantera inferior
        casco.scale = (0.98, 0.95, 0.88)
        bone_parent(casco, arm, "head")
        if pelo == "largo_recogido":
            mono = sphere((0, R_CAB * 0.95, z_cab + R_CAB * 0.3), R_CAB * 0.38, m_pelo)
            bone_parent(mono, arm, "head")
    if barba != "ninguna":
        color_b = color_pelo or (90, 70, 60)
        m_barba = noisy(nombre + "_barba_m", color_b, tuple(int(v * 0.8) for v in color_b), 50, 0.7)
        if barba == "bigote":
            bigote = tubo_cara(S, [(R_CAB * 0.3 * u, z_cab - R_CAB * (0.3 + 0.1 * abs(u))) for u in [i / 6 - 1 for i in range(13)]],
                               0.018 * kc, m_barba, off=0.012)
            bone_parent(bigote, arm, "head")
        else:
            barb = sphere((0, -R_CAB * 0.62, z_cab - R_CAB * 0.62), R_CAB * 0.55, m_barba, sc=(1.25, 0.75, 0.85))
            bone_parent(barb, arm, "head")

    # ---------- sombrero ----------
    H = empty(nombre + "_sombrero", (0, 0, z_cab + R_CAB * 0.66))
    sc = r["sombrero_color"]
    if r["sombrero"] == "gorra":
        mg = fabric(nombre + "_gorra_m", sc, scale=80)
        sphere((0, 0.01, 0), R_CAB * 1.02, mg, H, sc=(1, 1, 0.42))
        cyl((0, -R_CAB * 0.95, -0.02), R_CAB * 0.55, 0.012, mg, H, sc=(1.1, 0.6, 1), rot=(0.15, 0, 0))
    elif r["sombrero"] == "bombin":
        mb = mat(nombre + "_bombin_m", sc, 0.4)
        sphere((0, 0, 0.04), R_CAB * 0.82, mb, H, sc=(1, 1, 0.85))
        cyl((0, 0, -0.005), R_CAB * 1.25, 0.014, mb, H, verts=48)
        torus((0, 0, 0.0), R_CAB * 0.8, 0.012, mat(nombre + "_cinta", (60, 50, 50), 0.5), H)
    elif r["sombrero"] == "tricornio":
        mt = mat(nombre + "_tricornio_m", sc, 0.5)
        cyl((0, 0, 0.03), R_CAB * 0.85, 0.12, mt, H, verts=40)
        for a in range(3):
            ang = a * 2 * math.pi / 3 + math.pi / 2
            box((math.cos(ang) * R_CAB * 0.7, math.sin(ang) * R_CAB * 0.7 * -1, 0.06),
                (R_CAB * 1.1, 0.02, 0.1), mt, H, rot=(0, 0, ang + math.pi / 2), bevel=0.008)
    elif r["sombrero"] == "qing":
        mq = mat(nombre + "_qing_m", sc, 0.6)
        cyl((0, 0, 0.0), R_CAB * 1.15, 0.1, mq, H, r2=R_CAB * 0.6, verts=48)
        sphere((0, 0, 0.08), R_CAB * 0.14, mat(nombre + "_boton", (200, 30, 30), 0.3), H)
    bone_parent(H, arm, "head")

    # ---------- manos: puntos de anclaje para props ----------
    for s, lado in ((1, "L"), (-1, "R")):
        mano = empty(f"{nombre}_mano.{lado}", (s * 0.25 * g, -0.03, 0.39))
        bone_parent(mano, arm, f"forearm.{lado}")
        R[f"mano.{lado}"] = mano

    arm.scale = (k, k, k)
    R["escala"] = k
    return R


def colocar(R, loc, rotz=0.0):
    k = R.get("escala", 1.0)
    R["arm"].location = loc
    R["arm"].rotation_euler = (0, 0, rotz)
    R["arm"].scale = (k, k, k)


def posar(R, **huesos):
    for nombre, rot in huesos.items():
        R["arm"].pose.bones[nombre.replace("__", ".")].rotation_euler = rot
