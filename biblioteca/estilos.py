"""Estilo "plano": sombreado de dibujo animado (2 tonos) y contorno negro por casco invertido. Solo Eevee."""
import bpy

GROSOR_CONTORNO = 0.006


def _color_base(nt, bsdf):
    """Devuelve (socket_o_None, valor_por_defecto) del color base del Principled BSDF."""
    entrada = bsdf.inputs["Base Color"]
    if entrada.is_linked:
        return entrada.links[0].from_socket, None
    return None, tuple(entrada.default_value)


def toon(m: bpy.types.Material) -> None:
    if m is None or not m.use_nodes or m.get("toon"):
        return
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    salida = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if bsdf is None or salida is None:
        return
    if bsdf.inputs["Emission Strength"].default_value > 0.5:   # luces/ojos brillantes quedan igual
        return
    socket, valor = _color_base(nt, bsdf)
    difuso = nt.nodes.new("ShaderNodeBsdfDiffuse")
    a_rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.interpolation = "CONSTANT"
    rampa.color_ramp.elements[0].position = 0.0
    rampa.color_ramp.elements[0].color = (0.45, 0.45, 0.5, 1)
    rampa.color_ramp.elements[1].position = 0.18
    rampa.color_ramp.elements[1].color = (1, 1, 1, 1)
    mezcla = nt.nodes.new("ShaderNodeMix")
    mezcla.data_type = "RGBA"
    mezcla.blend_type = "MULTIPLY"
    mezcla.inputs["Factor"].default_value = 1.0
    emision = nt.nodes.new("ShaderNodeEmission")
    if socket is not None:
        nt.links.new(socket, difuso.inputs["Color"])
        nt.links.new(socket, mezcla.inputs["A"])
    else:
        difuso.inputs["Color"].default_value = valor
        mezcla.inputs["A"].default_value = valor
    nt.links.new(difuso.outputs["BSDF"], a_rgb.inputs["Shader"])
    nt.links.new(a_rgb.outputs["Color"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], mezcla.inputs["B"])
    nt.links.new(mezcla.outputs["Result"], emision.inputs["Color"])
    nt.links.new(emision.outputs["Emission"], salida.inputs["Surface"])
    m["toon"] = True


def material_contorno() -> bpy.types.Material:
    m = bpy.data.materials.get("contorno")
    if m:
        return m
    m = bpy.data.materials.new("contorno")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    emision = nt.nodes.new("ShaderNodeEmission")
    emision.inputs["Color"].default_value = (0.02, 0.015, 0.02, 1)
    nt.links.new(emision.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
    m.use_backface_culling = True
    return m


def contorno(o: bpy.types.Object, grosor: float = GROSOR_CONTORNO) -> None:
    if o.type != "MESH" or o.get("contorno"):
        return
    m = material_contorno()
    o.data.materials.append(m)
    mod = o.modifiers.new("contorno", "SOLIDIFY")
    mod.thickness = -grosor
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = len(o.data.materials) - 1
    o["contorno"] = True


def aplicar_plano(objetos) -> None:
    for o in objetos:
        if o.type not in {"MESH", "CURVE"}:
            continue
        for slot in o.material_slots:
            toon(slot.material)
        if o.type == "MESH" and max(o.dimensions) > 0.03:   # sin contorno en piezas diminutas (brillos de ojos)
            contorno(o)
