bl_info = {
    "name": "CL Texture Tools",
    "author": "mPlank",
    "version": (0, 5, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Texture Tools",
    "description": "Tools for Caribbean Legend texture relinking and engine path assignment",
    "category": "Material",
}

import bpy
import os
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator, Panel, PropertyGroup


ADDON_NAME = __name__


SUPPORTED_EXTENSIONS = {
    ".tga",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".dds",
    ".webp",
    ".exr",
}


PATH_PRESETS = {
    "NONE": "",
    "Props": "Resource\\Textures\\Props\\",
    "Location": "Resource\\Textures\\Location\\",
    "Vegetation": "Resource\\Textures\\Vegetation\\",
    "ShipOther": "Resource\\Textures\\Ships\\Other\\",
    "1ShipsTexture": "Resource\\Textures\\Ships\\1ShipsTextures\\",
    "Characters": "Resource\\Textures\\Characters\\",
    "WorldMap": "Resource\\Textures\\WorldMap\\geometry\\",
    "Ammo": "Resource\\Textures\\Ammo\\",
    "Items": "Resource\\Textures\\Items\\",
    "Grass": "Resource\\Textures\\Grass\\",
}


PATH_PRESET_ITEMS = [
    ("NONE", "None", "Use default texture paths"),
    ("Props", "Props", "Resource\\Textures\\Props\\"),
    ("Location", "Location", "Resource\\Textures\\Location\\"),
    ("Vegetation", "Vegetation", "Resource\\Textures\\Vegetation\\"),
    ("ShipOther", "ShipOther", "Resource\\Textures\\Ships\\Other\\"),
    ("1ShipsTexture", "1ShipsTexture", "Resource\\Textures\\Ships\\1ShipsTextures\\"),
    ("Characters", "Characters", "Resource\\Textures\\Characters\\"),
    ("WorldMap", "WorldMap", "Resource\\Textures\\WorldMap\\geometry\\"),
    ("Ammo", "Ammo", "Resource\\Textures\\Ammo\\"),
    ("Items", "Items", "Resource\\Textures\\Items\\"),
    ("Grass", "Grass", "Resource\\Textures\\Grass\\"),
]


TRANSLATIONS = {
    "ru_RU": {
        ("*", "Texture Folder"): "Папка текстур",
        ("*", "Folder with replacement textures"): "Папка с текстурами для перепривязки",

        ("*", "Search Subfolders"): "Искать в подпапках",
        ("*", "Search textures inside subfolders"): "Искать текстуры внутри подпапок",

        ("*", "Only Base Color"): "Только Base Color",
        ("*", "Relink only Image Texture nodes connected directly to Principled BSDF Base Color"):
            "Перепривязывать только Image Texture-ноды, напрямую подключённые к Base Color у Principled BSDF",

        ("*", "Prefer DDS"): "Приоритет DDS",
        ("*", "Search by texture name but force .dds extension. Example: store3_1.tga -> store3_1.dds"):
            "Искать по имени текстуры, но принудительно использовать расширение .dds. Например: store3_1.tga -> store3_1.dds",

        ("*", "Reuse Loaded Images"): "Использовать уже загруженные",
        ("*", "Reuse already loaded Blender images if they point to the same file"):
            "Использовать уже загруженные изображения Blender, если они указывают на тот же файл",

        ("*", "Path Preset"): "Пресет пути",
        ("*", "Saved path preset"): "Сохранённый пресет пути",

        ("*", "Albedo Path"): "Путь Albedo",
        ("*", "Path prefix for albedo texture image names"):
            "Префикс пути для имени albedo-текстур. Resource не нужен, движок подставляет его сам",

        ("*", "PBR Path"): "Путь PBR",
        ("*", "Path prefix for _nom and _rma texture image names"):
            "Префикс пути для _nom и _rma текстур. Для них Resource должен быть в пути",

        ("*", "AO Path"): "Путь AO",
        ("*", "Path prefix for _ao texture image names"):
            "Префикс пути для _ao текстур. Resource не нужен, движок подставляет его сам",

        ("*", "Relink Texture Files"): "Перепривязка файлов текстур",
        ("*", "Path Presets"): "Пресеты путей",
        ("*", "Apply Paths To Texture Names"): "Применить пути к именам текстур",

        ("*", "Relink Textures"): "Перепривязать текстуры",
        ("*", "Relink existing Image Texture nodes by filename to selected texture folder"):
            "Перепривязать существующие Image Texture-ноды по имени файла к выбранной папке",

        ("*", "Load Preset"): "Загрузить пресет",
        ("*", "Load selected path preset into Albedo, PBR and AO path fields"):
            "Загрузить выбранный пресет в поля Albedo, PBR и AO",

        ("*", "Apply Paths"): "Применить пути",
        ("*", "Apply path prefixes to texture image names on selected objects"):
            "Применить префиксы путей к именам текстур у выделенных объектов",

        ("*", "Use default texture paths"): "Использовать пути по умолчанию",
    }
}


def normalize_name(name):
    return os.path.basename(name).lower()


def get_name_without_extension(filename):
    return os.path.splitext(os.path.basename(filename))[0].lower()


def build_texture_index(folder_path, recursive=False):
    texture_index_by_full_name = {}
    texture_index_by_name_no_ext = {}

    if not os.path.isdir(folder_path):
        return texture_index_by_full_name, texture_index_by_name_no_ext

    def add_file(root, filename):
        ext = os.path.splitext(filename)[1].lower()

        if ext not in SUPPORTED_EXTENSIONS:
            return

        full_path = os.path.join(root, filename)
        full_name_key = normalize_name(filename)
        name_no_ext_key = get_name_without_extension(filename)

        texture_index_by_full_name[full_name_key] = full_path

        if name_no_ext_key not in texture_index_by_name_no_ext:
            texture_index_by_name_no_ext[name_no_ext_key] = {}

        texture_index_by_name_no_ext[name_no_ext_key][ext] = full_path

    if recursive:
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                add_file(root, filename)
    else:
        for filename in os.listdir(folder_path):
            full_path = os.path.join(folder_path, filename)

            if os.path.isfile(full_path):
                add_file(folder_path, filename)

    return texture_index_by_full_name, texture_index_by_name_no_ext


def get_image_filename(image):
    if image is None:
        return None

    if image.filepath:
        filename = os.path.basename(bpy.path.abspath(image.filepath))
        if filename:
            return filename

    if image.name:
        clean_name = image.name.replace("\\", "/")
        return os.path.basename(clean_name)

    return None


def get_image_base_filename(image):
    if image is None:
        return None

    if image.filepath:
        filename = os.path.basename(bpy.path.abspath(image.filepath))
        if filename:
            return filename

    if image.name:
        clean_name = image.name.replace("\\", "/")
        return os.path.basename(clean_name)

    return None


def image_texture_is_connected_to_base_color(node):
    if node is None:
        return False

    if "Color" not in node.outputs:
        return False

    for link in node.outputs["Color"].links:
        target_node = link.to_node
        target_socket = link.to_socket

        if target_node and target_node.type == "BSDF_PRINCIPLED":
            if target_socket and target_socket.name == "Base Color":
                return True

    return False


def get_texture_nodes(material, only_base_color):
    nodes = []

    if material is None:
        return nodes

    if not material.use_nodes:
        return nodes

    if material.node_tree is None:
        return nodes

    for node in material.node_tree.nodes:
        if node.type != "TEX_IMAGE":
            continue

        if only_base_color:
            if not image_texture_is_connected_to_base_color(node):
                continue

        nodes.append(node)

    return nodes


def find_replacement_texture(
    old_filename,
    texture_index_by_full_name,
    texture_index_by_name_no_ext,
    prefer_dds,
):
    if not old_filename:
        return None

    if prefer_dds:
        name_no_ext = get_name_without_extension(old_filename)

        if name_no_ext in texture_index_by_name_no_ext:
            textures_by_extension = texture_index_by_name_no_ext[name_no_ext]

            if ".dds" in textures_by_extension:
                return textures_by_extension[".dds"]

        return None

    full_name = normalize_name(old_filename)

    if full_name in texture_index_by_full_name:
        return texture_index_by_full_name[full_name]

    return None


def normalize_texture_prefix(prefix):
    prefix = prefix.strip()

    if not prefix:
        return ""

    prefix = prefix.replace("/", "\\")

    if not prefix.endswith("\\"):
        prefix += "\\"

    return prefix


def remove_resource_prefix(path):
    path = path.replace("/", "\\")

    if path.lower().startswith("resource\\"):
        return path[len("Resource\\"):]

    return path


def get_texture_path_type(filename):
    name = filename.lower()

    if "_ao" in name or name.endswith("ao.dds") or name.endswith("ao.tga") or name.endswith("ao.png"):
        return "AO"

    if "_nom" in name or "_rma" in name:
        return "PBR"

    return "ALBEDO"


def get_prefix_for_texture(filename, props):
    texture_type = get_texture_path_type(filename)

    if texture_type == "AO":
        return normalize_texture_prefix(props.ao_name_path), texture_type

    if texture_type == "PBR":
        return normalize_texture_prefix(props.pbr_name_path), texture_type

    return normalize_texture_prefix(props.albedo_name_path), texture_type


def get_preset_path(preset_key):
    return PATH_PRESETS.get(preset_key, "")


def apply_preset_to_path_fields(props, preset_key):
    path = get_preset_path(preset_key)

    if preset_key == "NONE":
        pbr_path = "Resource\\Textures\\"
        engine_path = "Textures\\"
    else:
        pbr_path = path
        engine_path = remove_resource_prefix(path)

    props.albedo_name_path = engine_path
    props.pbr_name_path = pbr_path
    props.ao_name_path = engine_path


class RelinkAlbedoTexturesProperties(PropertyGroup):
    texture_folder: StringProperty(
        name="Texture Folder",
        description="Folder with replacement textures",
        subtype="DIR_PATH",
        default="",
    )

    recursive_search: BoolProperty(
        name="Search Subfolders",
        description="Search textures inside subfolders",
        default=False,
    )

    only_base_color: BoolProperty(
        name="Only Base Color",
        description="Relink only Image Texture nodes connected directly to Principled BSDF Base Color",
        default=False,
    )

    prefer_dds: BoolProperty(
        name="Prefer DDS",
        description="Search by texture name but force .dds extension. Example: store3_1.tga -> store3_1.dds",
        default=False,
    )

    reuse_loaded_images: BoolProperty(
        name="Reuse Loaded Images",
        description="Reuse already loaded Blender images if they point to the same file",
        default=True,
    )

    path_preset: EnumProperty(
        name="Path Preset",
        description="Saved path preset",
        items=PATH_PRESET_ITEMS,
        default="NONE",
    )

    albedo_name_path: StringProperty(
        name="Albedo Path",
        description="Path prefix for albedo texture image names",
        default="Textures\\",
    )

    pbr_name_path: StringProperty(
        name="PBR Path",
        description="Path prefix for _nom and _rma texture image names",
        default="Resource\\Textures\\",
    )

    ao_name_path: StringProperty(
        name="AO Path",
        description="Path prefix for _ao texture image names",
        default="Textures\\",
    )


class RELINK_OT_albedo_textures(Operator):
    bl_idname = "relink.albedo_textures"
    bl_label = "Relink Textures"
    bl_description = "Relink existing Image Texture nodes by filename to selected texture folder"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.relink_albedo_textures_props

        folder_path = bpy.path.abspath(props.texture_folder)

        if not folder_path or not os.path.isdir(folder_path):
            self.report({"ERROR"}, "Texture folder is not valid")
            return {"CANCELLED"}

        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({"WARNING"}, "No objects selected")
            return {"CANCELLED"}

        texture_index_by_full_name, texture_index_by_name_no_ext = build_texture_index(
            folder_path,
            props.recursive_search,
        )

        if not texture_index_by_full_name:
            self.report({"WARNING"}, "No supported texture files found in selected folder")
            return {"CANCELLED"}

        processed_materials = set()
        relinked_count = 0
        missing_count = 0
        skipped_count = 0
        material_count = 0
        missing_files = []

        for obj in selected_objects:
            if not hasattr(obj, "material_slots"):
                continue

            for slot in obj.material_slots:
                material = slot.material

                if material is None:
                    continue

                if material.name in processed_materials:
                    continue

                processed_materials.add(material.name)
                material_count += 1

                texture_nodes = get_texture_nodes(material, props.only_base_color)

                if not texture_nodes:
                    skipped_count += 1
                    continue

                for node in texture_nodes:
                    old_image = node.image

                    if old_image is None:
                        skipped_count += 1
                        continue

                    old_filename = get_image_filename(old_image)

                    if not old_filename:
                        skipped_count += 1
                        continue

                    new_path = find_replacement_texture(
                        old_filename,
                        texture_index_by_full_name,
                        texture_index_by_name_no_ext,
                        props.prefer_dds,
                    )

                    if not new_path:
                        missing_count += 1

                        if props.prefer_dds:
                            missing_files.append(f"{get_name_without_extension(old_filename)}.dds")
                        else:
                            missing_files.append(old_filename)

                        continue

                    new_path_abs = os.path.abspath(new_path)

                    existing_image = None

                    if props.reuse_loaded_images:
                        for img in bpy.data.images:
                            if not img.filepath:
                                continue

                            img_path = os.path.abspath(bpy.path.abspath(img.filepath))

                            if os.path.normcase(img_path) == os.path.normcase(new_path_abs):
                                existing_image = img
                                break

                    if existing_image:
                        new_image = existing_image
                    else:
                        try:
                            new_image = bpy.data.images.load(new_path_abs, check_existing=True)
                        except Exception as error:
                            self.report({"WARNING"}, f"Failed to load: {old_filename}")
                            print(f"[Relink Albedo Textures] Failed to load {new_path_abs}: {error}")
                            skipped_count += 1
                            continue

                    new_image.colorspace_settings.name = "sRGB"
                    node.image = new_image

                    relinked_count += 1

                    print(
                        f"[Relink Albedo Textures] "
                        f"{material.name}: {old_filename} -> {new_path_abs}"
                    )

        if missing_files:
            print("[Relink Albedo Textures] Missing files:")
            for filename in sorted(set(missing_files)):
                print(f"  {filename}")

        self.report(
            {"INFO"},
            f"Done. Materials: {material_count}, Relinked: {relinked_count}, Missing: {missing_count}, Skipped: {skipped_count}"
        )

        return {"FINISHED"}


class RELINK_OT_load_path_preset(Operator):
    bl_idname = "relink.load_path_preset"
    bl_label = "Load Preset"
    bl_description = "Load selected path preset into Albedo, PBR and AO path fields"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.relink_albedo_textures_props

        apply_preset_to_path_fields(props, props.path_preset)

        self.report({"INFO"}, f"Loaded preset: {props.path_preset}")
        return {"FINISHED"}


class RELINK_OT_apply_texture_name_paths(Operator):
    bl_idname = "relink.apply_texture_name_paths"
    bl_label = "Apply Paths"
    bl_description = "Apply path prefixes to texture image names on selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.relink_albedo_textures_props

        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({"WARNING"}, "No objects selected")
            return {"CANCELLED"}

        processed_materials = set()
        renamed_count = 0
        skipped_count = 0

        for obj in selected_objects:
            if not hasattr(obj, "material_slots"):
                continue

            for slot in obj.material_slots:
                material = slot.material

                if material is None:
                    continue

                if material.name in processed_materials:
                    continue

                processed_materials.add(material.name)

                texture_nodes = get_texture_nodes(material, props.only_base_color)

                if not texture_nodes:
                    skipped_count += 1
                    continue

                for node in texture_nodes:
                    image = node.image

                    if image is None:
                        skipped_count += 1
                        continue

                    filename = get_image_base_filename(image)

                    if not filename:
                        skipped_count += 1
                        continue

                    prefix, texture_type = get_prefix_for_texture(filename, props)

                    if not prefix:
                        skipped_count += 1
                        print(
                            f"[Relink Albedo Textures] "
                            f"{material.name}: skipped '{filename}', empty {texture_type} path"
                        )
                        continue

                    new_name = prefix + filename

                    old_name = image.name
                    image.name = new_name

                    renamed_count += 1

                    print(
                        f"[Relink Albedo Textures] "
                        f"{material.name}: {texture_type} image name '{old_name}' -> '{new_name}'"
                    )

        self.report(
            {"INFO"},
            f"Apply Paths done. Renamed: {renamed_count}, Skipped: {skipped_count}"
        )

        return {"FINISHED"}


class RELINK_PT_albedo_textures_panel(Panel):
    bl_label = "Relink Textures"
    bl_idname = "RELINK_PT_albedo_textures_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Texture Tools"

    def draw(self, context):
        layout = self.layout
        props = context.scene.relink_albedo_textures_props

        layout.label(text="Relink Texture Files")
        layout.prop(props, "texture_folder")
        layout.prop(props, "recursive_search")
        layout.prop(props, "only_base_color")
        layout.prop(props, "prefer_dds")
        layout.prop(props, "reuse_loaded_images")

        layout.operator(
            "relink.albedo_textures",
            icon="FILE_REFRESH"
        )

        layout.separator()

        layout.label(text="Path Presets")
        row = layout.row(align=True)
        row.prop(props, "path_preset", text="")
        row.operator(
            "relink.load_path_preset",
            text="Load",
            icon="IMPORT"
        )

        layout.separator()

        layout.label(text="Apply Paths To Texture Names")
        layout.prop(props, "albedo_name_path")
        layout.prop(props, "pbr_name_path")
        layout.prop(props, "ao_name_path")

        layout.operator(
            "relink.apply_texture_name_paths",
            icon="FILE_TICK"
        )


classes = (
    RelinkAlbedoTexturesProperties,
    RELINK_OT_albedo_textures,
    RELINK_OT_load_path_preset,
    RELINK_OT_apply_texture_name_paths,
    RELINK_PT_albedo_textures_panel,
)


def register():
    bpy.app.translations.register(ADDON_NAME, TRANSLATIONS)

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.relink_albedo_textures_props = bpy.props.PointerProperty(
        type=RelinkAlbedoTexturesProperties
    )


def unregister():
    if hasattr(bpy.types.Scene, "relink_albedo_textures_props"):
        del bpy.types.Scene.relink_albedo_textures_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    bpy.app.translations.unregister(ADDON_NAME)


if __name__ == "__main__":
    register()