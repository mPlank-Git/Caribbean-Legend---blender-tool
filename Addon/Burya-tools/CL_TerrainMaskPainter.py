bl_info = {
"license": "GPL-3.0-or-later",
    "name": "CL_Terrain Mask Painter",
    "author": "mPlank",
    "version": (1, 0, 4),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Terrain Mask",
    "description": "Terrain texture blending using Base + RGB mask layers / Смешивание текстур террейна через базовый слой и RGB-маску",
    "category": "Material",
}
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This add-on is licensed under the GNU General Public License v3.0 or later.
# Этот аддон распространяется по лицензии GNU General Public License v3.0 или более поздней версии.
import bpy
from bpy.props import (
    PointerProperty,
    IntProperty,
    EnumProperty,
    StringProperty,
    FloatProperty,
    BoolProperty,
)
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras.io_utils import ExportHelper


def get_active_object(context):
    obj = context.active_object
    if obj and obj.type == "MESH":
        return obj
    return None


def ensure_material(obj):
    if obj.active_material is None:
        mat = bpy.data.materials.new("Terrain_RGB_Mask_Material")
        mat.use_nodes = True
        obj.data.materials.append(mat)
        obj.active_material = mat
    else:
        mat = obj.active_material
        mat.use_nodes = True
    return mat


def set_non_color(img):
    if img:
        try:
            img.colorspace_settings.name = "Non-Color"
        except Exception:
            pass


def link(links, out_socket, in_socket):
    for l in list(in_socket.links):
        links.remove(l)
    links.new(out_socket, in_socket)


class TerrainLayer(PropertyGroup):
    albedo: PointerProperty(
        name="Albedo",
        description="Albedo/base color texture for this layer / Цветовая текстура слоя",
        type=bpy.types.Image,
    )
    normal: PointerProperty(
        name="Normal",
        description="Normal map texture for this layer / Карта нормалей слоя",
        type=bpy.types.Image,
    )
    rma: PointerProperty(
        name="RMA",
        description="Packed Roughness-Metallic-AO texture / Упакованная текстура Roughness-Metallic-AO",
        type=bpy.types.Image,
    )


class TerrainProps(PropertyGroup):
    base: PointerProperty(type=TerrainLayer)
    red: PointerProperty(type=TerrainLayer)
    green: PointerProperty(type=TerrainLayer)
    blue: PointerProperty(type=TerrainLayer)

    mask: PointerProperty(
        name="RGB Mask",
        description="RGB mask texture. Black is Base; R/G/B are layered overlays / RGB-маска. Чёрный — база; R/G/B — накладываемые слои",
        type=bpy.types.Image,
    )

    mask_name: StringProperty(
        name="Mask Name",
        description="Name for the created RGB mask texture / Имя создаваемой RGB-маски",
        default="terrain_rgb_mask",
    )

    mask_resolution: IntProperty(
        name="Mask Resolution",
        description="Resolution of the created mask texture / Разрешение создаваемой маски",
        default=2048,
        min=128,
        max=8192,
    )

    tile_scale: FloatProperty(
        name="Tile Scale",
        description="Tiling scale for all terrain textures using UV1 / Масштаб тайлинга текстур по UV1",
        default=4.0,
        min=0.001,
        max=1000.0,
    )

    brush_strength: FloatProperty(
        name="Brush Strength",
        description="Brush strength for Texture Paint mode / Сила кисти для Texture Paint",
        default=1.0,
        min=0.0,
        max=1.0,
    )

    use_add_paint: BoolProperty(
        name="Use ADD Paint",
        description="Use ADD blend mode for R/G/B painting. Base always uses MIX / Использовать ADD-режим кисти для R/G/B. Base всегда использует MIX",
        default=False,
    )

    active_paint: EnumProperty(
        name="Paint",
        description="Currently selected paint layer / Текущий слой покраски",
        items=[
            ("BASE", "Base / Erase", "Paint black to return to Base layer / Чёрный возвращает базовый слой"),
            ("RED", "Red Layer", "Paint Red layer / Красит красный слой"),
            ("GREEN", "Green Layer", "Paint Green layer / Красит зелёный слой"),
            ("BLUE", "Blue Layer", "Paint Blue layer / Красит синий слой"),
        ],
        default="RED",
    )

    preview_mode: EnumProperty(
        name="Preview",
        description="Viewport preview mode / Режим предпросмотра",
        items=[
            ("MATERIAL", "Material", "Show final material / Показать итоговый материал"),
            ("MASK", "Mask RGB", "Show raw RGB mask / Показать RGB-маску"),
            ("R", "Red Channel", "Show only red channel / Показать только красный канал"),
            ("G", "Green Channel", "Show only green channel / Показать только зелёный канал"),
            ("B", "Blue Channel", "Show only blue channel / Показать только синий канал"),
        ],
        default="MATERIAL",
    )


def create_mask_image(props):
    res = props.mask_resolution
    name = props.mask_name.strip() or "terrain_rgb_mask"

    img = bpy.data.images.new(
        name=name,
        width=res,
        height=res,
        alpha=True,
        float_buffer=False,
    )

    pixels = [0.0] * (res * res * 4)
    for i in range(0, len(pixels), 4):
        pixels[i] = 0.0
        pixels[i + 1] = 0.0
        pixels[i + 2] = 0.0
        pixels[i + 3] = 1.0

    img.pixels[:] = pixels
    img.update()
    set_non_color(img)
    props.mask = img
    return img


def fill_mask(img, mode):
    if mode == "BASE":
        color = (0.0, 0.0, 0.0)
    elif mode == "RED":
        color = (1.0, 0.0, 0.0)
    elif mode == "GREEN":
        color = (0.0, 1.0, 0.0)
    elif mode == "BLUE":
        color = (0.0, 0.0, 1.0)
    else:
        color = (0.0, 0.0, 0.0)

    pixels = list(img.pixels)
    for i in range(0, len(pixels), 4):
        pixels[i] = color[0]
        pixels[i + 1] = color[1]
        pixels[i + 2] = color[2]
        pixels[i + 3] = 1.0

    img.pixels[:] = pixels
    img.update()


def blur_rgb_mask(img):
    width, height = img.size
    src = list(img.pixels)
    dst = src[:]

    for y in range(height):
        for x in range(width):
            acc_r = 0.0
            acc_g = 0.0
            acc_b = 0.0
            count = 0

            for oy in (-1, 0, 1):
                for ox in (-1, 0, 1):
                    sx = min(width - 1, max(0, x + ox))
                    sy = min(height - 1, max(0, y + oy))
                    idx = (sy * width + sx) * 4

                    acc_r += src[idx]
                    acc_g += src[idx + 1]
                    acc_b += src[idx + 2]
                    count += 1

            idx = (y * width + x) * 4
            dst[idx] = acc_r / count
            dst[idx + 1] = acc_g / count
            dst[idx + 2] = acc_b / count
            dst[idx + 3] = 1.0

    img.pixels[:] = dst
    img.update()


def new_math(nodes, name, operation, loc):
    n = nodes.new("ShaderNodeMath")
    n.name = name
    n.operation = operation
    n.location = loc
    return n


def subtract_from_one(nodes, links, value_socket, name, loc):
    n = new_math(nodes, name, "SUBTRACT", loc)
    n.inputs[0].default_value = 1.0
    links.new(value_socket, n.inputs[1])
    return n.outputs["Value"]


def multiply_values(nodes, links, a, b, name, loc):
    n = new_math(nodes, name, "MULTIPLY", loc)
    links.new(a, n.inputs[0])
    links.new(b, n.inputs[1])
    return n.outputs["Value"]


def add_values(nodes, links, a, b, name, loc):
    n = new_math(nodes, name, "ADD", loc)
    links.new(a, n.inputs[0])
    links.new(b, n.inputs[1])
    return n.outputs["Value"]


def divide_values(nodes, links, a, b, name, loc):
    n = new_math(nodes, name, "DIVIDE", loc)
    links.new(a, n.inputs[0])
    links.new(b, n.inputs[1])
    return n.outputs["Value"]


def value_to_color(nodes, links, value_socket, name, loc):
    n = nodes.new("ShaderNodeCombineColor")
    n.name = name
    n.mode = "RGB"
    n.location = loc
    links.new(value_socket, n.inputs["Red"])
    links.new(value_socket, n.inputs["Green"])
    links.new(value_socket, n.inputs["Blue"])
    return n.outputs["Color"]


def weighted_color(nodes, links, color_socket, weight_socket, name, loc):
    w_color = value_to_color(
        nodes,
        links,
        weight_socket,
        f"{name}_WeightColor",
        (loc[0] - 220, loc[1] - 80),
    )

    n = nodes.new("ShaderNodeMixRGB")
    n.name = name
    n.blend_type = "MULTIPLY"
    n.inputs["Fac"].default_value = 1.0
    n.location = loc

    links.new(color_socket, n.inputs["Color1"])
    links.new(w_color, n.inputs["Color2"])
    return n.outputs["Color"]


def add_color(nodes, links, a, b, name, loc):
    n = nodes.new("ShaderNodeMixRGB")
    n.name = name
    n.blend_type = "ADD"
    n.inputs["Fac"].default_value = 1.0
    n.location = loc

    links.new(a, n.inputs["Color1"])
    links.new(b, n.inputs["Color2"])
    return n.outputs["Color"]


def build_layered_weights(nodes, links, r, g, b):
    overlay_rg = add_values(nodes, links, r, g, "TRGB_Overlay_RG", (-1450, -50))
    overlay_rgb = add_values(nodes, links, overlay_rg, b, "TRGB_Overlay_RGB", (-1250, -50))

    overlay = new_math(nodes, "TRGB_Overlay_Clamp", "MINIMUM", (-1050, -50))
    links.new(overlay_rgb, overlay.inputs[0])
    overlay.inputs[1].default_value = 1.0

    inv_g = subtract_from_one(nodes, links, g, "TRGB_OneMinus_G", (-1450, -230))
    inv_b = subtract_from_one(nodes, links, b, "TRGB_OneMinus_B", (-1450, -400))

    raw_r_a = multiply_values(nodes, links, r, inv_g, "TRGB_RawR_A", (-1250, -230))
    raw_r = multiply_values(nodes, links, raw_r_a, inv_b, "TRGB_RawR", (-1050, -230))

    raw_g = multiply_values(nodes, links, g, inv_b, "TRGB_RawG", (-1050, -400))
    raw_b = b

    raw_rg = add_values(nodes, links, raw_r, raw_g, "TRGB_Raw_RG", (-850, -300))
    raw_rgb = add_values(nodes, links, raw_rg, raw_b, "TRGB_Raw_RGB", (-650, -300))

    raw_sum = new_math(nodes, "TRGB_RawSum_Safe", "MAXIMUM", (-450, -300))
    links.new(raw_rgb, raw_sum.inputs[0])
    raw_sum.inputs[1].default_value = 0.000001

    w_base = subtract_from_one(nodes, links, overlay.outputs["Value"], "TRGB_W_Base", (-850, 80))

    r_div = divide_values(nodes, links, raw_r, raw_sum.outputs["Value"], "TRGB_R_Div", (-250, -180))
    g_div = divide_values(nodes, links, raw_g, raw_sum.outputs["Value"], "TRGB_G_Div", (-250, -350))
    b_div = divide_values(nodes, links, raw_b, raw_sum.outputs["Value"], "TRGB_B_Div", (-250, -520))

    w_r = multiply_values(nodes, links, r_div, overlay.outputs["Value"], "TRGB_W_R", (0, -180))
    w_g = multiply_values(nodes, links, g_div, overlay.outputs["Value"], "TRGB_W_G", (0, -350))
    w_b = multiply_values(nodes, links, b_div, overlay.outputs["Value"], "TRGB_W_B", (0, -520))

    return w_base, w_r, w_g, w_b


def build_weighted_sum(nodes, links, sockets, weights, name, loc):
    c0 = weighted_color(nodes, links, sockets[0], weights[0], f"{name}_Base", (loc[0], loc[1]))
    c1 = weighted_color(nodes, links, sockets[1], weights[1], f"{name}_R", (loc[0], loc[1] - 220))
    c2 = weighted_color(nodes, links, sockets[2], weights[2], f"{name}_G", (loc[0], loc[1] - 440))
    c3 = weighted_color(nodes, links, sockets[3], weights[3], f"{name}_B", (loc[0], loc[1] - 660))

    a0 = add_color(nodes, links, c0, c1, f"{name}_Add_01", (loc[0] + 320, loc[1] - 120))
    a1 = add_color(nodes, links, a0, c2, f"{name}_Add_012", (loc[0] + 640, loc[1] - 260))
    a2 = add_color(nodes, links, a1, c3, f"{name}_Add_0123", (loc[0] + 960, loc[1] - 400))

    return a2


def build_material(context):
    obj = get_active_object(context)
    if obj is None:
        return False, "Select mesh object"

    if len(obj.data.uv_layers) < 2:
        return False, "Need UV1 and UV2"

    props = context.scene.terrain_rgb_mask_props
    mat = ensure_material(obj)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    uv1_name = obj.data.uv_layers[0].name
    uv2_name = obj.data.uv_layers[1].name

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (3800, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "TRGB_BSDF"
    bsdf.location = (3500, 0)

    uv1 = nodes.new("ShaderNodeUVMap")
    uv1.name = "TRGB_UV1"
    uv1.uv_map = uv1_name
    uv1.location = (-2600, 800)

    uv2 = nodes.new("ShaderNodeUVMap")
    uv2.name = "TRGB_UV2"
    uv2.uv_map = uv2_name
    uv2.location = (-2600, 200)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.name = "TRGB_Tile_Mapping"
    mapping.location = (-2350, 800)
    mapping.inputs["Scale"].default_value[0] = props.tile_scale
    mapping.inputs["Scale"].default_value[1] = props.tile_scale
    mapping.inputs["Scale"].default_value[2] = 1.0
    links.new(uv1.outputs["UV"], mapping.inputs["Vector"])

    mask = nodes.new("ShaderNodeTexImage")
    mask.name = "TRGB_Mask"
    mask.label = "RGB Mask"
    mask.image = props.mask
    mask.location = (-2350, 200)
    set_non_color(props.mask)
    links.new(uv2.outputs["UV"], mask.inputs["Vector"])

    sep = nodes.new("ShaderNodeSeparateColor")
    sep.name = "TRGB_Separate_Mask"
    sep.mode = "RGB"
    sep.location = (-2100, 200)
    links.new(mask.outputs["Color"], sep.inputs["Color"])

    weights = build_layered_weights(
        nodes,
        links,
        sep.outputs["Red"],
        sep.outputs["Green"],
        sep.outputs["Blue"],
    )

    layers = [
        ("Base", props.base),
        ("Red", props.red),
        ("Green", props.green),
        ("Blue", props.blue),
    ]

    albedos = []
    normals = []
    rmas = []

    y = 1500
    for name, layer in layers:
        alb = nodes.new("ShaderNodeTexImage")
        alb.name = f"TRGB_{name}_Albedo"
        alb.label = f"{name} Albedo"
        alb.image = layer.albedo
        alb.location = (-1800, y)
        links.new(mapping.outputs["Vector"], alb.inputs["Vector"])
        albedos.append(alb)

        nrm = nodes.new("ShaderNodeTexImage")
        nrm.name = f"TRGB_{name}_Normal"
        nrm.label = f"{name} Normal"
        nrm.image = layer.normal
        nrm.location = (-1800, y - 160)
        links.new(mapping.outputs["Vector"], nrm.inputs["Vector"])
        set_non_color(layer.normal)
        normals.append(nrm)

        rma = nodes.new("ShaderNodeTexImage")
        rma.name = f"TRGB_{name}_RMA"
        rma.label = f"{name} RMA"
        rma.image = layer.rma
        rma.location = (-1800, y - 320)
        links.new(mapping.outputs["Vector"], rma.inputs["Vector"])
        set_non_color(layer.rma)
        rmas.append(rma)

        y -= 520

    albedo_final = build_weighted_sum(
        nodes,
        links,
        [
            albedos[0].outputs["Color"],
            albedos[1].outputs["Color"],
            albedos[2].outputs["Color"],
            albedos[3].outputs["Color"],
        ],
        weights,
        "TRGB_Albedo",
        (500, 1300),
    )

    normal_final_color = build_weighted_sum(
        nodes,
        links,
        [
            normals[0].outputs["Color"],
            normals[1].outputs["Color"],
            normals[2].outputs["Color"],
            normals[3].outputs["Color"],
        ],
        weights,
        "TRGB_Normal",
        (500, 300),
    )

    rma_final_color = build_weighted_sum(
        nodes,
        links,
        [
            rmas[0].outputs["Color"],
            rmas[1].outputs["Color"],
            rmas[2].outputs["Color"],
            rmas[3].outputs["Color"],
        ],
        weights,
        "TRGB_RMA",
        (500, -700),
    )

    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.name = "TRGB_Final_Normal"
    normal_map.location = (2500, 100)
    links.new(normal_final_color, normal_map.inputs["Color"])

    final_rma = nodes.new("ShaderNodeSeparateColor")
    final_rma.name = "TRGB_Final_RMA"
    final_rma.mode = "RGB"
    final_rma.location = (2500, -650)
    links.new(rma_final_color, final_rma.inputs["Color"])

    preview = nodes.new("ShaderNodeMixRGB")
    preview.name = "TRGB_Preview_Switch"
    preview.blend_type = "MIX"
    preview.inputs["Fac"].default_value = 0.0
    preview.location = (3000, 450)

    combine = nodes.new("ShaderNodeCombineColor")
    combine.name = "TRGB_Preview_Combine"
    combine.mode = "RGB"
    combine.location = (2700, 250)

    links.new(albedo_final, preview.inputs["Color1"])
    links.new(mask.outputs["Color"], preview.inputs["Color2"])

    links.new(preview.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(final_rma.outputs["Red"], bsdf.inputs["Roughness"])
    links.new(final_rma.outputs["Green"], bsdf.inputs["Metallic"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    apply_preview(mat, props.preview_mode)

    return True, "Material built"


def apply_preview(mat, mode):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    preview = nodes.get("TRGB_Preview_Switch")
    mask = nodes.get("TRGB_Mask")
    sep = nodes.get("TRGB_Separate_Mask")
    combine = nodes.get("TRGB_Preview_Combine")
    albedo = nodes.get("TRGB_Albedo_Add_0123")

    if not preview:
        return

    if mode == "MATERIAL":
        preview.inputs["Fac"].default_value = 0.0
        if albedo:
            link(links, albedo.outputs["Color"], preview.inputs["Color1"])
        return

    preview.inputs["Fac"].default_value = 1.0

    if mode == "MASK":
        link(links, mask.outputs["Color"], preview.inputs["Color2"])
        return

    if not sep or not combine:
        return

    channel = {
        "R": sep.outputs["Red"],
        "G": sep.outputs["Green"],
        "B": sep.outputs["Blue"],
    }.get(mode)

    if channel:
        link(links, channel, combine.inputs["Red"])
        link(links, channel, combine.inputs["Green"])
        link(links, channel, combine.inputs["Blue"])
        link(links, combine.outputs["Color"], preview.inputs["Color2"])


class TERRAIN_OT_create_mask(Operator):
    bl_idname = "terrain_rgb.create_mask"
    bl_label = "Create RGB Mask"
    bl_description = "Create a new black RGB mask texture. Black means Base layer / Создаёт новую чёрную RGB-маску. Чёрный цвет означает базовый слой"

    def execute(self, context):
        create_mask_image(context.scene.terrain_rgb_mask_props)
        self.report({"INFO"}, "RGB mask created")
        return {"FINISHED"}


class TERRAIN_OT_build_material(Operator):
    bl_idname = "terrain_rgb.build_material"
    bl_label = "Build / Update Material"
    bl_description = "Build material preview using layered overlay formula / Собирает предпросмотр по формуле слоёв без просвечивания базы в overlap-зонах"

    def execute(self, context):
        ok, msg = build_material(context)
        if ok:
            self.report({"INFO"}, msg)
            return {"FINISHED"}
        self.report({"ERROR"}, msg)
        return {"CANCELLED"}


class TERRAIN_OT_assign_mask(Operator):
    bl_idname = "terrain_rgb.assign_mask"
    bl_label = "Assign Mask For Paint"
    bl_description = "Set RGB mask as active Texture Paint target / Назначает RGB-маску активной текстурой для рисования"

    def execute(self, context):
        obj = get_active_object(context)
        props = context.scene.terrain_rgb_mask_props

        if not obj or not obj.active_material:
            self.report({"ERROR"}, "No active material")
            return {"CANCELLED"}

        node = obj.active_material.node_tree.nodes.get("TRGB_Mask")
        if not node:
            self.report({"ERROR"}, "Build material first")
            return {"CANCELLED"}

        node.image = props.mask
        obj.active_material.node_tree.nodes.active = node

        self.report({"INFO"}, "Mask assigned for painting")
        return {"FINISHED"}


class TERRAIN_OT_set_paint(Operator):
    bl_idname = "terrain_rgb.set_paint"
    bl_label = "Set Paint Color"
    bl_description = "Switch brush color and blend mode for painting Base, Red, Green or Blue / Переключает цвет и режим кисти для покраски Base, Red, Green или Blue"

    mode: EnumProperty(
        items=[
            ("BASE", "Base", "Paint black to erase to Base. Always uses MIX / Чёрный возвращает базовый слой. Всегда использует MIX"),
            ("RED", "Red", "Paint Red layer / Красит красный слой"),
            ("GREEN", "Green", "Paint Green layer / Красит зелёный слой"),
            ("BLUE", "Blue", "Paint Blue layer / Красит синий слой"),
        ]
    )

    def execute(self, context):
        props = context.scene.terrain_rgb_mask_props
        props.active_paint = self.mode

        paint = getattr(context.tool_settings, "image_paint", None)
        if paint and paint.brush:
            paint.brush.strength = props.brush_strength

            if self.mode == "BASE":
                paint.brush.color = (0.0, 0.0, 0.0)
                paint.brush.blend = "MIX"

            elif self.mode == "RED":
                paint.brush.color = (1.0, 0.0, 0.0)
                paint.brush.blend = "ADD" if props.use_add_paint else "MIX"

            elif self.mode == "GREEN":
                paint.brush.color = (0.0, 1.0, 0.0)
                paint.brush.blend = "ADD" if props.use_add_paint else "MIX"

            elif self.mode == "BLUE":
                paint.brush.color = (0.0, 0.0, 1.0)
                paint.brush.blend = "ADD" if props.use_add_paint else "MIX"

        self.report({"INFO"}, f"Paint mode: {self.mode}")
        return {"FINISHED"}


class TERRAIN_OT_set_preview(Operator):
    bl_idname = "terrain_rgb.set_preview"
    bl_label = "Set Preview"
    bl_description = "Switch preview mode / Переключает режим предпросмотра"

    mode: EnumProperty(
        items=[
            ("MATERIAL", "Material", "Show final material / Показать итоговый материал"),
            ("MASK", "Mask", "Show RGB mask / Показать RGB-маску"),
            ("R", "R", "Show red channel / Показать красный канал"),
            ("G", "G", "Show green channel / Показать зелёный канал"),
            ("B", "B", "Show blue channel / Показать синий канал"),
        ]
    )

    def execute(self, context):
        props = context.scene.terrain_rgb_mask_props
        props.preview_mode = self.mode

        obj = get_active_object(context)
        if obj and obj.active_material:
            apply_preview(obj.active_material, self.mode)

        return {"FINISHED"}


class TERRAIN_OT_blur_mask(Operator):
    bl_idname = "terrain_rgb.blur_mask"
    bl_label = "Blur RGB Mask"
    bl_description = "Blur RGB mask with simple 3x3 filter / Размывает RGB-маску простым фильтром 3x3"

    def execute(self, context):
        img = context.scene.terrain_rgb_mask_props.mask
        if img is None:
            self.report({"ERROR"}, "No mask image")
            return {"CANCELLED"}

        blur_rgb_mask(img)
        self.report({"INFO"}, "RGB mask blurred")
        return {"FINISHED"}


class TERRAIN_OT_fill_mask(Operator):
    bl_idname = "terrain_rgb.fill_mask"
    bl_label = "Fill Mask"
    bl_description = "Fill whole RGB mask with selected layer / Заливает всю RGB-маску выбранным слоем"

    mode: EnumProperty(
        items=[
            ("BASE", "Base", "Fill with black Base / Залить базой"),
            ("RED", "Red", "Fill with Red / Залить красным"),
            ("GREEN", "Green", "Fill with Green / Залить зелёным"),
            ("BLUE", "Blue", "Fill with Blue / Залить синим"),
        ]
    )

    def execute(self, context):
        img = context.scene.terrain_rgb_mask_props.mask
        if img is None:
            self.report({"ERROR"}, "No mask image")
            return {"CANCELLED"}

        fill_mask(img, self.mode)
        self.report({"INFO"}, f"Mask filled: {self.mode}")
        return {"FINISHED"}


class TERRAIN_OT_save_mask(Operator, ExportHelper):
    bl_idname = "terrain_rgb.save_mask"
    bl_label = "Save RGB Mask"
    bl_description = "Save current RGB mask as PNG / Сохраняет текущую RGB-маску в PNG"

    filename_ext = ".png"
    filter_glob: StringProperty(default="*.png", options={"HIDDEN"})

    def execute(self, context):
        img = context.scene.terrain_rgb_mask_props.mask

        if img is None:
            self.report({"ERROR"}, "No mask image")
            return {"CANCELLED"}

        path = self.filepath
        if not path.lower().endswith(".png"):
            path += ".png"

        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()

        self.report({"INFO"}, f"Saved: {path}")
        return {"FINISHED"}


class VIEW3D_PT_terrain_rgb_mask(Panel):
    bl_label = "Terrain RGB Mask"
    bl_idname = "VIEW3D_PT_terrain_rgb_mask"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Terrain Mask"

    def draw(self, context):
        layout = self.layout
        props = context.scene.terrain_rgb_mask_props
        obj = get_active_object(context)

        layout.label(text="Mask")
        layout.prop(props, "mask_name")
        layout.prop(props, "mask_resolution")
        layout.prop(props, "mask")
        layout.operator("terrain_rgb.create_mask", text="Create RGB Mask")
        layout.operator("terrain_rgb.assign_mask", text="Assign Mask For Paint")

        layout.separator()
        layout.prop(props, "tile_scale")
        layout.operator("terrain_rgb.build_material", text="Build / Update Material")

        layout.separator()

        box = layout.box()
        box.label(text="Base Layer / Black")
        box.prop(props.base, "albedo")
        box.prop(props.base, "normal")
        box.prop(props.base, "rma")

        box = layout.box()
        box.label(text="Red Layer")
        box.prop(props.red, "albedo")
        box.prop(props.red, "normal")
        box.prop(props.red, "rma")

        box = layout.box()
        box.label(text="Green Layer")
        box.prop(props.green, "albedo")
        box.prop(props.green, "normal")
        box.prop(props.green, "rma")

        box = layout.box()
        box.label(text="Blue Layer")
        box.prop(props.blue, "albedo")
        box.prop(props.blue, "normal")
        box.prop(props.blue, "rma")

        layout.separator()
        layout.label(text="Paint")
        layout.prop(props, "brush_strength")
        layout.prop(props, "use_add_paint")

        row = layout.row(align=True)
        op = row.operator("terrain_rgb.set_paint", text="Base")
        op.mode = "BASE"
        op = row.operator("terrain_rgb.set_paint", text="R")
        op.mode = "RED"
        op = row.operator("terrain_rgb.set_paint", text="G")
        op.mode = "GREEN"
        op = row.operator("terrain_rgb.set_paint", text="B")
        op.mode = "BLUE"

        layout.prop(props, "active_paint", text="Active")

        layout.separator()
        layout.label(text="Mask Tools")

        row = layout.row(align=True)
        row.operator("terrain_rgb.blur_mask", text="Blur")

        layout.label(text="Fill")
        row = layout.row(align=True)
        op = row.operator("terrain_rgb.fill_mask", text="Base")
        op.mode = "BASE"
        op = row.operator("terrain_rgb.fill_mask", text="R")
        op.mode = "RED"
        op = row.operator("terrain_rgb.fill_mask", text="G")
        op.mode = "GREEN"
        op = row.operator("terrain_rgb.fill_mask", text="B")
        op.mode = "BLUE"

        layout.separator()
        layout.label(text="Preview")

        row = layout.row(align=True)
        op = row.operator("terrain_rgb.set_preview", text="Material")
        op.mode = "MATERIAL"
        op = row.operator("terrain_rgb.set_preview", text="Mask")
        op.mode = "MASK"

        row = layout.row(align=True)
        op = row.operator("terrain_rgb.set_preview", text="R")
        op.mode = "R"
        op = row.operator("terrain_rgb.set_preview", text="G")
        op.mode = "G"
        op = row.operator("terrain_rgb.set_preview", text="B")
        op.mode = "B"

        layout.separator()
        layout.operator("terrain_rgb.save_mask", text="Save Mask")

        if obj is None:
            layout.label(text="Select mesh object", icon="ERROR")
        elif len(obj.data.uv_layers) < 2:
            layout.label(text="Need UV1 and UV2", icon="ERROR")


classes = (
    TerrainLayer,
    TerrainProps,
    TERRAIN_OT_create_mask,
    TERRAIN_OT_build_material,
    TERRAIN_OT_assign_mask,
    TERRAIN_OT_set_paint,
    TERRAIN_OT_set_preview,
    TERRAIN_OT_blur_mask,
    TERRAIN_OT_fill_mask,
    TERRAIN_OT_save_mask,
    VIEW3D_PT_terrain_rgb_mask,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.terrain_rgb_mask_props = PointerProperty(type=TerrainProps)


def unregister():
    del bpy.types.Scene.terrain_rgb_mask_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()