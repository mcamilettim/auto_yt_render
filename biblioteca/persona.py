"""Persona estilizada (caricatura con cabeza grande) con esqueleto, ojos, boca, pelo, barba y ropa de época.

persona(nombre, edad, complexion, piel, pelo, barba, ropa, estilo) -> dict R con:
  R["arm"]   armature (huesos: hips, spine, head, upper_arm.L/R, forearm.L/R, thigh.L/R, shin.L/R)
  R["lids"]  empties de párpados [sup_izq, inf_izq, sup_der, inf_der]
  R["boca"]  objeto boca abierta (escala 0 = cerrada)
  R["cejas"] empties de cejas (rotación x = levantar/bajar)
  R["mano.L"/"mano.R"] empties en las manos para tomar props
Estilos: "caricatura" (cabeza grande, ~1.2 de alto), "realista" (proporciones humanas, ~1.65 de alto, ojos chicos)
y "plano" (proporciones de caricatura con sombreado de dibujo animado y contorno negro).
Convenciones: z arriba, el personaje mira hacia -y, L = +x.
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

ESTILOS = ("caricatura", "realista", "plano")
_CARICATURA = dict(R_cab=0.2, z_tob=0.07, z_rod=0.27, z_cad=0.5, z_cin=0.6, z_pecho=0.74, z_hom=0.8, z_cue=0.84,
                   hom_x=0.17, codo_x=0.23, codo_z=0.6, mano_x=0.25, mano_z=0.43, cad_x=0.085, rod_x=0.09,
                   torso=0.15, brazo=0.048, pierna=0.065, mano_r=0.05, cuello=0.05,
                   ojo=0.23, ojo_x=0.36, nariz=0.16, rubor=0.35, sss=0.25)
PROPORCIONES = {
    "caricatura": _CARICATURA,
    "plano": _CARICATURA,
    "realista": dict(R_cab=0.12, z_tob=0.08, z_rod=0.47, z_cad=0.86, z_cin=1.02, z_pecho=1.2, z_hom=1.32, z_cue=1.38,
                     hom_x=0.2, codo_x=0.24, codo_z=1.04, mano_x=0.26, mano_z=0.78, cad_x=0.095, rod_x=0.1,
                     torso=0.16, brazo=0.045, pierna=0.07, mano_r=0.045, cuello=0.045,
                     ojo=0.15, ojo_x=0.36, nariz=0.2, rubor=0.1, sss=0.45),
}

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
            barba="ninguna", ropa="moderno_casual", estilo="caricatura", iris=((120, 85, 50), (70, 45, 25))):
    import bpy
    antes = set(bpy.data.objects)
    P = PROPORCIONES[estilo]
    k, kc = EDADES[edad]
    if estilo == "realista":
        kc = 1.0 + (kc - 1.0) * 0.5          # en realista la cabeza de niño crece menos
    g = COMPLEXION[complexion]
    PIEL = hex_a_rgb(piel)
    PIEL_OSC = tuple(int(v * 0.86) for v in PIEL)
    R_CAB = P["R_cab"] * kc
    z_tob, z_rod, z_cad, z_cin, z_pecho, z_hom, z_cue = (P[c] for c in ("z_tob", "z_rod", "z_cad", "z_cin", "z_pecho", "z_hom", "z_cue"))
    ancho_torso = P["torso"] * g * 1.15
    hombro_x, codo_x, mano_x = P["hom_x"] * g, P["codo_x"] * g, P["mano_x"] * g
    cad_x, rod_x = P["cad_x"] * g, P["rod_x"] * g
    z_cab = z_cue + R_CAB * 1.35

    # ---------- cuerpo esculpido ----------
    partes = [
        sphere((0, 0, z_cab), R_CAB, None, sc=(0.95, 0.92, 1.05)),                                        # cabeza
        sphere((0, -R_CAB * 0.55, z_cab - R_CAB * 0.45), R_CAB * 0.55, None, sc=(1.2, 1, 0.75)),           # mandíbula
        sphere((0, -R_CAB * 0.98, z_cab - R_CAB * 0.08), R_CAB * P["nariz"], None, sc=(0.8, 1, 1.1)),      # nariz
    ]
    for s in (-1, 1):
        partes.append(sphere((s * R_CAB * 0.93, 0, z_cab - R_CAB * 0.05), R_CAB * 0.2, None, sc=(0.5, 0.8, 1)))  # orejas
    partes += capsule((0, 0, z_cab - R_CAB), (0, 0, z_cue), P["cuello"])
    partes += [sphere((0, 0, z_pecho), P["torso"] * g, None, sc=(1.15, 0.8, 0.9)),
               sphere((0, -0.01 * g, z_cin), P["torso"] * g, None, sc=(1.05, 0.85 + 0.15 * (g - 1), 0.9)),
               sphere((0, 0, z_cad), P["torso"] * 0.93 * g, None, sc=(1.1, 0.85, 0.7))]
    for s in (-1, 1):
        hombro, codo, mano = (s * hombro_x, 0, z_hom), (s * codo_x, 0.01, P["codo_z"]), (s * mano_x, -0.02, P["mano_z"])
        partes += capsule(hombro, codo, P["brazo"] * (0.8 + 0.2 * g), P["brazo"] * 0.875)
        partes += capsule(codo, mano, P["brazo"] * 0.875, P["brazo"] * 0.75)
        partes.append(sphere((mano[0], mano[1] - 0.005, mano[2] - 0.035), P["mano_r"], None, sc=(0.8, 0.9, 1.1)))
        cadera, rodilla, tobillo = (s * cad_x, 0, z_cad), (s * rod_x, -0.005, z_rod), (s * rod_x, 0, z_tob)
        partes += capsule(cadera, rodilla, P["pierna"] * (0.85 + 0.15 * g), P["pierna"] * 0.8)
        partes += capsule(rodilla, tobillo, P["pierna"] * 0.8, P["pierna"] * 0.65)
        partes.append(sphere((s * rod_x, -0.045, 0.04), 0.06, None, sc=(0.85, 1.6, 0.6)))               # pie
    cuerpo = fuse(partes, nombre + "_cuerpo", voxel=0.008)

    def color_piel(c):
        mejilla = min(math.dist((c.x, c.y, c.z), (sx * R_CAB * 0.55, -R_CAB * 0.8, z_cab - R_CAB * 0.35)) for sx in (-1, 1))
        return mix(PIEL, (232, 140, 130), P["rubor"] * (1 - sstep(R_CAB * 0.1, R_CAB * 0.35, mejilla)))
    paint(cuerpo, color_piel)
    m_piel = skin_mat(nombre + "_piel", (0.9, 0.4, 0.3), sss=P["sss"])
    cuerpo.data.materials.append(m_piel)

    arm = make_rig(nombre + "_rig", [
        ("hips", (0, 0, z_cad - 0.05), (0, 0, z_cin + 0.02), None),
        ("spine", (0, 0, z_cin + 0.02), (0, 0, z_cue + 0.02), "hips"),
        ("head", (0, 0, z_cue + 0.02), (0, 0, z_cab + R_CAB), "spine"),
        ("upper_arm.L", (hombro_x, 0, z_hom), (codo_x, 0.01, P["codo_z"]), "spine"),
        ("forearm.L", (codo_x, 0.01, P["codo_z"]), (mano_x, -0.02, P["mano_z"] - 0.03), "upper_arm.L"),
        ("upper_arm.R", (-hombro_x, 0, z_hom), (-codo_x, 0.01, P["codo_z"]), "spine"),
        ("forearm.R", (-codo_x, 0.01, P["codo_z"]), (-mano_x, -0.02, P["mano_z"] - 0.03), "upper_arm.R"),
        ("thigh.L", (cad_x, 0, z_cad), (rod_x, -0.005, z_rod), "hips"),
        ("shin.L", (rod_x, -0.005, z_rod), (rod_x, 0, 0.05), "thigh.L"),
        ("thigh.R", (-cad_x, 0, z_cad), (-rod_x, -0.005, z_rod), "hips"),
        ("shin.R", (-rod_x, -0.005, z_rod), (-rod_x, 0, 0.05), "thigh.R"),
    ])
    skin_to(cuerpo, arm)
    S = Surf(cuerpo)
    R = {"arm": arm, "lids": [], "eyes": [], "cejas": [], "body": cuerpo, "estilo": estilo, "altura": z_cab + R_CAB}

    # ---------- ropa ----------
    r = ROPAS[ropa]
    zc = r["largo_chaqueta"]
    ancho_pierna = cad_x + P["pierna"] * 1.6
    es_brazo = lambda c: abs(c.x) > ancho_torso
    manga = lambda c: es_brazo(c) and c.z > P["mano_z"] + 0.04
    camisa = deform_copy(cuerpo, arm, nombre + "_camisa",
                         lambda c: (not es_brazo(c) and z_cad - 0.04 < c.z < z_cue + 0.02) or (manga(c) and c.z > z_cad - 0.1),
                         0.012, fabric(nombre + "_camisa_m", r["camisa"]))
    camisa.parent = arm
    largo_pierna = z_tob - 0.04 if zc == "tunica" else z_tob + 0.005
    pantalon = deform_copy(cuerpo, arm, nombre + "_pantalon",
                           lambda c: largo_pierna < c.z < z_cad + 0.03 and abs(c.x) < ancho_pierna, 0.014,
                           fabric(nombre + "_pantalon_m", r["pantalon"], scale=120))
    pantalon.parent = arm
    zap = deform_copy(cuerpo, arm, nombre + "_zapatos", lambda c: c.z < z_tob + 0.015 and abs(c.x) < ancho_pierna, 0.012,
                      mat(nombre + "_zapatos_m", r["zapatos"], 0.35))
    zap.parent = arm
    if r["chaqueta"]:
        if zc == "chaleco":
            keep = lambda c: z_cad < c.z < z_cue and abs(c.x) < ancho_torso          # sin mangas
        elif zc == "levita":
            keep = lambda c: (z_rod + 0.09 < c.z < z_cue + 0.01 and not es_brazo(c) and not (c.y < -0.02 and abs(c.x) < 0.03)) \
                or (manga(c) and c.z > z_cad - 0.03)
        else:  # tunica larga hasta los tobillos
            keep = lambda c: (z_tob - 0.01 < c.z < z_cue + 0.01 and abs(c.x) < max(ancho_torso, ancho_pierna)) or manga(c)
        chaqueta = deform_copy(cuerpo, arm, nombre + "_chaqueta", keep, 0.024, fabric(nombre + "_chaqueta_m", r["chaqueta"], scale=90))
        chaqueta.parent = arm
    if r["tirantes"]:
        for s in (-1, 1):
            t = surface_tube(S, [(s * 0.07, -0.3, z_cad + 0.02), (s * 0.08, -0.3, (z_cad + z_hom) / 2), (s * 0.09, -0.3, z_hom),
                                 (s * 0.09, 0.0, z_cue + 0.02), (s * 0.08, 0.3, z_pecho - 0.04)],
                             0.011, mat(nombre + "_tirante", (60, 40, 30), 0.6), off=0.035)
            bone_parent(t, arm, "spine")

    # ---------- cara ----------
    m_iris = iris_mat(nombre + "_iris", *iris)
    for s in (-1, 1):
        E, lids = make_eye(S, s * R_CAB * P["ojo_x"], z_cab + R_CAB * 0.08, R_CAB * P["ojo"], m_piel, m_iris, s=s,
                           lidcol=PIEL_OSC, sink=0.5, upper=-0.5, lower=0.65)
        bone_parent(E, arm, "head")
        R["eyes"].append(E)
        R["lids"] += lids
        color_ceja = PELOS.get(pelo) or (90, 70, 60)
        ceja_pivote = empty(nombre + "_ceja", (s * R_CAB * 0.36, -R_CAB, z_cab + R_CAB * 0.38))
        ceja = tubo_cara(S, [(s * R_CAB * (0.36 + 0.2 * u), z_cab + R_CAB * (0.4 - 0.05 * abs(u) ** 1.5))
                             for u in [i / 4 - 0.5 for i in range(5)]], R_CAB * 0.055,
                         mat(nombre + "_ceja_m", color_ceja, 0.7), off=R_CAB * 0.04)
        ceja.parent = ceja_pivote
        ceja.matrix_parent_inverse = ceja_pivote.matrix_world.inverted()
        bone_parent(ceja_pivote, arm, "head")
        R["cejas"].append(ceja_pivote)
    boca_puntos = [(R_CAB * 0.22 * u, z_cab - R_CAB * (0.45 + 0.06 * (1 - u * u))) for u in [i / 4 - 1 for i in range(9)]]
    boca = tubo_cara(S, boca_puntos, R_CAB * 0.04, mat(nombre + "_labios", (130, 50, 50), 0.4), off=R_CAB * 0.01)
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
        casco = sphere((0, R_CAB * 0.16, z_cab + R_CAB * 0.2), R_CAB * 1.02, m_pelo, sc=(0.98, 0.95, 0.88))
        bone_parent(casco, arm, "head")
        if pelo == "largo_recogido":
            mono = sphere((0, R_CAB * 0.95, z_cab + R_CAB * 0.3), R_CAB * 0.38, m_pelo)
            bone_parent(mono, arm, "head")
    if barba != "ninguna":
        color_b = color_pelo or (90, 70, 60)
        m_barba = noisy(nombre + "_barba_m", color_b, tuple(int(v * 0.8) for v in color_b), 50, 0.7)
        if barba == "bigote":
            bigote = tubo_cara(S, [(R_CAB * 0.3 * u, z_cab - R_CAB * (0.3 + 0.1 * abs(u))) for u in [i / 6 - 1 for i in range(13)]],
                               R_CAB * 0.09, m_barba, off=R_CAB * 0.06)
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
        cyl((0, -R_CAB * 0.95, -R_CAB * 0.1), R_CAB * 0.55, R_CAB * 0.06, mg, H, sc=(1.1, 0.6, 1), rot=(0.15, 0, 0))
    elif r["sombrero"] == "bombin":
        mb = mat(nombre + "_bombin_m", sc, 0.4)
        sphere((0, 0, R_CAB * 0.2), R_CAB * 0.82, mb, H, sc=(1, 1, 0.85))
        cyl((0, 0, -R_CAB * 0.025), R_CAB * 1.25, R_CAB * 0.07, mb, H, verts=48)
        torus((0, 0, 0.0), R_CAB * 0.8, R_CAB * 0.06, mat(nombre + "_cinta", (60, 50, 50), 0.5), H)
    elif r["sombrero"] == "tricornio":
        mt = mat(nombre + "_tricornio_m", sc, 0.5)
        sphere((0, 0, R_CAB * 0.15), R_CAB * 0.85, mt, H, sc=(1, 1, 0.55))
        for a in range(3):  # tres alas levantadas formando el triángulo
            ang = a * 2 * math.pi / 3 - math.pi / 2
            ala = cyl((math.cos(ang) * R_CAB * 0.62, math.sin(ang) * R_CAB * 0.62, R_CAB * 0.12), R_CAB * 0.75, R_CAB * 0.06,
                      mt, H, sc=(1, 0.35, 1), rot=(0.0, 0.0, ang + math.pi / 2), verts=40)
            ala.rotation_euler = (math.radians(75), 0, ang + math.pi / 2)
    elif r["sombrero"] == "qing":
        mq = mat(nombre + "_qing_m", sc, 0.6)
        cyl((0, 0, 0.0), R_CAB * 1.15, R_CAB * 0.5, mq, H, r2=R_CAB * 0.6, verts=48)
        sphere((0, 0, R_CAB * 0.4), R_CAB * 0.14, mat(nombre + "_boton", (200, 30, 30), 0.3), H)
    bone_parent(H, arm, "head")

    # ---------- manos: puntos de anclaje para props ----------
    for s, lado in ((1, "L"), (-1, "R")):
        mano = empty(f"{nombre}_mano.{lado}", (s * mano_x, -0.03, P["mano_z"] - 0.04))
        bone_parent(mano, arm, f"forearm.{lado}")
        R[f"mano.{lado}"] = mano

    arm.scale = (k, k, k)
    R["escala"] = k
    R["objetos"] = [o for o in bpy.data.objects if o not in antes]
    if estilo == "plano":
        from biblioteca.estilos import aplicar_plano
        aplicar_plano(R["objetos"])
    return R


def colocar(R, loc, rotz=0.0):
    k = R.get("escala", 1.0)
    R["arm"].location = loc
    R["arm"].rotation_euler = (0, 0, rotz)
    R["arm"].scale = (k, k, k)


def posar(R, **huesos):
    for nombre, rot in huesos.items():
        R["arm"].pose.bones[nombre.replace("__", ".")].rotation_euler = rot
