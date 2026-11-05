"""Escultura, esqueleto, ojos, tela y pelo procedurales. Extraído de la referencia de Claude (chars2.py)."""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from biblioteca.base import *  # noqa: F401,F403
from biblioteca.base import col, cyl, empty, lin, mat, rgb, sphere, tube

# "Feature-animation" style characters: fused sculpted bodies, rigged, with SSS skin,
# detailed eyes with lids, fabric clothes and particle fur. exec() after lib3d.py.

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
