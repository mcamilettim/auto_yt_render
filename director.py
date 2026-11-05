"""Director: convierte una escena del storyboard en cuadros PNG animados.

    herramientas/blender.sh -P director.py -- storyboard.json e01 salida/e01 [--desde 1 --hasta N] [--estilo caricatura]

Todo se hornea en keyframes cuadro a cuadro (pose, ubicación, cámara, props), así el render es determinista y se
puede partir por tramos de cuadros en distintos runners.
"""
import json
import math
import os
import sys
import time

import bpy

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
bpy.ops.wm.read_factory_settings(use_empty=True)

from mathutils import Euler, Vector  # noqa: E402

from biblioteca.base import col, scene  # noqa: E402
from biblioteca.escenario import PROPS, SETS, _mesa, luz  # noqa: E402
from biblioteca.persona import colocar, persona  # noqa: E402
from biblioteca.render_cfg import configurar_render  # noqa: E402

# ---------------- utilidades ----------------
TRANSICION = 0.3            # s para mezclar poses/expresiones
VELOCIDAD = 0.9             # m/s al caminar (adulto); se escala con la estatura
PLANOS = {"plano_general": (2.4, 0.5), "plano_medio": (1.05, 0.72), "primer_plano": (0.5, 0.9), "detalle": (0.3, 0.6)}
#                            alto visible (en alturas del actor), altura del punto mirado (fracción de la altura)


def suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def angulo_hacia(desde, hacia):
    dx, dy = hacia[0] - desde[0], hacia[1] - desde[1]
    if abs(dx) + abs(dy) < 1e-6:
        return None
    return math.atan2(dx, -dy)   # el actor mira a -y con rotz=0


def mezclar_angulo(a, b, t):
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * t


# ---------------- poses ----------------
HUESOS = ("hips", "spine", "head", "upper_arm.L", "forearm.L", "upper_arm.R", "forearm.R",
          "thigh.L", "shin.L", "thigh.R", "shin.R")


def pose_vacia():
    return {h: [0.0, 0.0, 0.0] for h in HUESOS}


def sumar(p, hueso, x=0.0, y=0.0, z=0.0):
    v = p[hueso]
    v[0] += x
    v[1] += y
    v[2] += z


def mezclar_pose(a, b, t):
    return {h: [lerp(a[h][i], b[h][i], t) for i in range(3)] for h in HUESOS}


# Ejes medidos en el rig (herramientas/diagnostico_rig.py):
#   upper_arm/forearm x<0 -> mano hacia adelante/arriba; upper_arm.L z<0 -> brazo se abre (en .R es z>0)
#   thigh x<0 -> pierna adelante; shin x>0 -> rodilla se dobla; head x>0 -> cabeza baja; head y -> gira; head z -> inclina


def pose_idle(t, semilla):
    p = pose_vacia()
    resp = math.sin(2 * math.pi * 0.25 * t + semilla)
    sumar(p, "spine", x=0.015 * resp)
    sumar(p, "head", x=0.02 * math.sin(2 * math.pi * 0.17 * t + semilla * 2), y=0.04 * math.sin(2 * math.pi * 0.09 * t + semilla))
    for lado, s in (("L", 1), ("R", -1)):
        sumar(p, f"upper_arm.{lado}", x=0.03 * resp, z=-s * 0.08)
        sumar(p, f"forearm.{lado}", x=-0.12)
    return p


def pose_caminar(t, fase_paso):
    p = pose_idle(t, 0.0)
    a = math.sin(fase_paso)
    sumar(p, "thigh.L", x=-0.45 * a)
    sumar(p, "thigh.R", x=0.45 * a)
    sumar(p, "shin.L", x=0.55 * max(0.0, -math.cos(fase_paso)) + 0.05)
    sumar(p, "shin.R", x=0.55 * max(0.0, math.cos(fase_paso)) + 0.05)
    sumar(p, "upper_arm.L", x=0.35 * a)
    sumar(p, "upper_arm.R", x=-0.35 * a)
    sumar(p, "forearm.L", x=-0.25)
    sumar(p, "forearm.R", x=-0.25)
    sumar(p, "spine", y=0.06 * a)
    return p


def pose_accion(nombre, t, local, actor, estado):
    """local = segundos desde que empezó la acción."""
    s = estado["semilla"]
    if nombre == "hablar":
        p = pose_idle(t, s)
        sumar(p, "upper_arm.R", x=-0.35 - 0.12 * math.sin(2 * math.pi * 0.7 * local), z=0.15)
        sumar(p, "forearm.R", x=-0.9 - 0.2 * math.sin(2 * math.pi * 1.1 * local))
        sumar(p, "head", x=0.04 * math.sin(2 * math.pi * 1.6 * local))
        return p
    if nombre == "asentir":
        p = pose_idle(t, s)
        amp = 0.22 * (1 - suave((local - 1.2) / 0.4))
        sumar(p, "head", x=amp * max(0.0, math.sin(2 * math.pi * 2.0 * local)))
        return p
    if nombre == "negar":
        p = pose_idle(t, s)
        amp = 0.35 * (1 - suave((local - 1.2) / 0.4))
        sumar(p, "head", y=amp * math.sin(2 * math.pi * 2.0 * local))
        return p
    if nombre == "senalar":
        p = pose_idle(t, s)
        sumar(p, "upper_arm.R", x=-1.35, z=0.25)
        sumar(p, "forearm.R", x=-0.1)
        return p
    if nombre in ("levantar", "sostener"):
        p = pose_idle(t, s)
        if nombre == "levantar" and local < 0.5:            # se agacha a tomar
            k = suave(local / 0.5)
            sumar(p, "spine", x=0.35 * k)
            sumar(p, "upper_arm.L", x=-0.7 * k)
            sumar(p, "forearm.L", x=-0.2 * k)
        else:                                               # lo sostiene frente al pecho y lo mira
            sumar(p, "upper_arm.L", x=-0.55, z=0.2)
            sumar(p, "forearm.L", x=-1.25)
            sumar(p, "head", x=0.18)
        return p
    if nombre == "sentarse":
        p = pose_vacia()
        sumar(p, "thigh.L", x=-1.45)
        sumar(p, "thigh.R", x=-1.45)
        sumar(p, "shin.L", x=1.45)
        sumar(p, "shin.R", x=1.45)
        sumar(p, "forearm.L", x=-0.6)
        sumar(p, "forearm.R", x=-0.6)
        sumar(p, "spine", x=0.05 * math.sin(2 * math.pi * 0.25 * t))
        return p
    if nombre == "escribir":
        p = pose_idle(t, s)
        sumar(p, "head", x=0.38)
        sumar(p, "spine", x=0.18)
        sumar(p, "upper_arm.R", x=-0.75, z=0.15)
        sumar(p, "forearm.R", x=-1.0 + 0.07 * math.sin(2 * math.pi * 3 * local))
        sumar(p, "upper_arm.L", x=-0.55, z=-0.1)
        sumar(p, "forearm.L", x=-1.0)
        return p
    return pose_idle(t, s)       # idle, mirar, soltar, caminar_hasta terminado


# ---------------- expresiones ----------------
# (ceja_dz en R_cab, párpado superior, párpado inferior, boca abierta 0..1)
EXPRESIONES = {
    "neutral": (0.0, -0.5, 0.65, 0.0),
    "feliz": (0.06, -0.38, 0.42, 0.22),
    "sorpresa": (0.16, -0.9, 0.8, 0.85),
    "preocupado": (0.08, -0.42, 0.6, 0.08),
    "enojado": (-0.1, -0.18, 0.55, 0.0),
    "pensativo": (-0.03, -0.3, 0.6, 0.0),
}


def parpadeo(t, semilla):
    """1 durante un parpadeo (0.15 s), cada 3-5 s según la semilla."""
    periodo = 3.0 + (semilla * 7.3) % 2.0
    fase = (t + semilla) % periodo
    return 1.0 - suave(abs(fase - 0.075) / 0.075) if fase < 0.15 else 0.0


# ---------------- construcción ----------------

def cargar(ruta_storyboard, id_escena):
    d = json.load(open(ruta_storyboard, encoding="utf-8"))
    escena = next(e for e in d["escenas"] if e["id"] == id_escena)
    return d, escena


def construir(d, escena, estilo):
    info_set = SETS[escena["set"]]() or {}
    if scene.world is None:
        from biblioteca.base import world
        world((70, 64, 58), 0.5)
    luz(escena["luz"], escena["set"])
    actores = {}
    for i, a in enumerate(escena["actores"]):
        params = dict(d["elenco"][a["ref"]]["params"])
        R = persona(nombre=a["ref"], estilo=estilo, **params)
        colocar(R, (a["pos"][0], a["pos"][1], 0), 0.0)
        R["semilla"] = (sum(map(ord, a["ref"])) % 97) / 13.0
        actores[a["ref"]] = R
    props = {}
    mesa = info_set.get("mesa")
    for p in escena.get("props", []):
        spec = d["elenco"][p["ref"]]
        raiz, apoyo = PROPS[spec["nombre"]](**(spec.get("params") or {}))
        z = apoyo
        if p["sobre"] == "mesa":
            if mesa is None or math.dist(mesa[:2], p["pos"]) > 0.7:
                mesa = _mesa(p["pos"][0], p["pos"][1] + 0.05, 0.72, 0.8, 0.5)
            z += mesa[2]
        raiz.location = (p["pos"][0], p["pos"][1], z)
        props[p["ref"]] = {"obj": raiz, "reposo": Vector(raiz.location), "rot_reposo": Euler(raiz.rotation_euler)}
    return actores, props


def linea_de_tiempo(acciones, duracion):
    """[(t_inicio, t_fin, item)] para acciones con 'accion' y [(t, expresion)] para expresiones."""
    con_accion = [a for a in acciones if "accion" in a]
    tramos = []
    for i, a in enumerate(con_accion):
        fin = con_accion[i + 1]["t"] if i + 1 < len(con_accion) else duracion
        tramos.append((a["t"], fin, a))
    expresiones = [(a["t"], a["expresion"]) for a in acciones if "expresion" in a]
    if not expresiones or expresiones[0][0] > 0:
        expresiones.insert(0, (0.0, "neutral"))
    return tramos, expresiones


def preparar_estado(escena, actores, props):
    estados = {}
    for a in escena["actores"]:
        tramos, expresiones = linea_de_tiempo(a["acciones"], escena["duracion"])
        R = actores[a["ref"]]
        estados[a["ref"]] = {"tramos": tramos, "expresiones": expresiones, "pos0": tuple(a["pos"]),
                             "mira_a": a.get("mira_a", "camara"), "semilla": R["semilla"]}
    return estados


def posicion_en(estado, t, R):
    """Recorre los tramos de caminar hasta t. Devuelve (x, y, caminando, fase_paso, rumbo)."""
    pos = list(estado["pos0"])
    caminando, fase, rumbo = False, 0.0, None
    velocidad = VELOCIDAD * R.get("escala", 1.0)
    for inicio, fin, item in estado["tramos"]:
        if inicio > t:
            break
        if item["accion"] != "caminar_hasta":
            continue
        destino = item["pos"]
        distancia = math.dist(pos, destino)
        if distancia < 1e-4:
            continue
        dur = min(distancia / velocidad, fin - inicio)
        avance = min(1.0, (t - inicio) / dur) if dur > 0 else 1.0
        rumbo = angulo_hacia(pos, destino)
        if avance < 1.0:
            caminando = True
            recorrido = distancia * avance
            fase = recorrido / (0.55 * R.get("escala", 1.0)) * math.pi
        pos = [lerp(pos[0], destino[0], avance), lerp(pos[1], destino[1], avance)]
        if avance < 1.0:
            break
    return pos[0], pos[1], caminando, fase, rumbo


def tramo_activo(estado, t):
    activo = None
    for inicio, fin, item in estado["tramos"]:
        if inicio <= t:
            activo = (inicio, fin, item)
    return activo


def expresion_en(estado, t):
    actual, previa, t_cambio = "neutral", "neutral", 0.0
    for ti, nombre in estado["expresiones"]:
        if ti <= t:
            previa, actual, t_cambio = actual, nombre, ti
    k = suave((t - t_cambio) / TRANSICION)
    a, b = EXPRESIONES[previa], EXPRESIONES[actual]
    return tuple(lerp(a[i], b[i], k) for i in range(4))


def punto_cabeza(R, x, y, frac=0.85):
    return Vector((x, y, R["altura"] * R.get("escala", 1.0) * frac))


def hornear(d, escena, actores, props, cam, fps, desde, hasta):
    estados = preparar_estado(escena, actores, props)
    vl = bpy.context.view_layer
    dur = escena["duracion"]
    camara = escena["camara"]
    objetivo = actores[camara["objetivo"]]
    est_obj = estados[camara["objetivo"]]
    ultima_pose = {ref: pose_vacia() for ref in actores}
    sostenido = {}       # ref_prop -> (ref_actor, t_toma)
    for ref, est in estados.items():
        for inicio, _fin, item in est["tramos"]:
            if item["accion"] == "levantar":
                sostenido.setdefault(item["objeto"], []).append(("toma", inicio + 0.45, ref))
            if item["accion"] == "soltar":
                for pref, eventos in sostenido.items():
                    if eventos and eventos[-1][2] == ref:
                        eventos.append(("suelta", inicio, ref))
    for f in range(desde, hasta + 1):
        t = min((f - 1) / fps, dur)
        scene.frame_set(f)
        posiciones = {}
        for ref, R in actores.items():
            est = estados[ref]
            x, y, caminando, fase, rumbo = posicion_en(est, t, R)
            posiciones[ref] = (x, y)
            activo = tramo_activo(est, t)
            if caminando:
                objetivo_pose = pose_caminar(t, fase)
            elif activo:
                inicio, _fin, item = activo
                objetivo_pose = pose_accion(item["accion"], t, t - inicio, item, est)
            else:
                objetivo_pose = pose_idle(t, est["semilla"])
            # mantiene el objeto en la mano después de levantar, aunque cambie de acción
            sujeta = any(evs and evs[-1][0] == "toma" and evs[-1][2] == ref and evs[-1][1] <= t for evs in sostenido.values())
            if sujeta and activo and activo[2]["accion"] not in ("levantar", "escribir", "sentarse"):
                sumar(objetivo_pose, "upper_arm.L", x=-0.55, z=0.2)
                sumar(objetivo_pose, "forearm.L", x=-1.25)
            k = 1.0 if f == desde else min(1.0, (1 / fps) / TRANSICION * 2.2)
            pose = mezclar_pose(ultima_pose[ref], objetivo_pose, k) if f != desde else objetivo_pose
            ultima_pose[ref] = pose
            # rumbo del cuerpo
            mira = est["mira_a"]
            if caminando and rumbo is not None:
                rotz = rumbo
            elif activo and activo[2].get("accion") in ("senalar", "mirar") and activo[2].get("objetivo") in {**actores, **props}:
                obj = activo[2]["objetivo"]
                if obj in props:
                    destino = tuple(props[obj]["obj"].location)[:2]
                else:
                    destino = posiciones.get(obj, estados[obj]["pos0"] if obj in estados else (x, y - 1))
                rotz = angulo_hacia((x, y), destino) or 0.0
            elif mira in props:
                rotz = angulo_hacia((x, y), tuple(props[mira]["reposo"])[:2]) or 0.0
            elif mira in actores and mira != ref:
                otro = estados[mira]["pos0"]
                rotz = angulo_hacia((x, y), otro) or 0.0
            else:
                rotz = angulo_hacia((x, y), (cam["pos"].x, cam["pos"].y)) or 0.0
                rotz *= 0.6        # hacia la cámara, sin girar del todo
            arm = R["arm"]
            previo = arm.get("rotz_prev")
            if previo is not None:
                rotz = mezclar_angulo(previo, rotz, 0.18)
            arm["rotz_prev"] = rotz
            z_base = 0.0
            if activo and activo[2]["accion"] == "sentarse":
                z_base = -(R["z_cad"] - R["z_rod"]) * R.get("escala", 1.0) * suave((t - activo[0]) / 0.6)
            arm.location = (x, y, z_base)
            arm.rotation_euler = (0, 0, rotz)
            arm.keyframe_insert("location", frame=f)
            arm.keyframe_insert("rotation_euler", frame=f)
            for h in HUESOS:
                pb = arm.pose.bones[h]
                pb.rotation_euler = pose[h]
                pb.keyframe_insert("rotation_euler", frame=f)
            # cara
            ceja_dz, sup, inf, boca = expresion_en(est, t)
            if activo and activo[2]["accion"] == "hablar":
                boca = max(boca, 0.15 + 0.55 * abs(math.sin(2 * math.pi * 3.1 * t + est["semilla"])) * (0.6 + 0.4 * math.sin(7.3 * t)))
            cierre = parpadeo(t, est["semilla"])
            for i, lid in enumerate(R["lids"]):
                if i % 2 == 0:
                    lid.rotation_euler.x = lerp(sup, 0.55, cierre)
                else:
                    lid.rotation_euler.x = math.pi + lerp(inf, 0.05, cierre)
                lid.keyframe_insert("rotation_euler", index=0, frame=f)
            for ceja in R["cejas"]:
                ceja.location.z = ceja["base_z"] + ceja_dz * R["R_cab"]
                ceja.keyframe_insert("location", index=2, frame=f)
            e = R["boca_escala"]
            R["boca"].scale = (e.x * boca, e.y * max(boca, 0.001), e.z * boca)
            R["boca"].keyframe_insert("scale", frame=f)
        vl.update()
        # props sostenidos siguen la mano
        for pref, P in props.items():
            evs = [e for e in sostenido.get(pref, []) if e[1] <= t]
            o = P["obj"]
            if evs and evs[-1][0] == "toma":
                R = actores[evs[-1][2]]
                mano = R["mano.L"].matrix_world.translation
                k = suave((t - evs[-1][1]) / 0.25)
                o.location = P["reposo"].lerp(mano, k)
                o.rotation_euler = (P["rot_reposo"].x, P["rot_reposo"].y + 0.6 * k, R["arm"].rotation_euler.z)
            elif evs and evs[-1][0] == "suelta":
                o.location = Vector((o.location.x, o.location.y, P["reposo"].z if P["reposo"].z < 0.05 else 0.012))
            else:
                o.location = P["reposo"]
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("rotation_euler", frame=f)
        # cámara
        mover_camara(cam, camara, objetivo, posiciones[camara["objetivo"]], t, dur, f)


def crear_camara(d):
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    col.objects.link(cam)
    scene.camera = cam
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.lens = 35
    cd.clip_end = 300
    return {"obj": cam, "pos": Vector((0, -6, 1.2))}


def mover_camara(cam, camara, R, pos_xy, t, dur, f):
    k = suave(t / dur) if dur > 0 else 1.0
    mov = camara["movimiento"]
    alto_a, frac_a = PLANOS[camara["desde"]]
    alto_b, frac_b = PLANOS[camara["hasta"]]
    if mov == "fijo":
        alto_b, frac_b = alto_a, frac_a
    if mov == "dolly_out" and alto_b < alto_a:
        alto_a, alto_b, frac_a, frac_b = alto_b, alto_a, frac_b, frac_a
    estatura = R["altura"] * R.get("escala", 1.0)
    visible = lerp(alto_a, alto_b, k) * estatura
    foco_z = lerp(frac_a, frac_b, k) * estatura
    medio_fov = math.atan(12 / 35)
    distancia = visible / 2 / math.tan(medio_fov)
    azimut = math.radians(8)
    elevacion = 0.08 * estatura
    lateral = 0.0
    if mov == "orbita":
        azimut = math.radians(lerp(-30, 30, k))
    elif mov == "paneo_izq":
        lateral = lerp(0.6, -0.6, k)
    elif mov == "paneo_der":
        lateral = lerp(-0.6, 0.6, k)
    elif mov == "grua_arriba":
        elevacion = lerp(0.0, 0.9 * estatura, k)
    foco = Vector((pos_xy[0] + lateral, pos_xy[1], foco_z))
    pos = foco + Vector((math.sin(azimut) * distancia, -math.cos(azimut) * distancia, elevacion))
    o = cam["obj"]
    o.location = pos
    o.rotation_euler = (foco - pos).to_track_quat("-Z", "Y").to_euler()
    cam["pos"] = pos
    o.keyframe_insert("location", frame=f)
    o.keyframe_insert("rotation_euler", frame=f)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    ruta, id_escena, salida = args[0], args[1], os.path.abspath(args[2])
    opciones = dict(zip(args[3::2], args[4::2]))
    t0 = time.time()
    d, escena = cargar(ruta, id_escena)
    fps = d["fps"]
    estilo = opciones.get("--estilo") or d.get("estilo", "caricatura")
    total = max(1, math.ceil(escena["duracion"] * fps))
    desde = int(opciones.get("--desde", 1))
    hasta = min(int(opciones.get("--hasta", total)), total)
    actores, props = construir(d, escena, estilo)
    cam = crear_camara(d)
    if estilo == "plano":
        from biblioteca.estilos import aplicar_plano
        aplicar_plano(list(bpy.data.objects))
    print("CONSTRUCCION", round(time.time() - t0, 1), flush=True)
    hornear(d, escena, actores, props, cam, fps, desde, hasta)
    print("HORNEADO", round(time.time() - t0, 1), flush=True)
    ancho, alto = d["resolucion"]
    configurar_render(ancho, alto, d.get("calidad", "rapida"), fps)
    scene.frame_start, scene.frame_end = desde, hasta
    os.makedirs(salida, exist_ok=True)
    scene.render.filepath = salida + os.sep
    t1 = time.time()
    bpy.ops.render.render(animation=True)
    cuadros = hasta - desde + 1
    print(f"DIRECTOR OK escena={id_escena} cuadros={desde}-{hasta} construccion+horneado={t1 - t0:.1f}s "
          f"render={time.time() - t1:.1f}s s_por_cuadro={(time.time() - t1) / cuadros:.2f}", flush=True)


main()
