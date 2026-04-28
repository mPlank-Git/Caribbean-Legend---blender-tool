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
from bpy.props import PointerProperty, IntProperty, EnumProperty, StringProperty, FloatProperty
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
        description="RGB mask texture. Black means Base layer; Red, Green and Blue paint additional layers / RGB-маска. Чёрный — базовый слой; красный, зелёный и синий — дополнительные слои",
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
        description="Tiling scale for all terrain layer textures using UV1 / Масштаб тайлинга текстур слоёв по UV1",
        default=4.0,
        min=0.001,
        max=1000.0,
    )

    brush_strength: FloatProperty(
        name="Brush Strength",
        description="Brush strength for Texture Paint mode / Сила кисти для режима Texture Paint",
        default=1.0,
        min=0.0,
        max=1.0,
    )

    active_paint: EnumProperty(
        name="Paint",
        description="Currently selected paint color/layer / Текущий выбранный слой покраски",
        items=[
            ("BASE", "Base / Erase", "Paint black to return to the Base layer / Красит чёрным, возвращая базовый слой"),
            ("RED", "Red Layer", "Paint the Red terrain layer / Красит красный слой"),
            ("GREEN", "Green Layer", "Paint the Green terrain layer / Красит зелёный слой"),
            ("BLUE", "Blue Layer", "Paint the Blue terrain layer / Красит синий слой"),
        ],
        default="RED",
    )

    preview_mode: EnumProperty(
        name="Preview",
        description="Viewport preview mode / Режим предпросмотра во вьюпорте",
        items=[
            ("MATERIAL", "Material", "Show final blended material / Показать итоговый смешанный материал"),
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


def process_pixels(img, func):
    pixels = list(img.pixels)

    for i in range(0, len(pixels), 4):
        r = pixels[i]
        g = pixels[i + 1]
        b = pixels[i + 2]

        r, g, b = func(r, g, b)

        pixels[i] = max(0.0, min(1.0, r))
        pixels[i + 1] = max(0.0, min(1.0, g))
        pixels[i + 2] = max(0.0, min(1.0, b))
        pixels[i + 3] = 1.0

    img.pixels[:] = pixels
    img.update()


def normalize_rgb_mask(img):
    def fn(r, g, b):
        s = r + g + b
        if s > 1.0:
            r /= s
            g /= s
            b /= s
        return r, g, b

    process_pixels(img, fn)


def suppress_others(img, active):
    def fn(r, g, b):
        if active == "RED":
            g *= 1.0 - r
            b *= 1.0 - r
        elif active == "GREEN":
            r *= 1.0 - g
            b *= 1.0 - g
        elif active == "BLUE":
            r *= 1.0 - b
            g *= 1.0 - b
        return r, g, b

    process_pixels(img, fn)


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
    out.location = (2600, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "TRGB_BSDF"
    bsdf.location = (2300, 0)

    uv1 = nodes.new("ShaderNodeUVMap")
    uv1.name = "TRGB_UV1"
    uv1.uv_map = uv1_name
    uv1.location = (-2200, 700)

    uv2 = nodes.new("ShaderNodeUVMap")
    uv2.name = "TRGB_UV2"
    uv2.uv_map = uv2_name
    uv2.location = (-2200, 100)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.name = "TRGB_Tile_Mapping"
    mapping.location = (-1950, 700)
    mapping.inputs["Scale"].default_value[0] = props.tile_scale
    mapping.inputs["Scale"].default_value[1] = props.tile_scale
    mapping.inputs["Scale"].default_value[2] = 1.0
    links.new(uv1.outputs["UV"], mapping.inputs["Vector"])

    mask = nodes.new("ShaderNodeTexImage")
    mask.name = "TRGB_Mask"
    mask.label = "RGB Mask"
    mask.image = props.mask
    mask.location = (-1950, 100)
    set_non_color(props.mask)
    links.new(uv2.outputs["UV"], mask.inputs["Vector"])

    sep = nodes.new("ShaderNodeSeparateColor")
    sep.name = "TRGB_Separate_Mask"
    sep.mode = "RGB"
    sep.location = (-1700, 100)
    links.new(mask.outputs["Color"], sep.inputs["Color"])

    layers = [
        ("Base", props.base),
        ("Red", props.red),
        ("Green", props.green),
        ("Blue", props.blue),
    ]

    albedos = []
    normals = []
    sep_rmas = []

    y = 1200
    for name, layer in layers:
        alb = nodes.new("ShaderNodeTexImage")
        alb.name = f"TRGB_{name}_Albedo"
        alb.label = f"{name} Albedo"
        alb.image = layer.albedo
        alb.location = (-1450, y)
        links.new(mapping.outputs["Vector"], alb.inputs["Vector"])
        albedos.append(alb)

        nrm = nodes.new("ShaderNodeTexImage")
        nrm.name = f"TRGB_{name}_Normal"
        nrm.label = f"{name} Normal"
        nrm.image = layer.normal
        nrm.location = (-1450, y - 160)
        links.new(mapping.outputs["Vector"], nrm.inputs["Vector"])
        set_non_color(layer.normal)
        normals.append(nrm)

        rma = nodes.new("ShaderNodeTexImage")
        rma.name = f"TRGB_{name}_RMA"
        rma.label = f"{name} RMA"
        rma.image = layer.rma
        rma.location = (-1450, y - 320)
        links.new(mapping.outputs["Vector"], rma.inputs["Vector"])
        set_non_color(layer.rma)

        srma = nodes.new("ShaderNodeSeparateColor")
        srma.name = f"TRGB_{name}_Separate_RMA"
        srma.mode = "RGB"
        srma.location = (-1200, y - 320)
        links.new(rma.outputs["Color"], srma.inputs["Color"])
        sep_rmas.append(srma)

        y -= 480

    def mix_rgb(name, a, b, fac, loc):
        m = nodes.new("ShaderNodeMixRGB")
        m.name = name
        m.blend_type = "MIX"
        m.location = loc
        links.new(a, m.inputs["Color1"])
        links.new(b, m.inputs["Color2"])
        links.new(fac, m.inputs["Fac"])
        return m

    alb_r = mix_rgb(
        "TRGB_Albedo_Mix_R",
        albedos[0].outputs["Color"],
        albedos[1].outputs["Color"],
        sep.outputs["Red"],
        (-700, 900),
    )

    alb_g = mix_rgb(
        "TRGB_Albedo_Mix_G",
        alb_r.outputs["Color"],
        albedos[2].outputs["Color"],
        sep.outputs["Green"],
        (-450, 750),
    )

    alb_b = mix_rgb(
        "TRGB_Albedo_Mix_B",
        alb_g.outputs["Color"],
        albedos[3].outputs["Color"],
        sep.outputs["Blue"],
        (-200, 600),
    )

    nrm_r = mix_rgb(
        "TRGB_Normal_Mix_R",
        normals[0].outputs["Color"],
        normals[1].outputs["Color"],
        sep.outputs["Red"],
        (-700, 250),
    )

    nrm_g = mix_rgb(
        "TRGB_Normal_Mix_G",
        nrm_r.outputs["Color"],
        normals[2].outputs["Color"],
        sep.outputs["Green"],
        (-450, 100),
    )

    nrm_b = mix_rgb(
        "TRGB_Normal_Mix_B",
        nrm_g.outputs["Color"],
        normals[3].outputs["Color"],
        sep.outputs["Blue"],
        (-200, -50),
    )

    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.name = "TRGB_Final_Normal"
    normal_map.location = (300, -50)
    links.new(nrm_b.outputs["Color"], normal_map.inputs["Color"])

    def mix_value(name, a, b, fac, loc):
        mix = nodes.new("ShaderNodeMix")
        mix.name = name
        mix.data_type = "FLOAT"
        mix.factor_mode = "UNIFORM"
        mix.location = loc
        links.new(fac, mix.inputs["Factor"])
        links.new(a, mix.inputs[6])
        links.new(b, mix.inputs[7])
        return mix

    rough_r = mix_value(
        "TRGB_Rough_R",
        sep_rmas[0].outputs["Red"],
        sep_rmas[1].outputs["Red"],
        sep.outputs["Red"],
        (-700, -500),
    )

    rough_g = mix_value(
        "TRGB_Rough_G",
        rough_r.outputs[0],
        sep_rmas[2].outputs["Red"],
        sep.outputs["Green"],
        (-350, -500),
    )

    rough_b = mix_value(
        "TRGB_Rough_B",
        rough_g.outputs[0],
        sep_rmas[3].outputs["Red"],
        sep.outputs["Blue"],
        (0, -500),
    )

    metal_r = mix_value(
        "TRGB_Metal_R",
        sep_rmas[0].outputs["Green"],
        sep_rmas[1].outputs["Green"],
        sep.outputs["Red"],
        (-700, -800),
    )

    metal_g = mix_value(
        "TRGB_Metal_G",
        metal_r.outputs[0],
        sep_rmas[2].outputs["Green"],
        sep.outputs["Green"],
        (-350, -800),
    )

    metal_b = mix_value(
        "TRGB_Metal_B",
        metal_g.outputs[0],
        sep_rmas[3].outputs["Green"],
        sep.outputs["Blue"],
        (0, -800),
    )

    preview = nodes.new("ShaderNodeMixRGB")
    preview.name = "TRGB_Preview_Switch"
    preview.blend_type = "MIX"
    preview.inputs["Fac"].default_value = 0.0
    preview.location = (1700, 400)

    combine = nodes.new("ShaderNodeCombineColor")
    combine.name = "TRGB_Preview_Combine"
    combine.mode = "RGB"
    combine.location = (1400, 100)

    links.new(alb_b.outputs["Color"], preview.inputs["Color1"])
    links.new(mask.outputs["Color"], preview.inputs["Color2"])

    links.new(preview.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(rough_b.outputs[0], bsdf.inputs["Roughness"])
    links.new(metal_b.outputs[0], bsdf.inputs["Metallic"])
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
    albedo = nodes.get("TRGB_Albedo_Mix_B")

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
        props = context.scene.terrain_rgb_mask_props
        create_mask_image(props)
        self.report({"INFO"}, "RGB mask created")
        return {"FINISHED"}


class TERRAIN_OT_build_material(Operator):
    bl_idname = "terrain_rgb.build_material"
    bl_label = "Build / Update Material"
    bl_description = "Build or update the preview material using Base + Red + Green + Blue layers / Собирает или обновляет материал предпросмотра из базового, красного, зелёного и синего слоёв"

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
    bl_description = "Set the RGB mask as the active Texture Paint target / Назначает RGB-маску активной текстурой для рисования в Texture Paint"

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
    bl_description = "Switch brush color for painting Base, Red, Green or Blue mask layer / Переключает цвет кисти для покраски базового, красного, зелёного или синего слоя"

    mode: EnumProperty(
        items=[
            ("BASE", "Base", "Paint black to erase to Base layer / Красит чёрным, возвращая базовый слой"),
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
            elif self.mode == "RED":
                paint.brush.color = (1.0, 0.0, 0.0)
            elif self.mode == "GREEN":
                paint.brush.color = (0.0, 1.0, 0.0)
            elif self.mode == "BLUE":
                paint.brush.color = (0.0, 0.0, 1.0)

        self.report({"INFO"}, f"Paint mode: {self.mode}")
        return {"FINISHED"}


class TERRAIN_OT_set_preview(Operator):
    bl_idname = "terrain_rgb.set_preview"
    bl_label = "Set Preview"
    bl_description = "Switch viewport preview between final material, full mask, or single RGB channel / Переключает предпросмотр между итоговым материалом, полной маской или отдельным RGB-каналом"

    mode: EnumProperty(
        items=[
            ("MATERIAL", "Material", "Show final blended material / Показать итоговый смешанный материал"),
            ("MASK", "Mask", "Show raw RGB mask / Показать RGB-маску"),
            ("R", "R", "Show red channel only / Показать только красный канал"),
            ("G", "G", "Show green channel only / Показать только зелёный канал"),
            ("B", "B", "Show blue channel only / Показать только синий канал"),
        ]
    )

    def execute(self, context):
        props = context.scene.terrain_rgb_mask_props
        props.preview_mode = self.mode

        obj = get_active_object(context)
        if obj and obj.active_material:
            apply_preview(obj.active_material, self.mode)

        return {"FINISHED"}


class TERRAIN_OT_normalize_mask(Operator):
    bl_idname = "terrain_rgb.normalize_mask"
    bl_label = "Normalize RGB Mask"
    bl_description = "Normalize RGB channels so their sum does not exceed 1. Reduces dirty overblending / Нормализует RGB-каналы, чтобы их сумма не превышала 1. Убирает грязное пересмешивание"

    def execute(self, context):
        img = context.scene.terrain_rgb_mask_props.mask
        if img is None:
            self.report({"ERROR"}, "No mask image")
            return {"CANCELLED"}

        normalize_rgb_mask(img)
        self.report({"INFO"}, "RGB mask normalized")
        return {"FINISHED"}


class TERRAIN_OT_suppress_others(Operator):
    bl_idname = "terrain_rgb.suppress_others"
    bl_label = "Paint One / Suppress Others"
    bl_description = "Make the active painted layer suppress the other RGB channels / Активный слой подавляет остальные RGB-каналы, делая покраску чище"

    def execute(self, context):
        props = context.scene.terrain_rgb_mask_props
        img = props.mask

        if img is None:
            self.report({"ERROR"}, "No mask image")
            return {"CANCELLED"}

        if props.active_paint == "BASE":
            self.report({"WARNING"}, "Base mode does not suppress channels")
            return {"CANCELLED"}

        suppress_others(img, props.active_paint)
        normalize_rgb_mask(img)

        self.report({"INFO"}, "Other channels suppressed")
        return {"FINISHED"}


class TERRAIN_OT_blur_mask(Operator):
    bl_idname = "terrain_rgb.blur_mask"
    bl_label = "Blur RGB Mask"
    bl_description = "Blur the RGB mask with a simple 3x3 filter and normalize it after blur / Размывает RGB-маску простым фильтром 3x3 и нормализует её после размытия"

    def execute(self, context):
        img = context.scene.terrain_rgb_mask_props.mask
        if img is None:
            self.report({"ERROR"}, "No mask image")
            return {"CANCELLED"}

        blur_rgb_mask(img)
        normalize_rgb_mask(img)

        self.report({"INFO"}, "RGB mask blurred")
        return {"FINISHED"}


class TERRAIN_OT_fill_mask(Operator):
    bl_idname = "terrain_rgb.fill_mask"
    bl_label = "Fill Mask"
    bl_description = "Fill the whole RGB mask with Base, Red, Green or Blue / Полностью заливает RGB-маску базовым, красным, зелёным или синим слоем"

    mode: EnumProperty(
        items=[
            ("BASE", "Base", "Fill mask with black Base layer / Залить маску чёрным базовым слоем"),
            ("RED", "Red", "Fill mask with Red layer / Залить маску красным слоем"),
            ("GREEN", "Green", "Fill mask with Green layer / Залить маску зелёным слоем"),
            ("BLUE", "Blue", "Fill mask with Blue layer / Залить маску синим слоем"),
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
    bl_description = "Save the current RGB mask texture as PNG / Сохраняет текущую RGB-маску в PNG"

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
        layout.label(text="Mask Tools / Инструменты маски")

        row = layout.row(align=True)
        row.operator("terrain_rgb.normalize_mask", text="Normalize")
        row.operator("terrain_rgb.suppress_others", text="Paint One")

        row = layout.row(align=True)
        row.operator("terrain_rgb.blur_mask", text="Blur")

        layout.label(text="Fill / Заливка")
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
    TERRAIN_OT_normalize_mask,
    TERRAIN_OT_suppress_others,
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