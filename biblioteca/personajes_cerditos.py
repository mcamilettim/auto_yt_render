"""Cerditos y lobo v2 de la referencia. Se conservan como ejemplo de la técnica y para pruebas de regresión."""
import math

from mathutils import Vector

from biblioteca.base import box, col, cyl, empty, mat, noisy, sphere, torus, tube
from biblioteca.rig import (
    Surf, bone_parent, capsule, deform_copy, fabric, fur, fuse, hair_mat, iris_mat, make_eye, make_rig, mix, paint,
    skin_mat, skin_to, sstep, surface_tube, vgroup,
)

# ---------- pig ----------
PIG_BASE = (246, 172, 176); PIG_SNOUT = (236, 140, 152); PIG_HOOF = (105, 62, 64); PIG_BELLY = (252, 196, 196)
PIG_SKIN = None

def pig2(outfit, hat, iris_c):
    global PIG_SKIN
    parts = [sphere((0, 0, 0.46), 0.3, None, sc=(1, 0.9, 1.02)), sphere((0, -0.06, 0.4), 0.25, None),
             sphere((0, 0, 0.3), 0.25, None, sc=(1, 0.9, 0.8)), sphere((0, -0.01, 0.7), 0.2, None),
             sphere((0, -0.02, 0.93), 0.25, None, sc=(1.02, 0.96, 0.92))]
    for s in (-1, 1):
        parts += capsule((s * 0.12, 0, 0.3), (s * 0.12, -0.01, 0.08), 0.075)
        parts += [sphere((s * 0.12, -0.03, 0.055), 0.085, None, sc=(1, 1.15, 0.65))]
        parts += capsule((s * 0.25, 0, 0.62), (s * 0.34, -0.04, 0.4), 0.058)
        parts += [sphere((s * 0.345, -0.045, 0.37), 0.066, None)]
        parts += [sphere((s * 0.11, -0.13, 0.84), 0.125, None)]
    parts += [cyl((0, -0.235, 0.885), 0.092, 0.13, None, rot=(math.pi / 2, 0, 0), verts=40)]
    body = fuse(parts, "pigbody", voxel=0.008)
    def colf(c):
        col_ = mix(PIG_BASE, PIG_BELLY, sstep(-0.14, -0.26, c.y) * (1 - sstep(0.5, 0.62, c.z)) * sstep(0.18, 0.28, c.z))
        sn = sstep(-0.2, -0.27, c.y) * (1 - sstep(0.09, 0.11, math.hypot(c.x, c.z - 0.885)))
        col_ = mix(col_, PIG_SNOUT, sn)
        col_ = mix(col_, PIG_HOOF, 1 - sstep(0.06, 0.085, c.z))
        hand = min(math.dist((c.x, c.y, c.z), (0.345, -0.045, 0.34)), math.dist((c.x, c.y, c.z), (-0.345, -0.045, 0.34)))
        return mix(col_, PIG_HOOF, 1 - sstep(0.035, 0.05, hand))
    paint(body, colf)
    if PIG_SKIN is None: PIG_SKIN = skin_mat("pigskin2", (0.9, 0.35, 0.3))
    skin = PIG_SKIN; body.data.materials.append(skin)
    arm = make_rig("pigrig", [("hips", (0, 0, 0.22), (0, 0, 0.5), None), ("spine", (0, 0, 0.5), (0, 0, 0.74), "hips"),
                              ("head", (0, -0.02, 0.76), (0, -0.02, 1.12), "spine"),
                              ("arm.L", (0.24, 0, 0.63), (0.345, -0.045, 0.36), "spine"), ("arm.R", (-0.24, 0, 0.63), (-0.345, -0.045, 0.36), "spine"),
                              ("leg.L", (0.12, 0, 0.3), (0.12, -0.01, 0.06), "hips"), ("leg.R", (-0.12, 0, 0.3), (-0.12, -0.01, 0.06), "hips")])
    skin_to(body, arm)
    S = Surf(body)
    cloth = fabric("cloth_" + hat, outfit)
    ov = deform_copy(body, arm, "overalls", lambda c: ((0.13 < c.z < 0.5) and not (abs(c.x) > 0.235 and c.z > 0.3)) or (0.5 <= c.z < 0.64 and c.y < -0.13 and abs(c.x) < 0.17), 0.014, cloth)
    ov.parent = arm
    R = {"arm": arm, "lids": [], "eyes": []}
    gold = mat("btnG", (235, 190, 70), 0.25, metal=0.9)
    for s in (-1, 1):
        a, n = S.near((s * 0.125, -0.35, 0.615))
        strap = surface_tube(S, [(s * 0.13, -0.3, 0.63), (s * 0.15, -0.2, 0.73), (s * 0.15, 0.0, 0.8), (s * 0.14, 0.2, 0.68), (s * 0.12, 0.3, 0.5)], 0.016, cloth, off=0.02)
        bone_parent(strap, arm, "spine")
        btn = sphere(tuple(a + n * 0.025), 0.022, gold, sc=(1, 0.6, 1)); bone_parent(btn, arm, "spine")
    nm = mat("nostril", (70, 30, 38), 0.5)
    for s in (-1, 1):
        p, n = S.front(s * 0.035, 0.888)
        nos = sphere(tuple(p + Vector((0, 0.004, 0))), 0.019, nm, sc=(1, 0.5, 1.35)); bone_parent(nos, arm, "head")
    for s in (-1, 1):
        E, lids = make_eye(S, s * 0.094, 0.99, 0.07, skin, iris_c, s=s, lidcol=PIG_BASE, sink=0.55)
        bone_parent(E, arm, "head"); R["eyes"].append(E); R["lids"] += lids
        br = surface_tube(S, [(s * (0.095 + 0.05 * u), -0.3, 1.085 + 0.012 * math.cos(u * 2)) for u in [i / 6 - 0.5 for i in range(7)]], 0.009, mat("pigbrow", (160, 85, 90), 0.6), off=0.006)
        bone_parent(br, arm, "head")
        ear = empty("ear", (s * 0.15, 0.0, 1.11), rot=(-0.35, s * 0.45, s * 0.25))
        e1 = sphere((0, 0, 0.06), 0.085, skin, ear, sc=(0.85, 0.22, 1.05)); paint(e1, lambda c: PIG_BASE)
        e2 = sphere((0, -0.012, 0.05), 0.06, skin, ear, sc=(0.75, 0.12, 0.9)); paint(e2, lambda c: PIG_SNOUT)
        bone_parent(ear, arm, "head")
    sm = surface_tube(S, [(0.075 * u, -0.3, 0.8 - 0.025 * (1 - u * u) + 0.012 * u ** 4) for u in [i / 6 - 1 for i in range(13)]], 0.0075, mat("mouth", (110, 35, 50), 0.4), off=0.001)
    bone_parent(sm, arm, "head")
    tl = tube([(0.045 * math.cos(u), 0.25 + 0.015 * u, 0.35 + 0.045 * math.sin(u)) for u in [i * 0.5 for i in range(16)]], 0.014, mat("tailpink", PIG_SNOUT, 0.45))
    bone_parent(tl, arm, "hips")
    H = empty("hatG", (0, -0.02, 1.13))
    if hat == "straw":
        hm = noisy("strawhat2", (238, 205, 120), (196, 160, 80), 60, 0.85)
        w1 = hm.node_tree.nodes.new("ShaderNodeTexWave"); w1.inputs["Scale"].default_value = 90; w1.wave_type = "RINGS"
        bp = hm.node_tree.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.4
        hm.node_tree.links.new(w1.outputs["Fac"], bp.inputs["Height"]); hm.node_tree.links.new(bp.outputs["Normal"], hm.node_tree.nodes["Principled BSDF"].inputs["Normal"])
        g = empty("h", (0, 0.02, 0.02), H, rot=(-0.15, 0.12, 0))
        brim = cyl((0, 0, 0), 0.34, 0.02, hm, g, verts=64)
        sd = brim.modifiers.new("w", "SIMPLE_DEFORM"); sd.deform_method = "BEND"; sd.angle = 0.35; sd.deform_axis = "Y"
        cyl((0, 0, 0.075), 0.17, 0.15, hm, g, r2=0.15, verts=48)
        torus((0, 0, 0.025), 0.165, 0.02, mat("hatband2", (190, 60, 55), 0.6), g)
    elif hat == "cap":
        cm = fabric("capF", (60, 115, 210))
        g = empty("h", (0, 0.0, -0.03), H, rot=(-0.12, 0, 0))
        sphere((0, 0.01, 0.0), 0.235, cm, g, sc=(1, 1, 0.6))
        cyl((0, -0.24, -0.03), 0.13, 0.018, cm, g, sc=(1.1, 0.75, 1), rot=(0.18, 0, 0))
        sphere((0, 0.01, 0.14), 0.025, cm, g)
    else:
        hm = mat("helmet2", (240, 130, 25), 0.22, spec=0.8); hm.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.8
        g = empty("h", (0, 0.0, -0.03), H, rot=(-0.08, 0, 0))
        sphere((0, 0, 0.0), 0.245, hm, g, sc=(1, 1, 0.68))
        cyl((0, -0.01, -0.03), 0.29, 0.022, hm, g, verts=64, sc=(1, 1.05, 1))
        box((0, 0, 0.165), (0.045, 0.42, 0.04), hm, g, bevel=0.018)
    bone_parent(H, arm, "head")
    R["body"] = body
    return R

# ---------- wolf ----------
W_GREY = (118, 122, 136); W_DARK = (80, 82, 96); W_WHITE = (232, 232, 236)

def wolf2():
    parts = [sphere((0, 0, 0.8), 0.24, None, sc=(1, 0.85, 0.8)), sphere((0, -0.02, 1.12), 0.27, None, sc=(1, 0.8, 1.12)),
             sphere((0, -0.05, 0.94), 0.22, None), sphere((0, -0.03, 1.6), 0.19, None, sc=(1, 1.05, 0.95)),
             sphere((0, -0.13, 1.67), 0.1, None, sc=(1.6, 0.7, 0.5))]
    parts += capsule((0, 0, 1.3), (0, -0.03, 1.52), 0.1)
    parts += capsule((0, -0.12, 1.57), (0, -0.37, 1.545), 0.09, 0.055)
    parts += capsule((0, -0.12, 1.5), (0, -0.3, 1.49), 0.055, 0.04)
    for s in (-1, 1):
        parts += [sphere((s * 0.14, -0.05, 1.55), 0.09, None, sc=(1, 1, 0.9))]
        parts += capsule((s * 0.12, 0, 0.75), (s * 0.13, 0.02, 0.42), 0.09, 0.075)
        parts += capsule((s * 0.13, 0.02, 0.42), (s * 0.13, 0.05, 0.1), 0.07, 0.06)
        parts += [sphere((s * 0.13, -0.06, 0.055), 0.08, None, sc=(1, 2.0, 0.6))]
        parts += capsule((s * 0.25, 0, 1.3), (s * 0.34, -0.02, 0.98), 0.07, 0.06)
        parts += capsule((s * 0.34, -0.02, 0.98), (s * 0.37, -0.06, 0.72), 0.058, 0.05)
        parts += [sphere((s * 0.375, -0.07, 0.67), 0.072, None, sc=(1, 1, 1.25))]
    body = fuse(parts, "wolfbody", voxel=0.009)
    def white_w(c):
        m1 = sstep(-0.2, -0.27, c.y) * (1 - sstep(1.56, 1.6, c.z)) * sstep(1.4, 1.45, c.z)
        m2 = sstep(-0.14, -0.2, c.y) * sstep(0.84, 0.92, c.z) * (1 - sstep(1.22, 1.3, c.z)) * (1 - sstep(0.13, 0.18, abs(c.x)))
        m3 = sstep(0.12, 0.17, abs(c.x)) * sstep(1.47, 1.5, c.z) * (1 - sstep(1.6, 1.63, c.z)) * (1 - sstep(0.0, 0.05, c.y))
        return max(m1, m2, m3)
    def colf(c):
        col_ = mix(W_GREY, W_DARK, sstep(0.0, 0.18, c.y) * 0.6)
        col_ = mix(col_, W_WHITE, white_w(c))
        return mix(col_, W_DARK, 1 - sstep(0.07, 0.1, c.z))
    paint(body, colf)
    wskin = skin_mat("wolfskin", (0.5, 0.4, 0.4), sss=0.1, rough=0.7, pores=0.15); body.data.materials.append(wskin)
    arm = make_rig("wolfrig", [("hips", (0, 0, 0.6), (0, 0, 0.92), None), ("spine", (0, 0, 0.92), (0, 0, 1.32), "hips"),
                               ("head", (0, -0.02, 1.38), (0, -0.02, 1.8), "spine"),
                               ("arm.L", (0.24, 0, 1.3), (0.375, -0.07, 0.68), "spine"), ("arm.R", (-0.24, 0, 1.3), (-0.375, -0.07, 0.68), "spine"),
                               ("leg.L", (0.12, 0, 0.78), (0.13, 0.04, 0.06), "hips"), ("leg.R", (-0.12, 0, 0.78), (-0.13, 0.04, 0.06), "hips")])
    skin_to(body, arm)
    S = Surf(body)
    pants = fabric("wpants2", (92, 70, 128), scale=120)
    pn = deform_copy(body, arm, "pants", lambda c: 0.3 < c.z < 0.9 and not (abs(c.x) > 0.22 and c.z > 0.6), 0.016, pants)
    pn.parent = arm
    patch = box((0.14, -0.21, 0.66), (0.1, 0.012, 0.1), fabric("wpatch2", (150, 112, 70), scale=60), rot=(0.1, 0, 0.3), bevel=0.004)
    bone_parent(patch, arm, "hips")
    vgroup(body, "greyfur", lambda c: (1 - white_w(c)) if (c.z > 0.88 or abs(c.x) > 0.22 or c.z < 0.34) else 0.0)
    vgroup(body, "whitefur", lambda c: white_w(c))
    fur(body, hair_mat("furG", (100, 104, 118), (150, 154, 168)), 9000, 0.03, "greyfur", child=8)
    fur(body, hair_mat("furW", (215, 215, 222), (245, 245, 250)), 3000, 0.025, "whitefur", child=8)
    R = {"arm": arm, "lids": [], "eyes": []}
    p, n = S.front(0, 1.555)
    nose = sphere(tuple(p + n * 0.01), 0.045, mat("wnose", (25, 22, 26), 0.12, spec=1.0), sc=(1.35, 1.0, 0.9)); bone_parent(nose, arm, "head")
    iris = iris_mat("irisW", (250, 205, 70), (215, 130, 25))
    for s in (-1, 1):
        E, lids = make_eye(S, s * 0.078, 1.668, 0.058, wskin, iris, upper=-0.25, lower=0.75, tilt=0.35, s=s, sink=0.45, lidcol=W_GREY)
        bone_parent(E, arm, "head"); R["eyes"].append(E); R["lids"] += lids
        br = surface_tube(S, [(s * (0.075 + 0.05 * u), -0.3, 1.735 - 0.035 * u) for u in [i / 6 - 0.5 for i in range(7)]], 0.02, mat("wbrow2", (45, 45, 55), 0.7), off=0.026)
        bone_parent(br, arm, "head")
        ear = empty("wear", (s * 0.11, 0.02, 1.76), rot=(0.05, s * 0.32, 0))
        e1 = cyl((0, 0, 0.1), 0.08, 0.22, wskin, ear, r2=0.006, sc=(1, 0.45, 1)); paint(e1, lambda c: W_GREY)
        cyl((0, -0.016, 0.09), 0.05, 0.16, mat("earin2", (225, 150, 160), 0.6), ear, r2=0.004, sc=(1, 0.3, 1))
        bone_parent(ear, arm, "head")
        fp, fn_ = S.front(s * 0.04, 1.5)
        fang = cyl(tuple(fp + Vector((0, 0.012, -0.012))), 0.012, 0.035, mat("fang", (250, 248, 238), 0.25), r2=0.0, rot=(math.pi, 0, 0))
        bone_parent(fang, arm, "head")
    mpts = [(0.07 * u, -0.3 + 0.12 * abs(u), 1.505 + 0.02 * abs(u)) for u in [i / 6 - 1 for i in range(13)]]
    ml = surface_tube(S, mpts, 0.008, mat("wmouth", (40, 20, 25), 0.5), off=0.001); bone_parent(ml, arm, "head")
    op, on = S.front(0, 1.5)
    R["omouth"] = sphere(tuple(op + Vector((0, 0.01, 0))), 0.04, mat("wmouthO", (60, 20, 28), 0.5), sc=(1, 0.5, 0.9))
    bone_parent(R["omouth"], arm, "head"); R["omouth_s"] = R["omouth"].scale.copy(); R["omouth"].scale = (0, 0, 0)
    tail = fuse(capsule((0, 0.2, 0.78), (0, 0.5, 0.5), 0.075, 0.09) + [sphere((0, 0.56, 0.44), 0.075, None)], "wtail", voxel=0.012)
    paint(tail, lambda c: mix(W_GREY, W_WHITE, sstep(0.5, 0.56, c.y))); tail.data.materials.append(wskin)
    fur(tail, hair_mat("furT", (110, 114, 128), (200, 200, 210)), 2500, 0.05, child=8)
    bone_parent(tail, arm, "hips")
    R["body"] = body
    return R

def place(R, loc, rotz, k=1.0):
    R["arm"].location = loc; R["arm"].rotation_euler = (0, 0, rotz); R["arm"].scale = (k, k, k)

def pose(R, **bones):
    for bn, rot in bones.items():
        R["arm"].pose.bones[bn.replace("_", ".")].rotation_euler = rot
