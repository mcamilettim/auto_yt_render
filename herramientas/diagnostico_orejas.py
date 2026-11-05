import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bpy.ops.wm.read_factory_settings(use_empty=True)
from mathutils import Vector  # noqa: E402

from biblioteca.persona import persona  # noqa: E402

R = persona(nombre="t", edad="adulto", complexion="media", ropa="comerciante_1890", pelo="corto_castano", barba="bigote",
            piel="#c68642")
bpy.context.view_layer.update()
z_oreja = R["altura"] - R["R_cab"] * 1.05
print("ALTURA", R["altura"], "R_cab", R["R_cab"], "z_oreja", z_oreja)
for o in bpy.data.objects:
    if o.type not in {"MESH", "CURVE"}:
        continue
    esquinas = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [c.x for c in esquinas]
    zs = [c.z for c in esquinas]
    ys = [c.y for c in esquinas]
    if max(xs) > R["R_cab"] * 0.8 and min(zs) < z_oreja + 0.1 and max(zs) > z_oreja - 0.1:
        mats = [s.material.name if s.material else None for s in o.material_slots]
        print("OBJ", o.name, o.type, "x", round(min(xs), 3), round(max(xs), 3), "y", round(min(ys), 3), round(max(ys), 3),
              "z", round(min(zs), 3), round(max(zs), 3), mats, "parent", o.parent.name if o.parent else None)
print("LAMINA OK")
