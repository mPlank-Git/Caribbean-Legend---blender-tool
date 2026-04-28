bl_info = {
"license": "GPL-3.0-or-later",
    "name": "CL_GM JSON Export",
    "author": "mPlank",
    "version": (1, 4, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > GM JSON",
    "description": "Per-collection JSON with mesh object properties for Caribbean Legend GM pipeline",
    "category": "Import-Export",
}
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This add-on is licensed under the GNU General Public License v3.0 or later.
# Этот аддон распространяется по лицензии GNU General Public License v3.0 или более поздней версии.
import bpy
from bpy.props import (
    BoolProperty,
    PointerProperty,
    StringProperty,
    CollectionProperty,
    IntProperty,
    EnumProperty,
)
from bpy.types import Operator, Panel, PropertyGroup, UIList, AddonPreferences
import os
import json


DEFAULTS = {
    "reflection": 0,
    "alpha": 0,
    "rma_texture": "Resource\\Textures\\base_RMA.tga.tx",
    "normal_texture": "Resource\\Textures\\base_nom.tga.tx",
}


# тут пресеты путей
# Добавляй новые пресеты сюда.
# Ключ слева должен совпадать с первым значением в PATH_PRESET_ITEMS ниже.
PATH_PRESETS = {
    "NONE": "",
    "Props": "Resource\\Textures\\Props\\",
    "Location": "Resource\\Textures\\Location\\",
    "Vegetation": "Resource\\Textures\\Vegetation\\",
}

# UI-список пресетов для EnumProperty.
# Если добавляешь новый preset в PATH_PRESETS, добавь его и сюда.
PATH_PRESET_ITEMS = [
    ("NONE", "None", "Use default Resource\\Textures\\"),
    ("Props", "Props", "Resource\\Textures\\Props\\"),
    ("Location", "Location", "Resource\\Textures\\Location\\"),
    ("Vegetation", "Vegetation", "Resource\\Textures\\Vegetation\\"),
]


def normalize_path(p: str) -> str:
    if not p:
        return ""
    return p.replace("/", "\\")


def looks_like_path(s: str) -> bool:
    return ("/" in s) or ("\\" in s)


def preset_base_path(preset_name: str) -> str:
    if not preset_name or preset_name == "NONE":
        return "Resource\\Textures\\"
    return PATH_PRESETS.get(preset_name, "Resource\\Textures\\")


def build_texture_path(name: str, preset_name: str) -> str:
    name = normalize_path(name)
    if not name:
        return ""
    if looks_like_path(name):
        return name
    return preset_base_path(preset_name) + name


def _prefs():
    return bpy.context.preferences.addons[__name__].preferences


def collection_key(scene: bpy.types.Scene, coll: bpy.types.Collection) -> str:
    blend = bpy.data.filepath if bpy.data.filepath else "<unsaved>"
    return f"{blend}|{scene.name}|{coll.name}"


def get_folder_for_collection(scene, coll) -> str:
    key = collection_key(scene, coll)
    return _prefs().collection_paths.get(key, "")


def set_folder_for_collection(scene, coll, folder: str):
    key = collection_key(scene, coll)
    paths = _prefs().collection_paths
    paths[key] = folder
    _prefs().collection_paths = paths


def json_path_for(scene, coll) -> str:
    folder = get_folder_for_collection(scene, coll)
    if not folder:
        return ""
    return os.path.join(folder, f"{coll.name}.json")


def read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"models": {}}
    except Exception:
        return {"models": {}}


def write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def meshes_in_collection(coll: bpy.types.Collection):
    return [o for o in set(coll.all_objects) if o.type == "MESH"]


def selected_meshes_in_collection(context, coll: bpy.types.Collection):
    allowed = set(o.name for o in meshes_in_collection(coll))
    return [o for o in context.selected_objects if o.type == "MESH" and o.name in allowed]


def find_duplicate_names_in_collection(coll: bpy.types.Collection):
    seen = set()
    dups = set()
    for o in meshes_in_collection(coll):
        if o.name in seen:
            dups.add(o.name)
        else:
            seen.add(o.name)
    return sorted(dups)


def _iter_image_texture_nodes(node_tree, visited=None):
    if not node_tree:
        return
    if visited is None:
        visited = set()
    ptr = node_tree.as_pointer()
    if ptr in visited:
        return
    visited.add(ptr)

    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE":
            yield node
        elif node.type == "GROUP" and getattr(node, "node_tree", None):
            yield from _iter_image_texture_nodes(node.node_tree, visited)


def _image_node_name(node) -> str:
    img = getattr(node, "image", None)
    if not img:
        return ""
    return img.name or ""


def detect_textures_from_object(obj: bpy.types.Object, preset_name: str = "NONE"):
    rma = None
    nom = None
    emission = None

    if not obj or obj.type != "MESH":
        return (None, None, None)
    if not obj.material_slots:
        return (None, None, None)

    mat = obj.material_slots[0].material
    if not mat or not mat.use_nodes or not mat.node_tree:
        return (None, None, None)

    for node in _iter_image_texture_nodes(mat.node_tree):
        name = _image_node_name(node)
        if not name:
            continue

        low = name.lower()

        if rma is None and "_rma" in low:
            rma = build_texture_path(name, preset_name)
        if nom is None and "_nom" in low:
            nom = build_texture_path(name, preset_name)
        if emission is None and "_emission" in low:
            emission = build_texture_path(name, preset_name)

        if rma and nom and emission:
            break

    return (rma, nom, emission)


def ensure_entry(models: dict, obj: bpy.types.Object, refresh_textures=False):
    if not obj:
        return

    entry = models.get(obj.name)
    if entry is None:
        entry = dict(DEFAULTS)
        entry["path_preset"] = "NONE"
        models[obj.name] = entry

    for k, v in DEFAULTS.items():
        entry.setdefault(k, v)
    entry.setdefault("path_preset", "NONE")

    if refresh_textures:
        preset_name = entry.get("path_preset", "NONE")
        rma, nom, _em = detect_textures_from_object(obj, preset_name)
        if rma:
            entry["rma_texture"] = normalize_path(rma)
        if nom:
            entry["normal_texture"] = normalize_path(nom)


def normalize_models_before_write(models: dict):
    for ent in models.values():
        if isinstance(ent, dict):
            ent.setdefault("path_preset", "NONE")

            if "rma_texture" in ent:
                ent["rma_texture"] = normalize_path(ent.get("rma_texture", DEFAULTS["rma_texture"])) or DEFAULTS["rma_texture"]
            if "normal_texture" in ent:
                ent["normal_texture"] = normalize_path(ent.get("normal_texture", DEFAULTS["normal_texture"])) or DEFAULTS["normal_texture"]
            if "emission_texture" in ent:
                ent["emission_texture"] = normalize_path(ent.get("emission_texture", ""))


def sync_collection(scene: bpy.types.Scene, coll: bpy.types.Collection, refresh_textures=False, remove_missing=True):
    path = json_path_for(scene, coll)
    if not path:
        return [], "Select folder for this collection first"

    data = read_json(path)
    if "models" not in data or not isinstance(data["models"], dict):
        data["models"] = {}

    models = data["models"]
    coll_meshes = meshes_in_collection(coll)
    current_names = set(o.name for o in coll_meshes)

    for o in coll_meshes:
        ensure_entry(models, o, refresh_textures=refresh_textures)

    removed = []
    if remove_missing:
        for name in list(models.keys()):
            if name not in current_names:
                removed.append(name)
                models.pop(name, None)

    normalize_models_before_write(models)
    write_json(path, data)
    return removed, ""


def batch_flag_status(context, coll, flag_name: str) -> str:
    targets = selected_meshes_in_collection(context, coll)
    if not targets:
        return "No selection"

    path = json_path_for(context.scene, coll)
    data = read_json(path) if path else {"models": {}}
    models = data.get("models", {})

    values = []
    for obj in targets:
        ensure_entry(models, obj, refresh_textures=False)
        entry = models.get(obj.name, {})
        values.append(1 if entry.get(flag_name, 0) else 0)

    if not values:
        return "No selection"

    if all(v == 1 for v in values):
        return "On"
    if all(v == 0 for v in values):
        return "Off"
    return "Mixed"


def sync_active_object_from_viewport(context):
    scene = context.scene
    settings = scene.gmjson_settings
    coll = settings.collection
    wm = context.window_manager

    if not coll:
        return

    active = context.active_object
    if not active or active.type != "MESH":
        return

    allowed = set(o.name for o in meshes_in_collection(coll))
    if active.name not in allowed:
        return

    if wm.gmjson_proxy_object == active.name:
        return

    rebuild_object_list(context)
    for i, it in enumerate(scene.gmjson_objects):
        if it.name == active.name:
            settings.active_index = i
            break


class GMJSON_ObjectItem(PropertyGroup):
    name: StringProperty(name="Object Name")


def _on_collection_change(self, context):
    rebuild_object_list(context)
    settings = context.scene.gmjson_settings
    if settings.collection:
        folder = get_folder_for_collection(context.scene, settings.collection)
        if folder:
            sync_collection(context.scene, settings.collection, refresh_textures=False, remove_missing=False)


def _on_active_index_change(self, context):
    settings = context.scene.gmjson_settings
    coll = settings.collection
    wm = context.window_manager

    if not coll or settings.active_index < 0 or settings.active_index >= len(context.scene.gmjson_objects):
        wm.gmjson_proxy_object = ""
        return

    obj_name = context.scene.gmjson_objects[settings.active_index].name
    wm.gmjson_proxy_object = obj_name
    load_proxy_from_json(context, coll, obj_name)


def _on_emission_toggle(self, context):
    _proxy_update(self, context)

    scene = context.scene
    coll = scene.gmjson_settings.collection
    wm = context.window_manager

    if not coll:
        return

    obj_name = wm.gmjson_proxy_object
    if not obj_name:
        return

    if wm.gmjson_emission and not wm.gmjson_emission_texture.strip():
        path = json_path_for(scene, coll)
        if not path:
            return

        data = read_json(path)
        models = data.get("models", {})
        entry = models.get(obj_name, {})
        preset_name = entry.get("path_preset", "NONE")

        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return

        _rma, _nom, emission = detect_textures_from_object(obj, preset_name)
        if emission:
            wm.gmjson_emission_texture = normalize_path(emission)


class GMJSON_Settings(PropertyGroup):
    collection: PointerProperty(type=bpy.types.Collection, update=_on_collection_change)
    active_index: IntProperty(default=-1, update=_on_active_index_change)


class GMJSON_AddonPreferences(AddonPreferences):
    bl_idname = __name__

    autosave: BoolProperty(
        name="Autosave",
        description="Automatically save JSON after edits",
        default=False,
    )

    collection_paths_json: StringProperty(default="{}")

    def _get_paths(self):
        try:
            return json.loads(self.collection_paths_json or "{}")
        except Exception:
            return {}

    def _set_paths(self, d):
        try:
            self.collection_paths_json = json.dumps(d, ensure_ascii=False)
        except Exception:
            self.collection_paths_json = "{}"

    @property
    def collection_paths(self):
        return self._get_paths()

    @collection_paths.setter
    def collection_paths(self, v):
        self._set_paths(v)

    def draw(self, context):
        self.layout.prop(self, "autosave")


def _proxy_update(self, context):
    scene = context.scene
    coll = scene.gmjson_settings.collection
    if not coll:
        return

    obj_name = context.window_manager.gmjson_proxy_object
    if not obj_name:
        return

    path = json_path_for(scene, coll)
    if not path:
        return

    data = read_json(path)
    models = data.get("models", {})
    if not isinstance(models, dict):
        models = {}
        data["models"] = models

    allowed = set(o.name for o in meshes_in_collection(coll))
    if obj_name not in allowed:
        return

    entry = models.get(obj_name)
    if entry is None:
        entry = dict(DEFAULTS)
        entry["path_preset"] = "NONE"
        models[obj_name] = entry

    for k, v in DEFAULTS.items():
        entry.setdefault(k, v)
    entry.setdefault("path_preset", "NONE")

    wm = context.window_manager

    entry["reflection"] = 1 if wm.gmjson_reflection else 0
    entry["alpha"] = 1 if wm.gmjson_alpha else 0
    entry["rma_texture"] = normalize_path(wm.gmjson_rma_texture) or DEFAULTS["rma_texture"]
    entry["normal_texture"] = normalize_path(wm.gmjson_normal_texture) or DEFAULTS["normal_texture"]
    entry["path_preset"] = wm.gmjson_path_preset

    if wm.gmjson_animation_enabled and wm.gmjson_animation_name.strip():
        entry["animation"] = wm.gmjson_animation_name.strip()
    else:
        entry.pop("animation", None)

    if wm.gmjson_shadow_cw:
        entry["shadow_cw"] = 1
    else:
        entry.pop("shadow_cw", None)

    if wm.gmjson_emission:
        entry["emission"] = 1
        tex = normalize_path(wm.gmjson_emission_texture).strip()
        if tex:
            entry["emission_texture"] = tex
        else:
            entry.pop("emission_texture", None)
    else:
        entry.pop("emission", None)
        entry.pop("emission_texture", None)

    if _prefs().autosave:
        normalize_models_before_write(models)
        write_json(path, data)


def load_proxy_from_json(context, coll, obj_name):
    scene = context.scene
    path = json_path_for(scene, coll)
    if not path:
        return

    data = read_json(path)
    models = data.get("models", {})
    entry = models.get(obj_name, DEFAULTS)

    wm = context.window_manager
    wm.gmjson_reflection = bool(entry.get("reflection", 0))
    wm.gmjson_alpha = bool(entry.get("alpha", 0))
    wm.gmjson_rma_texture = normalize_path(entry.get("rma_texture", DEFAULTS["rma_texture"]))
    wm.gmjson_normal_texture = normalize_path(entry.get("normal_texture", DEFAULTS["normal_texture"]))
    wm.gmjson_animation_enabled = "animation" in entry
    wm.gmjson_animation_name = entry.get("animation", "")
    wm.gmjson_shadow_cw = bool(entry.get("shadow_cw", 0))
    wm.gmjson_emission = bool(entry.get("emission", 0))
    wm.gmjson_emission_texture = normalize_path(entry.get("emission_texture", ""))
    wm.gmjson_path_preset = entry.get("path_preset", "NONE")


class GMJSON_OT_select_folder(Operator):
    bl_idname = "gmjson.select_folder"
    bl_label = "Select Folder for Collection"
    bl_options = {"REGISTER", "UNDO"}

    directory: StringProperty(subtype="DIR_PATH")

    def invoke(self, context, event):
        if not context.scene.gmjson_settings.collection:
            self.report({"WARNING"}, "No collection selected")
            return {"CANCELLED"}
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        coll = context.scene.gmjson_settings.collection
        folder = self.directory
        if not folder:
            self.report({"WARNING"}, "No folder selected")
            return {"CANCELLED"}

        folder = os.path.abspath(folder)
        set_folder_for_collection(context.scene, coll, folder)
        sync_collection(context.scene, coll, refresh_textures=True, remove_missing=False)

        self.report({"INFO"}, f"Folder set for {coll.name}")
        return {"FINISHED"}


class GMJSON_OT_sync_collection(Operator):
    bl_idname = "gmjson.sync_collection"
    bl_label = "Sync Collection"
    bl_options = {"REGISTER", "UNDO"}

    refresh_textures: BoolProperty(default=False)
    remove_missing: BoolProperty(default=True)

    def execute(self, context):
        coll = context.scene.gmjson_settings.collection
        if not coll:
            self.report({"WARNING"}, "No collection selected")
            return {"CANCELLED"}

        if not json_path_for(context.scene, coll):
            self.report({"WARNING"}, "Select folder for this collection first")
            return {"CANCELLED"}

        removed, err = sync_collection(
            context.scene,
            coll,
            refresh_textures=self.refresh_textures,
            remove_missing=self.remove_missing
        )

        if err:
            self.report({"WARNING"}, err)
            return {"CANCELLED"}

        rebuild_object_list(context)
        self.report({"INFO"}, "Synced" + (f", removed {len(removed)}" if removed else ""))
        return {"FINISHED"}


class GMJSON_OT_save_export(Operator):
    bl_idname = "gmjson.save_export"
    bl_label = "Save/Export"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        coll = scene.gmjson_settings.collection
        if not coll:
            self.report({"WARNING"}, "No collection selected")
            return {"CANCELLED"}

        path = json_path_for(scene, coll)
        if not path:
            self.report({"WARNING"}, "Select folder for this collection first")
            return {"CANCELLED"}

        data = read_json(path)
        if "models" not in data or not isinstance(data["models"], dict):
            data["models"] = {}

        models = data["models"]

        for o in meshes_in_collection(coll):
            ensure_entry(models, o, refresh_textures=False)

        obj_name = context.window_manager.gmjson_proxy_object
        if obj_name:
            entry = models.get(obj_name, dict(DEFAULTS))
            wm = context.window_manager

            entry["reflection"] = 1 if wm.gmjson_reflection else 0
            entry["alpha"] = 1 if wm.gmjson_alpha else 0
            entry["rma_texture"] = normalize_path(wm.gmjson_rma_texture) or DEFAULTS["rma_texture"]
            entry["normal_texture"] = normalize_path(wm.gmjson_normal_texture) or DEFAULTS["normal_texture"]
            entry["path_preset"] = wm.gmjson_path_preset

            if wm.gmjson_animation_enabled and wm.gmjson_animation_name.strip():
                entry["animation"] = wm.gmjson_animation_name.strip()
            else:
                entry.pop("animation", None)

            if wm.gmjson_shadow_cw:
                entry["shadow_cw"] = 1
            else:
                entry.pop("shadow_cw", None)

            if wm.gmjson_emission:
                entry["emission"] = 1
                tex = normalize_path(wm.gmjson_emission_texture).strip()
                if tex:
                    entry["emission_texture"] = tex
                else:
                    entry.pop("emission_texture", None)
            else:
                entry.pop("emission", None)
                entry.pop("emission_texture", None)

            models[obj_name] = entry

        normalize_models_before_write(models)
        write_json(path, data)
        self.report({"INFO"}, f"Saved: {os.path.basename(path)}")
        return {"FINISHED"}


class GMJSON_OT_refresh_textures_active(Operator):
    bl_idname = "gmjson.refresh_textures_active"
    bl_label = "Refresh Textures"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        coll = context.scene.gmjson_settings.collection
        if not coll:
            return {"CANCELLED"}

        obj_name = context.window_manager.gmjson_proxy_object
        if not obj_name:
            self.report({"WARNING"}, "No active object selected in list")
            return {"CANCELLED"}

        obj = bpy.data.objects.get(obj_name)
        if not obj:
            self.report({"WARNING"}, "Object not found. Sync list.")
            return {"CANCELLED"}

        preset_name = context.window_manager.gmjson_path_preset
        rma, nom, emission = detect_textures_from_object(obj, preset_name)
        wm = context.window_manager

        if rma:
            wm.gmjson_rma_texture = normalize_path(rma)
        if nom:
            wm.gmjson_normal_texture = normalize_path(nom)
        if wm.gmjson_emission and emission:
            wm.gmjson_emission_texture = normalize_path(emission)

        if (not rma) and (not nom) and (not emission):
            self.report({"WARNING"}, "No '_RMA' / '_nom' / '_Emission' textures found (by IMAGE NAME).")

        return {"FINISHED"}


class GMJSON_OT_reset_defaults_active(Operator):
    bl_idname = "gmjson.reset_defaults_active"
    bl_label = "Reset Defaults"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        wm = context.window_manager
        wm.gmjson_reflection = False
        wm.gmjson_alpha = False
        wm.gmjson_rma_texture = DEFAULTS["rma_texture"]
        wm.gmjson_normal_texture = DEFAULTS["normal_texture"]
        wm.gmjson_animation_enabled = False
        wm.gmjson_animation_name = ""
        wm.gmjson_shadow_cw = False
        wm.gmjson_emission = False
        wm.gmjson_emission_texture = ""
        wm.gmjson_path_preset = "NONE"
        return {"FINISHED"}


class GMJSON_OT_focus_from_viewport(Operator):
    bl_idname = "gmjson.focus_from_viewport"
    bl_label = "Focus from Viewport Selection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sync_active_object_from_viewport(context)
        return {"FINISHED"}


class GMJSON_OT_apply_checkboxes_to_selected(Operator):
    bl_idname = "gmjson.apply_checkboxes_to_selected"
    bl_label = "Apply Checkbox Values to Selected"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        coll = scene.gmjson_settings.collection
        wm = context.window_manager

        if not coll:
            self.report({"WARNING"}, "No collection selected")
            return {"CANCELLED"}

        path = json_path_for(scene, coll)
        if not path:
            self.report({"WARNING"}, "Select folder for this collection first")
            return {"CANCELLED"}

        targets = selected_meshes_in_collection(context, coll)
        if not targets:
            self.report({"WARNING"}, "No selected mesh objects from current collection")
            return {"CANCELLED"}

        data = read_json(path)
        if "models" not in data or not isinstance(data["models"], dict):
            data["models"] = {}

        models = data["models"]

        for obj in targets:
            ensure_entry(models, obj, refresh_textures=False)
            entry = models[obj.name]

            entry["reflection"] = 1 if wm.gmjson_batch_reflection else 0
            entry["alpha"] = 1 if wm.gmjson_batch_alpha else 0

            if wm.gmjson_batch_shadow_cw:
                entry["shadow_cw"] = 1
            else:
                entry.pop("shadow_cw", None)

            if wm.gmjson_batch_emission:
                entry["emission"] = 1
                current_tex = normalize_path(entry.get("emission_texture", "")).strip()
                if not current_tex:
                    preset_name = entry.get("path_preset", "NONE")
                    _rma, _nom, em_tex = detect_textures_from_object(obj, preset_name)
                    if em_tex:
                        entry["emission_texture"] = normalize_path(em_tex)
            else:
                entry.pop("emission", None)
                entry.pop("emission_texture", None)

        normalize_models_before_write(models)
        write_json(path, data)

        self.report({"INFO"}, f"Applied checkbox values to {len(targets)} object(s)")
        return {"FINISHED"}


class GMJSON_OT_apply_path_preset_to_selected(Operator):
    bl_idname = "gmjson.apply_path_preset_to_selected"
    bl_label = "Apply Path Preset to Selected"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        coll = scene.gmjson_settings.collection
        wm = context.window_manager

        if not coll:
            self.report({"WARNING"}, "No collection selected")
            return {"CANCELLED"}

        path = json_path_for(scene, coll)
        if not path:
            self.report({"WARNING"}, "Select folder for this collection first")
            return {"CANCELLED"}

        targets = selected_meshes_in_collection(context, coll)
        if not targets:
            self.report({"WARNING"}, "No selected mesh objects from current collection")
            return {"CANCELLED"}

        data = read_json(path)
        if "models" not in data or not isinstance(data["models"], dict):
            data["models"] = {}

        models = data["models"]

        for obj in targets:
            ensure_entry(models, obj, refresh_textures=False)
            entry = models[obj.name]
            entry["path_preset"] = wm.gmjson_path_preset

            rma, nom, emission = detect_textures_from_object(obj, wm.gmjson_path_preset)

            if rma:
                entry["rma_texture"] = normalize_path(rma)
            if nom:
                entry["normal_texture"] = normalize_path(nom)

            if entry.get("emission", 0) == 1 and emission:
                entry["emission_texture"] = normalize_path(emission)

        normalize_models_before_write(models)
        write_json(path, data)

        self.report({"INFO"}, f"Applied path preset to {len(targets)} object(s)")
        return {"FINISHED"}


def rebuild_object_list(context):
    scene = context.scene
    settings = scene.gmjson_settings
    scene.gmjson_objects.clear()

    if not settings.collection:
        settings.active_index = -1
        return

    for o in sorted(meshes_in_collection(settings.collection), key=lambda x: x.name.lower()):
        it = scene.gmjson_objects.add()
        it.name = o.name

    settings.active_index = min(settings.active_index, len(scene.gmjson_objects) - 1) if scene.gmjson_objects else -1


class GMJSON_UL_objects(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name, icon="MESH_CUBE")


class GMJSON_PT_panel(Panel):
    bl_label = "GM JSON"
    bl_idname = "GMJSON_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "GM JSON"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.gmjson_settings
        wm = context.window_manager

        layout.prop(settings, "collection", text="Collection")

        if not settings.collection:
            layout.label(text="Choose a collection.", icon="INFO")
            return

        coll = settings.collection
        folder = get_folder_for_collection(scene, coll)

        row = layout.row(align=True)
        if folder:
            row.label(text=folder, icon="FOLDER_REDIRECT")
            row.operator("gmjson.select_folder", text="", icon="FILE_FOLDER")
        else:
            row.label(text="Select folder to start", icon="ERROR")
            row.operator("gmjson.select_folder", text="Select Folder", icon="FILE_FOLDER")

        col = layout.column()
        col.enabled = bool(folder)

        dups = find_duplicate_names_in_collection(coll)
        if dups:
            box = col.box()
            box.label(text="Duplicate mesh names in collection!", icon="ERROR")
            box.label(text=", ".join(dups[:6]) + (" ..." if len(dups) > 6 else ""))

        col.operator("gmjson.sync_collection", text="Sync (Add Defaults)", icon="FILE_REFRESH").refresh_textures = False
        op = col.operator("gmjson.sync_collection", text="Sync + Refresh Textures", icon="TEXTURE")
        op.refresh_textures = True
        op.remove_missing = True

        col.template_list("GMJSON_UL_objects", "", scene, "gmjson_objects", settings, "active_index", rows=8)

        row_focus = col.row(align=True)
        row_focus.prop(wm, "gmjson_viewport_auto_selection", text="Viewport Auto Selection")
        row_focus.operator("gmjson.focus_from_viewport", text="", icon="RESTRICT_SELECT_OFF")

        col.separator()
        col.prop(_prefs(), "autosave", text="Autosave (global)")
        col.operator("gmjson.save_export", icon="FILE_TICK")

        if settings.active_index >= 0 and settings.active_index < len(scene.gmjson_objects):
            obj_name = scene.gmjson_objects[settings.active_index].name
            obj = bpy.data.objects.get(obj_name)

            box = col.box()
            box.label(text=f"Object: {obj_name}", icon="OBJECT_DATA")

            if obj and len(obj.material_slots) > 1:
                box.label(text=f"Warning: {len(obj.material_slots)} materials (using slot 0)", icon="INFO")

            box.prop(wm, "gmjson_path_preset", text="Path Preset")

            box.prop(wm, "gmjson_reflection", text="Reflection")
            box.prop(wm, "gmjson_alpha", text="Alpha")
            box.prop(wm, "gmjson_rma_texture", text="RMA")
            box.prop(wm, "gmjson_normal_texture", text="Normal")

            box.separator()
            box.prop(wm, "gmjson_animation_enabled", text="Animation")
            row_anim = box.row()
            row_anim.enabled = wm.gmjson_animation_enabled
            row_anim.prop(wm, "gmjson_animation_name", text="Animation Name")

            box.prop(wm, "gmjson_shadow_cw", text="Shadow CW")

            box.separator()
            box.prop(wm, "gmjson_emission", text="Emission")
            row_em = box.row()
            row_em.enabled = wm.gmjson_emission
            row_em.prop(wm, "gmjson_emission_texture", text="Emission Texture")

            rowb = box.row(align=True)
            rowb.operator("gmjson.refresh_textures_active", text="Refresh Textures", icon="TEXTURE")
            rowb.operator("gmjson.reset_defaults_active", text="Reset Defaults", icon="LOOP_BACK")

        batch_box = col.box()
        batch_box.label(text="Apply to Selected", icon="CHECKBOX_HLT")

        status_ref = batch_flag_status(context, coll, "reflection")
        row = batch_box.row(align=True)
        row.prop(wm, "gmjson_batch_reflection", text="Reflection")
        row.label(text=f"Status: {status_ref}")

        status_alpha = batch_flag_status(context, coll, "alpha")
        row = batch_box.row(align=True)
        row.prop(wm, "gmjson_batch_alpha", text="Alpha")
        row.label(text=f"Status: {status_alpha}")

        status_shadow = batch_flag_status(context, coll, "shadow_cw")
        row = batch_box.row(align=True)
        row.prop(wm, "gmjson_batch_shadow_cw", text="Shadow CW")
        row.label(text=f"Status: {status_shadow}")

        status_em = batch_flag_status(context, coll, "emission")
        row = batch_box.row(align=True)
        row.prop(wm, "gmjson_batch_emission", text="Emission")
        row.label(text=f"Status: {status_em}")

        batch_box.operator("gmjson.apply_checkboxes_to_selected", icon="CHECKMARK")

        preset_box = col.box()
        preset_box.label(text="Path Preset Tools", icon="FILE_FOLDER")
        preset_box.prop(wm, "gmjson_path_preset", text="Preset")
        preset_box.operator("gmjson.apply_path_preset_to_selected", icon="CHECKMARK")


classes = (
    GMJSON_ObjectItem,
    GMJSON_Settings,
    GMJSON_AddonPreferences,
    GMJSON_OT_select_folder,
    GMJSON_OT_sync_collection,
    GMJSON_OT_save_export,
    GMJSON_OT_refresh_textures_active,
    GMJSON_OT_reset_defaults_active,
    GMJSON_OT_focus_from_viewport,
    GMJSON_OT_apply_checkboxes_to_selected,
    GMJSON_OT_apply_path_preset_to_selected,
    GMJSON_UL_objects,
    GMJSON_PT_panel,
)


_TIMER_REGISTERED = False


def _gmjson_viewport_timer():
    try:
        ctx = bpy.context
        wm = getattr(ctx, "window_manager", None)
        if not wm:
            return 0.35

        if getattr(wm, "gmjson_viewport_auto_selection", False):
            scene = getattr(ctx, "scene", None)
            if scene and hasattr(scene, "gmjson_settings"):
                sync_active_object_from_viewport(ctx)
    except Exception:
        pass

    return 0.35


def register():
    global _TIMER_REGISTERED

    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.gmjson_settings = PointerProperty(type=GMJSON_Settings)
    bpy.types.Scene.gmjson_objects = CollectionProperty(type=GMJSON_ObjectItem)

    bpy.types.WindowManager.gmjson_proxy_object = StringProperty(default="")
    bpy.types.WindowManager.gmjson_reflection = BoolProperty(default=False, update=_proxy_update)
    bpy.types.WindowManager.gmjson_alpha = BoolProperty(default=False, update=_proxy_update)
    bpy.types.WindowManager.gmjson_rma_texture = StringProperty(default=DEFAULTS["rma_texture"], update=_proxy_update)
    bpy.types.WindowManager.gmjson_normal_texture = StringProperty(default=DEFAULTS["normal_texture"], update=_proxy_update)

    bpy.types.WindowManager.gmjson_animation_enabled = BoolProperty(default=False, update=_proxy_update)
    bpy.types.WindowManager.gmjson_animation_name = StringProperty(default="", update=_proxy_update)
    bpy.types.WindowManager.gmjson_shadow_cw = BoolProperty(default=False, update=_proxy_update)
    bpy.types.WindowManager.gmjson_emission = BoolProperty(default=False, update=_on_emission_toggle)
    bpy.types.WindowManager.gmjson_emission_texture = StringProperty(default="", update=_proxy_update)
    bpy.types.WindowManager.gmjson_path_preset = EnumProperty(
        name="Path Preset",
        items=PATH_PRESET_ITEMS,
        default="NONE",
        update=_proxy_update,
    )

    bpy.types.WindowManager.gmjson_batch_reflection = BoolProperty(default=False)
    bpy.types.WindowManager.gmjson_batch_alpha = BoolProperty(default=False)
    bpy.types.WindowManager.gmjson_batch_shadow_cw = BoolProperty(default=False)
    bpy.types.WindowManager.gmjson_batch_emission = BoolProperty(default=False)
    bpy.types.WindowManager.gmjson_viewport_auto_selection = BoolProperty(default=False)

    def _deferred_init():
        try:
            rebuild_object_list(bpy.context)
        except Exception:
            pass
        return None

    try:
        bpy.app.timers.register(_deferred_init, first_interval=0.1)
    except Exception:
        pass

    if not _TIMER_REGISTERED:
        try:
            bpy.app.timers.register(_gmjson_viewport_timer, first_interval=0.35)
            _TIMER_REGISTERED = True
        except Exception:
            pass


def unregister():
    global _TIMER_REGISTERED

    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.gmjson_settings
    del bpy.types.Scene.gmjson_objects

    del bpy.types.WindowManager.gmjson_proxy_object
    del bpy.types.WindowManager.gmjson_reflection
    del bpy.types.WindowManager.gmjson_alpha
    del bpy.types.WindowManager.gmjson_rma_texture
    del bpy.types.WindowManager.gmjson_normal_texture
    del bpy.types.WindowManager.gmjson_animation_enabled
    del bpy.types.WindowManager.gmjson_animation_name
    del bpy.types.WindowManager.gmjson_shadow_cw
    del bpy.types.WindowManager.gmjson_emission
    del bpy.types.WindowManager.gmjson_emission_texture
    del bpy.types.WindowManager.gmjson_path_preset

    del bpy.types.WindowManager.gmjson_batch_reflection
    del bpy.types.WindowManager.gmjson_batch_alpha
    del bpy.types.WindowManager.gmjson_batch_shadow_cw
    del bpy.types.WindowManager.gmjson_batch_emission
    del bpy.types.WindowManager.gmjson_viewport_auto_selection

    _TIMER_REGISTERED = False


if __name__ == "__main__":
    register()