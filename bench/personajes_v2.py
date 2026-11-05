# personajes_v2_todo_en_uno.py — lámina de personajes v2 (personajes_v2.jpg) en un solo archivo.
# Ejecutar:  blender -b -P personajes_v2_todo_en_uno.py
# Opcional:  ORIENT=vertical FAST=1 blender -b -P personajes_v2_todo_en_uno.py
import bpy, math, os, time
bpy.ops.wm.read_factory_settings(use_empty=True)
D = os.path.dirname(os.path.abspath(__file__)) + os.sep

# ======== lib3d.py (materiales, primitivas, luces, prado) ========
import bpy, math
from mathutils import Vector
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
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
        b.inputs["Alpha"].default_value = alpha; m.blend_method = "BLEND"; m.shadow_method = "NONE"
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

# ---------------- characters ----------------
WOODL = wood("woodL", (232, 184, 128), (205, 150, 96), scale=6, direction="Z", distort=3)
WOODD = wood("woodD", (168, 110, 66), (130, 82, 46), scale=6, direction="Z", distort=3)
JOINT = mat("joint", (92, 58, 34), 0.6)
SKIN = mat("skin", (246, 196, 160), 0.55)
BLACK = mat("black", (20, 18, 22), 0.15, spec=0.9)
WHITE = mat("eyewhite", (250, 250, 250), 0.25)
SHINE = mat("shine", (255, 255, 255), 0.2, emit=3)
PINK = mat("cheek", (240, 130, 130), 0.7)
LIPS = mat("lips", (150, 45, 45), 0.4)

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


# ======== chars2.py (cerditos y lobo v2: esculpidos, con huesos, piel, ojos, tela, pelaje) ========
# "Feature-animation" style characters: fused sculpted bodies, rigged, with SSS skin,
# detailed eyes with lids, fabric clothes and particle fur. exec() after lib3d.py.
import bmesh, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

def _act(o):
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active = o

def _apply(o, mod):
    _act(o); bpy.ops.object.modifier_apply(modifier=mod.name)

def capsule(p, q, r1, r2=None):
    r2 = r1 if r2 is None else r2
    p, q = Vector(p), Vector(q); d = q - p
    rot = d.to_track_quat("Z", "Y").to_euler()
    return [cyl((p + q) / 2, r1, d.length, None, rot=rot, r2=r2 if r2 != r1 else None, verts=24),
            sphere(p, r1, None, seg=24), sphere(q, r2, None, seg=24)]

def fuse(parts, name, voxel=0.009, smooth=5):
    _act(parts[0])
    for o in parts: o.select_set(True)
    bpy.ops.object.join(); o = bpy.context.object; o.name = name
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR") if False else None
    o.data.transform(o.matrix_world); o.matrix_world = Matrix()
    rm = o.modifiers.new("rm", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = voxel; _apply(o, rm)
    sm = o.modifiers.new("sm", "SMOOTH"); sm.factor = 0.6; sm.iterations = smooth; _apply(o, sm)
    for p in o.data.polygons: p.use_smooth = True
    return o

def paint(o, fn):
    attr = o.data.color_attributes.new("col", "FLOAT_COLOR", "POINT")
    for i, v in enumerate(o.data.vertices):
        c = fn(v.co); attr.data[i].color = (lin(c[0]), lin(c[1]), lin(c[2]), 1)

def vgroup(o, name, fn):
    g = o.vertex_groups.new(name=name)
    for v in o.data.vertices:
        w = fn(v.co)
        if w > 0: g.add([v.index], w, "REPLACE")
    return g

def sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

def mix(c1, c2, t): return tuple(a + (b - a) * t for a, b in zip(c1, c2))

# ---------- materials ----------
def skin_mat(name, sss_col, sss=0.35, rough=0.42, pores=0.04):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "col"
    nt.links.new(at.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Radius"].default_value = sss_col
    b.inputs["Subsurface Scale"].default_value = 0.03
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.4
    b.inputs["Coat Weight"].default_value = 0.08
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 180; nz.inputs["Detail"].default_value = 2
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = pores
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    try: m.use_sss_translucency = True
    except Exception: pass
    return m

def fabric(name, c, rough=0.85, scale=160, sheen=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w1 = nt.nodes.new("ShaderNodeTexWave"); w1.bands_direction = "X"; w1.inputs["Scale"].default_value = scale
    w2 = nt.nodes.new("ShaderNodeTexWave"); w2.bands_direction = "Z"; w2.inputs["Scale"].default_value = scale
    mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY"
    for w in (w1, w2): nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    nt.links.new(w1.outputs["Fac"], mu.inputs[0]); nt.links.new(w2.outputs["Fac"], mu.inputs[1])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = rgb(tuple(int(v * 0.82) for v in c)); cr.color_ramp.elements[1].color = rgb(c)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.25
    nt.links.new(mu.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Specular IOR Level"].default_value = 0.3
    return m

def hair_mat(name, c1, c2):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    hi = nt.nodes.new("ShaderNodeHairInfo"); cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = rgb(c1); cr.color_ramp.elements[1].color = rgb(c2)
    nt.links.new(hi.outputs["Random"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55; b.inputs["Specular IOR Level"].default_value = 0.3
    return m

def iris_mat(name, inner, outer):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    cb = nt.nodes.new("ShaderNodeCombineXYZ"); ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
    nt.links.new(tc.outputs["Object"], sp.inputs[0]); nt.links.new(sp.outputs["X"], cb.inputs["X"]); nt.links.new(sp.outputs["Z"], cb.inputs["Z"])
    nt.links.new(cb.outputs[0], ln.inputs[0])
    st = nt.nodes.new("ShaderNodeTexNoise"); st.inputs["Scale"].default_value = 40
    nt.links.new(tc.outputs["Object"], st.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); E = cr.color_ramp.elements
    E[0].position = 0.0; E[0].color = (0.005, 0.005, 0.006, 1)
    E[1].position = 0.17; E[1].color = (0.005, 0.005, 0.006, 1)
    for pos, c in [(0.2, inner), (0.38, outer), (0.44, tuple(int(v * 0.35) for v in outer))]:
        e = E.new(pos); e.color = rgb(c)
    nt.links.new(ln.outputs["Value"], cr.inputs["Fac"])
    mx = nt.nodes.new("ShaderNodeMixRGB"); mx.blend_type = "OVERLAY"; mx.inputs["Fac"].default_value = 0.35
    nt.links.new(cr.outputs["Color"], mx.inputs["Color1"]); nt.links.new(st.outputs["Color"], mx.inputs["Color2"])
    nt.links.new(mx.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.3
    return m

SCLERA = mat("sclera", (246, 242, 238), 0.25)
CORNEA = mat("cornea", (255, 255, 255), 0.01, alpha=0.06, spec=1.0)
CATCH = mat("catch", (255, 255, 255), 0.2, emit=6)

# ---------- rig ----------
def make_rig(name, bones):
    ad = bpy.data.armatures.new(name); arm = bpy.data.objects.new(name, ad); col.objects.link(arm)
    _act(arm); bpy.ops.object.mode_set(mode="EDIT")
    for bn, h, t, par in bones:
        eb = ad.edit_bones.new(bn); eb.head = h; eb.tail = t
        if par: eb.parent = ad.edit_bones[par]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones: pb.rotation_mode = "XYZ"
    return arm

def skin_to(mesh, arm):
    _act(mesh); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

def bone_parent(o, arm, bn):
    b = arm.data.bones[bn]
    P = b.matrix_local @ Matrix.Translation((0, b.length, 0))
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    o.parent = arm; o.parent_type = "BONE"; o.parent_bone = bn
    o.matrix_parent_inverse = P.inverted(); o.matrix_basis = mw

def deform_copy(body, arm, name, keep, thick, m):
    o = body.copy(); o.data = body.data.copy(); o.name = name; col.objects.link(o)
    for md in list(o.modifiers): o.modifiers.remove(md)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep(v.co)], context="VERTS"); bm.to_mesh(o.data); bm.free()
    o.data.materials.clear(); o.data.materials.append(m)
    am = o.modifiers.new("arm", "ARMATURE"); am.object = arm
    so = o.modifiers.new("sol", "SOLIDIFY"); so.thickness = thick; so.offset = 1; so.use_rim = True
    return o

class Surf:
    def __init__(s, o):
        dg = bpy.context.evaluated_depsgraph_get(); s.t = BVHTree.FromObject(o, dg)
    def front(s, x, z, y0=-3.0, dirv=(0, 1, 0)):
        hit = s.t.ray_cast(Vector((x, y0, z)), Vector(dirv))
        return hit[0], hit[1]
    def near(s, p):
        r = s.t.find_nearest(Vector(p)); return r[0], r[1]

def dome(r, m, thick=0.004):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=r)
    o = bpy.context.object; bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-5], context="VERTS"); bm.to_mesh(o.data); bm.free()
    for p in o.data.polygons: p.use_smooth = True
    so = o.modifiers.new("s", "SOLIDIFY"); so.thickness = thick; so.offset = 1
    o.data.materials.append(m); return o

def make_eye(S, x, z, r, skin, iris, upper=-0.55, lower=0.6, tilt=0.0, s=1, sink=0.5, fwd=0.55, lidcol=None):
    p, n = S.front(x, z)
    d = (n * (1 - fwd) + Vector((0.12 * s, -1, 0)) * fwd).normalized()
    ctr = p - n * r * sink
    E = empty("eyeR", ctr, rot=d.to_track_quat("-Y", "Z").to_euler())
    sphere((0, 0, 0), r, SCLERA, E, seg=40)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.0)
    cap = bpy.context.object; bm = bmesh.new(); bm.from_mesh(cap.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > -0.86], context="VERTS"); bm.to_mesh(cap.data); bm.free()
    for pp in cap.data.polygons: pp.use_smooth = True
    cap.scale = (r * 1.004,) * 3; cap.data.materials.append(iris); cap.parent = E
    sphere((0, -0.03 * r, 0), r * 1.04, CORNEA, E, seg=40)
    sphere((0.28 * r * s, -0.97 * r, 0.32 * r), r * 0.1, CATCH, E, seg=16)
    lids = []
    for kind, a in (("up", upper), ("lo", lower)):
        L = empty("lid", (0, 0, 0), E, rot=(a if kind == "up" else math.pi + a, 0, tilt * s if kind == "up" else 0))
        dm = dome(r * 1.07, skin, thick=r * 0.08); dm.parent = L
        if lidcol: paint(dm, lambda c: lidcol)
        lids.append(L)
    return E, lids

def surface_tube(S, pts, r, m, off=0.004):
    out = []
    for p in pts:
        q, n = S.near(p); out.append(tuple(q + n * off))
    return tube(out, r, m)

def fur(o, m, count, length, group=None, rough=0.004, child=8, diam=0.0035):
    if os.environ.get("FAST", "0") == "1": count, child = count // 2, min(child, 4)
    _act(o); o.data.materials.append(m)
    md = o.modifiers.new("fur" + m.name, "PARTICLE_SYSTEM"); psys = o.particle_systems[-1]; ps = psys.settings
    ps.type = "HAIR"; ps.count = count; ps.hair_length = length; ps.child_type = "INTERPOLATED"
    ps.rendered_child_count = child; ps.child_percent = child
    ps.root_radius = 1; ps.tip_radius = 0.1; ps.radius_scale = diam; ps.roughness_2 = rough; ps.roughness_endpoint = 0.05
    ps.length_random = 0.4
    ps.clump_factor = 0.2
    ps.material_slot = m.name
    if group: psys.vertex_group_density = group
    return psys

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

# ======== sheet2.py (pasto, poses, luces, cámara y render) ========
t0 = time.time()
ORIENT = os.environ.get("ORIENT", "horizontal")   # horizontal | vertical
FAST = os.environ.get("FAST", "0") == "1"           # 1 = configuración rápida (<1 min)

meadow()
# grass patch around the characters
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.6, 0.002)); gp = bpy.context.object; gp.scale = (9, 6, 1)
bpy.ops.object.transform_apply(scale=True)
gm = bpy.data.materials.new("grassH"); gm.use_nodes = True; nt = gm.node_tree; b = nt.nodes["Principled BSDF"]
hi = nt.nodes.new("ShaderNodeHairInfo"); cr = nt.nodes.new("ShaderNodeValToRGB")
cr.color_ramp.elements[0].color = rgb((40, 95, 40)); cr.color_ramp.elements[1].color = rgb((140, 200, 95))
nt.links.new(hi.outputs["Intercept"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = 0.6
gp.data.materials.append(mat("grassbase", (80, 140, 60), 0.9))
ps = fur(gp, gm, 3000 if FAST else 7000, 0.09, child=6 if FAST else 10, rough=0.01, diam=0.006); ps.settings.length_random = 0.6

print("T meadow", time.time()-t0, flush=True)
p1 = pig2((232, 196, 90), "straw", iris_mat("irisP1", (175, 120, 60), (110, 70, 35)))
place(p1, (-1.35, 0, 0), math.radians(12))
print("T p1", time.time()-t0, flush=True)
p2 = pig2((80, 140, 225), "cap", iris_mat("irisP2", (120, 185, 240), (45, 95, 175)))
place(p2, (-0.45, 0, 0), math.radians(4))
p3 = pig2((195, 75, 55), "helmet", iris_mat("irisP3", (140, 190, 90), (60, 120, 50)))
place(p3, (0.45, 0, 0), math.radians(-4))
print("T p3", time.time()-t0, flush=True)
w = wolf2()
place(w, (1.45, 0.1, 0), math.radians(-36))
pose(p1, arm_R=(0, 0, 0), arm_L=(0, 0, 1.2), head=(0, 0, 0.12))
pose(p2, head=(0.08, 0, 0))
pose(p3, head=(0, 0, -0.08), arm_R=(0, 0, -0.15))
pose(w, head=(0.05, 0, -0.2), arm_L=(0.2, 0, 0.15))
print("BUILD", time.time() - t0, flush=True)

# lights: warm key, cool fill, strong rim
for o in list(bpy.data.objects):
    if o.type == "LIGHT": bpy.data.objects.remove(o)
def L(kind, loc, rot, energy, color, size):
    l = light(kind, loc, energy, color, size=size, rot=rot); l.use_contact_shadow = True; return l
L("SUN", (0, 0, 10), (math.radians(50), math.radians(10), math.radians(-35)), 4.0, (1.0, 0.9, 0.78), 2.5).angle = math.radians(4)
L("AREA", (3.0, -4.0, 2.5), (math.radians(65), 0, math.radians(40)), 350, (0.75, 0.85, 1.0), 5)
L("AREA", (0.0, 3.5, 2.6), (math.radians(-60), 0, 0), 900, (1.0, 0.92, 0.85), 6)

cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); col.objects.link(cam); scene.camera = cam
cam.location = (0.05, -5.0, 1.0); cam.rotation_euler = (math.radians(86.5), 0, 0); cd.lens = 42
if ORIENT == "vertical":                       # 9:16: el sensor se ajusta al alto, la cámara se aleja y sube un poco
    cd.sensor_fit = "VERTICAL"; cd.lens = 30; cam.location = (0.05, -6.2, 1.15); cam.rotation_euler = (math.radians(85), 0, 0)
cd.dof.use_dof = True; cd.dof.focus_distance = 5.0; cd.dof.aperture_fstop = 4.0
e = scene.eevee
e.taa_render_samples = 8 if FAST else 24; e.use_gtao = True; e.gtao_distance = 0.3; e.gtao_factor = 1.0; e.use_soft_shadows = True
e.shadow_cube_size = "1024" if FAST else "2048"; e.shadow_cascade_size = "2048" if FAST else "4096"; e.use_bloom = True; e.bloom_intensity = 0.03
e.use_ssr = not FAST; e.sss_samples = 5 if FAST else 9
scene.render.engine = "BLENDER_EEVEE"; scene.render.hair_type = "STRIP"
scene.render.resolution_x, scene.render.resolution_y = (1080, 1920) if ORIENT == "vertical" else (1920, 1080)
if FAST: scene.render.resolution_percentage = 50   # se renderiza a la mitad y se escala con ffmpeg (lanczos)
try:
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Punchy"
except Exception:
    scene.view_settings.view_transform = "Filmic"
scene.render.filepath = D + f"personajes2_{ORIENT}{'_fast' if FAST else ''}.png"
bpy.ops.render.render(write_still=True)
print("TOTAL", time.time() - t0)
