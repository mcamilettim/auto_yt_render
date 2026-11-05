import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bpy.ops.wm.read_factory_settings(use_empty=True)
from biblioteca.persona import persona  # noqa: E402

R = persona(nombre="t", estilo="caricatura")
arm = R["arm"]
vl = bpy.context.view_layer


def pos(o):
    vl.update()
    return tuple(round(v, 3) for v in o.matrix_world.translation)


def pie():
    vl.update()
    pb = arm.pose.bones["shin.L"]
    return tuple(round(v, 3) for v in (arm.matrix_world @ pb.tail))


print("BASE mano.L", pos(R["mano.L"]), "pie.L", pie())
for hueso, eje in [("upper_arm.L", 0), ("upper_arm.L", 1), ("upper_arm.L", 2), ("thigh.L", 0), ("thigh.L", 2),
                   ("forearm.L", 0), ("shin.L", 0)]:
    for v in (0.8, -0.8):
        rot = [0, 0, 0]
        rot[eje] = v
        arm.pose.bones[hueso].rotation_euler = rot
        print("ROT", hueso, "xyz"[eje], v, "mano.L", pos(R["mano.L"]), "pie.L", pie())
        arm.pose.bones[hueso].rotation_euler = (0, 0, 0)
for eje in range(3):
    rot = [0, 0, 0]
    rot[eje] = 0.5
    arm.pose.bones["head"].rotation_euler = rot
    vl.update()
    print("HEAD", "xyz"[eje], tuple(round(v, 3) for v in (arm.matrix_world @ arm.pose.bones["head"].tail)))
    arm.pose.bones["head"].rotation_euler = (0, 0, 0)

for estilo in ("realista",):
    R2 = persona(nombre="r", estilo=estilo)
    print("ALTURA", estilo, round(R2["altura"], 3))
print("ALTURA caricatura", round(R["altura"], 3))
print("LAMINA OK diagnostico")
