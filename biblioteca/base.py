"""Base 3D: materiales, primitivas, luces y cielo. Extraído de la referencia de Claude (lib3d.py).

Uso dentro de Blender, después de `bpy.ops.wm.read_factory_settings(use_empty=True)`:
    from biblioteca.base import *
"""
import math
import os

import bpy
from mathutils import Vector

FONT = ("C:/Windows/Fonts/arialbd.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
scene = bpy.context.scene
col = scene.collection
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def lin(c): c = c / 255; return c / 12.92 if c < 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def rgb(c): return (lin(c[0]), lin(c[1]), lin(c[2]), 1)

# ---------------- materials ----------------
MATS = {}
def mat(name, c, rough=0.5, emit=0.0, metal=0.0, alpha=1.0, spec=0.5):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgb(c)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if emit:
        b.inputs["Emission Color"].default_value = rgb(c); b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha; m.blend_method = "BLEND"; setattr(m, "shadow_method", "NONE") if hasattr(m, "shadow_method") else None
    MATS[name] = m; return m

def wood(name, c1, c2, scale=3.0, direction="X", distort=5.0, rough=0.55):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.bands_direction = direction
    wv.inputs["Scale"].default_value = 2.0; wv.inputs["Distortion"].default_value = distort
    wv.inputs["Detail"].default_value = 3.0
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = rgb(c1); cr.color_ramp.elements[1].color = rgb(c2)
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(wv.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough
    MATS[name] = m; return m

def noisy(name, c1, c2, scale=8.0, rough=0.8):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 4
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = rgb(c1); cr.color_ramp.elements[1].color = rgb(c2)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    MATS[name] = m; return m

# ---------------- primitives ----------------
def _fin(o, m, parent, smooth=True):
    if m: o.data.materials.append(m)
    if smooth and o.type == "MESH":
        for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o

def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0), scale=1.0):
    e = bpy.data.objects.new(name, None); col.objects.link(e)
    e.location = loc; e.rotation_euler = rot; e.scale = (scale, scale, scale)
    if parent: e.parent = parent
    return e

def sphere(loc, r, m, parent=None, sc=(1, 1, 1), rot=(0, 0, 0), seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = sc; return _fin(o, m, parent)

def ico(loc, r, m, parent=None, sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    return _fin(bpy.context.object, m, parent)

def cyl(loc, r, depth, m, parent=None, rot=(0, 0, 0), r2=None, verts=32, sc=(1, 1, 1)):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = sc
    _fin(o, m, parent)
    for p in o.data.polygons:                                         # keep caps flat-shaded
        if abs(p.normal.z) > 0.99: p.use_smooth = False
    return o

def box(loc, size, m, parent=None, bevel=0.015, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size
    if bevel:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bm = o.modifiers.new("b", "BEVEL"); bm.width = bevel; bm.segments = 3; bm.limit_method = "NONE"
        bm.use_clamp_overlap = True
    return _fin(o, m, parent, smooth=False)

def torus(loc, R, r, m, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=40, minor_segments=12)
    return _fin(bpy.context.object, m, parent)

def tube(points, r, m, parent=None):
    cu = bpy.data.curves.new("tube", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r; cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(points) - 1)
    for p, (x, y, z) in zip(sp.points, points): p.co = (x, y, z, 1)
    o = bpy.data.objects.new("tube", cu); col.objects.link(o); o.data.materials.append(m)
    if parent: o.parent = parent
    return o

def surf(r, x, z, off=0.0):      # y on the front (-y) of a sphere of radius r centred at origin
    return -math.sqrt(max(1e-6, r * r - x * x - z * z)) - off

def star_obj(loc, r, m, parent=None, depth=0.02):
    me = bpy.data.meshes.new("star"); verts = []
    for i in range(10):
        a = i * math.pi / 5 + math.pi / 2; rr = r if i % 2 == 0 else r * 0.45
        verts.append((rr * math.cos(a), 0, rr * math.sin(a)))
    me.from_pydata(verts, [], [list(range(10))]); o = bpy.data.objects.new("star", me); col.objects.link(o)
    s = o.modifiers.new("s", "SOLIDIFY"); s.thickness = depth; s.offset = 0
    b = o.modifiers.new("b", "BEVEL"); b.width = depth * 0.3; b.segments = 2
    o.location = loc; o.data.materials.append(m)
    if parent: o.parent = parent
    return o

def text3d(body, loc, size, m, rot=(math.pi / 2, 0, 0)):
    cu = bpy.data.curves.new("txt", "FONT"); cu.body = body; cu.size = size; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    cu.extrude = size * 0.09; cu.bevel_depth = size * 0.025; cu.bevel_resolution = 3
    try: cu.font = bpy.data.fonts.load(FONT)
    except Exception: pass
    o = bpy.data.objects.new("txt", cu); col.objects.link(o); o.location = loc; o.rotation_euler = rot
    o.data.materials.append(m); return o

def wpos(o, local=(0, 0, 0)):
    m = o.matrix_basis.copy(); p = o.parent
    while p: m = p.matrix_basis @ m; p = p.parent
    return m @ Vector(local)


# ---------------- sets ----------------
def light(kind, loc, energy, color=(1, 1, 1), size=1.0, rot=(0, 0, 0), name="L"):
    l = bpy.data.lights.new(name, kind); l.energy = energy; l.color = color
    if kind == "AREA": l.size = size
    else: l.shadow_soft_size = size
    o = bpy.data.objects.new(name, l); col.objects.link(o); o.location = loc; o.rotation_euler = rot
    return l

def world(c, strength):
    w = bpy.data.worlds.new("w"); scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = rgb(c)
    w.node_tree.nodes["Background"].inputs[1].default_value = strength

def sky_world(top, horizon, strength=1.0):
    w = bpy.data.worlds.new("sky"); scene.world = w; w.use_nodes = True; nt = w.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.49; cr.color_ramp.elements[0].color = rgb(horizon)
    cr.color_ramp.elements[1].position = 0.6; cr.color_ramp.elements[1].color = rgb(top)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], cr.inputs["Fac"])
    bg = nt.nodes["Background"]; nt.links.new(cr.outputs["Color"], bg.inputs[0]); bg.inputs[1].default_value = strength

def meadow():
    sky_world((95, 160, 235), (195, 225, 250), 1.0)
    grass = noisy("grass", (110, 180, 90), (80, 150, 70), 3)
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); _fin(bpy.context.object, grass, None)
    for x, y, r, c in [(-6, 14, 7, (95, 165, 85)), (5, 18, 9, (85, 150, 80)), (14, 12, 6, (105, 175, 90)), (-14, 16, 8, (90, 160, 85))]:
        sphere((x, y, -r * 0.55), r, noisy(f"hill{x}", c, tuple(int(v * 0.85) for v in c), 1.5), None, sc=(1.6, 1, 1))
    sphere((7, 30, 6), 2.2, mat("sunD", (255, 230, 150), 0.5, emit=8), None)
    trunk = mat("trunk", (120, 80, 50), 0.8); leaf = noisy("foliage", (70, 150, 70), (50, 125, 55), 4, 0.7)
    for x, y in [(-3.2, 3.5), (3.6, 4.5), (-5.5, 7)]:
        cyl((x, y, 0.7), 0.13, 1.4, trunk, None)
        for dx, dz, r in [(0, 1.7, 0.75), (-0.45, 1.35, 0.5), (0.45, 1.4, 0.55), (0.1, 2.15, 0.5)]: sphere((x + dx, y, dz), r, leaf, None)
    flower_cols = [(250, 90, 110), (255, 210, 70), (250, 250, 250), (180, 120, 230)]
    for i in range(26):
        x = -2.6 + (i * 0.73) % 5.4; y = -0.9 + (i * 0.47) % 2.6
        if abs(x) < 1.0 and y < 0.8: continue
        cyl((x, y, 0.06), 0.008, 0.12, mat("stem", (70, 140, 60)), None)
        sphere((x, y, 0.13), 0.035, mat(f"fl{i % 4}", flower_cols[i % 4], 0.5), None)
    clouds = []
    for cx, cz, cy in [(-3.5, 3.6, 8), (2.5, 4.2, 10), (6, 3.2, 9)]:
        e = empty("cloud", (cx, cy, cz))
        for dx, dz, r in [(0, 0, 0.55), (0.6, 0.1, 0.75), (1.3, 0, 0.5), (0.6, 0.55, 0.45)]:
            sphere((dx, 0, dz), r, mat("cloud", (255, 255, 255), 0.9, emit=0.6), e)
        clouds.append(e)
    light("SUN", (0, 0, 10), 3.2, (1.0, 0.93, 0.8), size=3, rot=(0.9, 0.2, -0.5), name="sunL")
    light("AREA", (2.5, -4, 3), 300, (0.85, 0.9, 1.0), size=4, rot=(0.9, 0, 0.5), name="fill")
    return clouds
