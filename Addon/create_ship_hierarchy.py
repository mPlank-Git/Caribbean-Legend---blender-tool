bl_info = {
    "name": "Create Ship Hierarchy",
    "author": "mPlank",
    "version": (1, 9, 2),
    "blender": (3, 6, 0),
    "location": "3D Viewport > N-Panel > Create Ship",
    "description": "Структура корабля: root+дети, каноны, свет, fireplace, flares, geometry-группы, мачты; безопасное удаление; сервисные камеры; поворот детей geometry (90,0,90). Исправлено дублирование root/детей, добавлены poll и нормализация scale=1.",
    "category": "Object",
}

import bpy
import re
from math import radians

# ---------------------------------
# Константы и шаблоны имён/регексы
# ---------------------------------

EMPTY_NAMES = [
    "geometry",
    "Camera",
    "cannonb",
    "cannonf",
    "cannonl",
    "cannonr",
    "fireplace",
    "lights",
    "waterline",
    "flares",
]

# Cannons
CANNON_KEYS = ["cannonb", "cannonf", "cannonl", "cannonr"]
CANNON_CHILD_ROT_DEG = {
    "cannonb": (90.0, 0.0, -90.0),
    "cannonf": (90.0, 0.0,  90.0),
    "cannonl": (90.0, 0.0,   0.0),
    "cannonr": (90.0, 0.0, 180.0),
}
_cannon_child_re = re.compile(r"^_(\d+)$")

# Lights / Fireplace
_light_child_re      = re.compile(r"^l(\d{3})$")
_fireplace_child_re  = re.compile(r"^locator(\d{3})$")

# Geometry
_parts_empty_re     = re.compile(r"^parts(\d+)$")
_shatter_empty_re   = re.compile(r"^shatter(\d+)$")
STATIC_GROUPS = ["path", "wind", "watermask", "fonar_day", "fonar_night", "shatter1_baller"]

# Rotation for any child of 'geometry'
GEOM_CHILD_ROT_DEG = (90.0, 0.0, 90.0)

# -------------
# Вспомогалки
# -------------

def sanitize(name: str) -> str:
    import re as _re
    safe = _re.sub(r"[^A-Za-z0-9_\-]+", "_", name.strip())
    safe = _re.sub(r"_+", "_", safe).strip("_")
    return safe or "Ship"

def scene_root_collection():
    return bpy.context.scene.collection

def link_collection_to_scene(col: bpy.types.Collection):
    root = scene_root_collection()
    if col.name not in [c.name for c in root.children]:
        root.children.link(col)

def ensure_collection(ship_name: str) -> bpy.types.Collection:
    root = scene_root_collection()
    if ship_name in bpy.data.collections:
        col = bpy.data.collections[ship_name]
        if col.name not in [c.name for c in root.children]:
            root.children.link(col)
        return col
    col = bpy.data.collections.new(ship_name)
    root.children.link(col)
    return col

def unlink_collection_everywhere(col: bpy.types.Collection):
    for parent in list(bpy.data.collections):
        if col in parent.children:
            parent.children.unlink(col)
    root = scene_root_collection()
    if col in root.children:
        root.children.unlink(col)

def is_collection_empty(col: bpy.types.Collection) -> bool:
    if col.objects:
        return False
    for child in col.children:
        if not is_collection_empty(child):
            return False
    return True

def create_empty(name: str, collection: bpy.types.Collection, parent=None):
    """Создание EMPTY (сразу scale=1) без защиты от суффиксов. Для служебных имён лучше get_or_make_empty_exact()."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = 0.6
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_mode = 'XYZ'
    obj.scale = (1.0, 1.0, 1.0)
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    collection.objects.link(obj)
    return obj

def find_in_collection(collection: bpy.types.Collection, name: str):
    for obj in collection.objects:
        if obj.name == name:
            return obj
    return None

def find_named_or_suffixed_empty_in_collection(collection: bpy.types.Collection, base_name: str):
    """Ищет EMPTY с именем base_name или base_name.### именно В ЭТОЙ коллекции."""
    for obj in collection.objects:
        if obj.type == 'EMPTY' and obj.name == base_name:
            return obj
    prefix = base_name + "."
    for obj in collection.objects:
        if obj.type == 'EMPTY' and obj.name.startswith(prefix):
            tail = obj.name[len(prefix):]
            if tail.isdigit():
                return obj
    return None

def get_or_make_empty_exact(collection: bpy.types.Collection, base_name: str, parent=None):
    """Гарантирует EMPTY с ИМЕНЕМ base_name в данной коллекции (без суффиксов, если возможно)."""
    obj = find_named_or_suffixed_empty_in_collection(collection, base_name)
    if obj is None:
        obj = bpy.data.objects.new(base_name, None)
        obj.empty_display_type = 'PLAIN_AXES'
        obj.empty_display_size = 0.6
        collection.objects.link(obj)

    # Постараемся вернуть точное имя без суффикса
    if obj.name != base_name:
        if bpy.data.objects.get(base_name) is None:
            try:
                obj.name = base_name
            except Exception:
                pass

    # Нормализация трансформов и родитель
    obj.location = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = (0.0, 0.0, 0.0)
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj

def normalize_empty(obj: bpy.types.Object):
    obj.location = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    obj.rotation_mode = 'XYZ'

def set_geom_child_rotation(obj: bpy.types.Object):
    rx, ry, rz = map(radians, GEOM_CHILD_ROT_DEG)
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = (rx, ry, rz)
    obj.scale = (1.0, 1.0, 1.0)

def ensure_root_and_children(ship_col: bpy.types.Collection):
    """Безопасно гарантирует: root и все EMPTY_NAMES как дети root, без дубликатов и с нормализованными трансформами."""
    root = get_or_make_empty_exact(ship_col, "root", None)
    for name in EMPTY_NAMES:
        child = get_or_make_empty_exact(ship_col, name, root)
        child.rotation_euler = (0.0, 0.0, 0.0)
        child.scale = (1.0, 1.0, 1.0)
    return root

# Cannons helpers

def clear_cannon_children(parent_obj: bpy.types.Object):
    to_delete = [ch for ch in list(parent_obj.children)
                 if ch.type == 'EMPTY' and _cannon_child_re.match(ch.name)]
    for obj in to_delete:
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        bpy.data.objects.remove(obj)

def ensure_cannon_parents(ship_col: bpy.types.Collection):
    result = {}
    root = get_or_make_empty_exact(ship_col, "root", None)
    for key in CANNON_KEYS:
        obj = get_or_make_empty_exact(ship_col, key, root)
        result[key] = obj
    return result

def set_child_orientation_for_group(child_obj: bpy.types.Object, group_key: str):
    deg = CANNON_CHILD_ROT_DEG.get(group_key, (0.0, 0.0, 0.0))
    rx, ry, rz = map(radians, deg)
    child_obj.rotation_mode = 'XYZ'
    child_obj.rotation_euler = (rx, ry, rz)
    child_obj.scale = (1.0, 1.0, 1.0)

# Generic clear by regex

def clear_children_regex(parent_obj: bpy.types.Object, regex: re.Pattern):
    to_delete = [ch for ch in list(parent_obj.children)
                 if ch.type == 'EMPTY' and regex.match(ch.name)]
    for obj in to_delete:
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        bpy.data.objects.remove(obj)

# Geometry helpers

def ensure_geometry_parent(ship_col: bpy.types.Collection):
    root = ensure_root_and_children(ship_col)
    geom = get_or_make_empty_exact(ship_col, "geometry", root)
    return geom

def clear_geometry_children_by_regex(geom_obj: bpy.types.Object, regex: re.Pattern):
    to_delete = [ch for ch in list(geom_obj.children)
                 if ch.type == 'EMPTY' and regex.match(ch.name)]
    for obj in to_delete:
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        bpy.data.objects.remove(obj)

def enforce_rotation_on_all_geom_children(geom_obj: bpy.types.Object):
    for ch in geom_obj.children:
        if ch.type == 'EMPTY':
            set_geom_child_rotation(ch)

# ----------------
# Свойства (UI)
# ----------------

class CSH_Props(bpy.types.PropertyGroup):
    ship_name: bpy.props.StringProperty(name="Ship Name", default="MyShip")

    # Foldouts
    show_ship_base: bpy.props.BoolProperty(name="Ship Base", default=True)
    show_cannons: bpy.props.BoolProperty(name="Cannons", default=False)
    show_lights: bpy.props.BoolProperty(name="Lights", default=False)
    show_flares: bpy.props.BoolProperty(name="Flares", default=False)
    show_fireplace: bpy.props.BoolProperty(name="Fireplace", default=False)
    show_geometry: bpy.props.BoolProperty(name="Geometry / Groups", default=False)
    show_mast: bpy.props.BoolProperty(name="Mast", default=False)

    # Cannons
    cannonb_count: bpy.props.IntProperty(name="cannonb", description="Количество пушек (back)", default=0, min=0)
    cannonf_count: bpy.props.IntProperty(name="cannonf", description="Количество пушек (front)", default=0, min=0)
    cannonl_count: bpy.props.IntProperty(name="cannonl", description="Количество пушек (left)", default=0, min=0)
    cannonr_count: bpy.props.IntProperty(name="cannonr", description="Количество пушек (right)", default=0, min=0)

    # Lights
    lights_count: bpy.props.IntProperty(name="lights", description="Количество источников света (l001..)", default=0, min=0)

    # Flares
    flares_type: bpy.props.EnumProperty(
        name="type",
        description="Тип префикса имени (f или fm)",
        items=[('f', "f", "f"), ('fm', "fm", "fm")],
        default='fm'
    )
    flares_mast: bpy.props.IntProperty(
        name="mast",
        description="Номер мачты (однозначное число)",
        default=1, min=0, max=9
    )

    # Fireplace
    fireplace_count: bpy.props.IntProperty(name="fireplace", description="Количество локаторов fireplace (locator001..)", default=0, min=0)

    # Geometry counts
    parts_count: bpy.props.IntProperty(name="parts", description="Количество коллекций Ship_parts# и указателей parts#", default=0, min=0)
    shatter_count: bpy.props.IntProperty(name="shatter", description="Количество коллекций Ship_shatter# и указателей shatter#", default=0, min=0)

    # Static geometry groups
    make_path: bpy.props.BoolProperty(name="path", default=False)
    make_wind: bpy.props.BoolProperty(name="wind", default=False)
    make_watermask: bpy.props.BoolProperty(name="watermask", default=False)
    make_fonar_day: bpy.props.BoolProperty(name="fonar_day", default=False)
    make_fonar_night: bpy.props.BoolProperty(name="fonar_night", default=False)
    make_shatter1_baller: bpy.props.BoolProperty(name="shatter1_baller", default=False)

    # Mast controls
    mast_number: bpy.props.IntProperty(
        name="Mast #",
        description="Номер мачты для создания коллекции <Ship>_mast# и указателя в geometry",
        default=1, min=0, max=9
    )

# --------------
# Операторы (с poll)
# --------------

class CSH_OT_Create(bpy.types.Operator):
    """Создать коллекцию и пустышки; добавить camera под waterline; cam_* под Camera"""
    bl_idname = "csh.create_ship"
    bl_label = "Create Ship"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def _ensure_camera_childs(self, ship_col: bpy.types.Collection):
        cam_parent = find_in_collection(ship_col, "Camera")
        if cam_parent is None:
            return
        wanted = {
            "cam_b": (90.0, 0.0, -90.0),
            "cam_f": (90.0, 0.0,  90.0),
            "cam_r": (90.0, 0.0, 180.0),
            "cam_l": (90.0, 0.0,   0.0),
        }
        for name, deg in wanted.items():
            obj = next((ch for ch in cam_parent.children if ch.type == 'EMPTY' and ch.name == name), None)
            if obj is None:
                obj = get_or_make_empty_exact(ship_col, name, cam_parent)
            else:
                obj.parent = cam_parent
                obj.matrix_parent_inverse = cam_parent.matrix_world.inverted()
                normalize_empty(obj)
            rx, ry, rz = map(radians, deg)
            obj.rotation_euler = (rx, ry, rz)

    def _ensure_waterline_camera(self, ship_col: bpy.types.Collection):
        water = find_in_collection(ship_col, "waterline")
        if water is None:
            return
        cam = next((ch for ch in water.children if ch.type == 'EMPTY' and ch.name == "camera"), None)
        if cam is None:
            cam = get_or_make_empty_exact(ship_col, "camera", water)
        else:
            cam.parent = water
            cam.matrix_parent_inverse = water.matrix_world.inverted()
            normalize_empty(cam)

    def execute(self, context):
        props = context.scene.csh_props
        ship_name = sanitize(props.ship_name)
        if not ship_name:
            self.report({'ERROR'}, "Введите имя корабля.")
            return {'CANCELLED'}

        ship_col = ensure_collection(ship_name)
        root_obj = ensure_root_and_children(ship_col)
        self._ensure_waterline_camera(ship_col)
        self._ensure_camera_childs(ship_col)

        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        root_obj.select_set(True)
        bpy.context.view_layer.objects.active = root_obj

        self.report({'INFO'}, f"Корабль '{ship_name}' создан/обновлён.")
        return {'FINISHED'}

class CSH_OT_ApplyCannons(bpy.types.Operator):
    """Создать/пересоздать локаторы пушек (_1.._N) с ориентацией по группам"""
    bl_idname = "csh.apply_cannons"
    bl_label = "Apply Cannon Layout"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        props = context.scene.csh_props
        ship_name = sanitize(props.ship_name)
        if not ship_name:
            self.report({'ERROR'}, "Введите имя корабля.")
            return {'CANCELLED'}

        ship_col = ensure_collection(ship_name)
        parents = ensure_cannon_parents(ship_col)

        for key in CANNON_KEYS:
            clear_cannon_children(parents[key])

        counts = {
            "cannonb": max(0, int(props.cannonb_count)),
            "cannonf": max(0, int(props.cannonf_count)),
            "cannonl": max(0, int(props.cannonl_count)),
            "cannonr": max(0, int(props.cannonr_count)),
        }

        current_idx = 1
        total = sum(counts.values())

        for key in CANNON_KEYS:
            parent = parents[key]
            for _ in range(counts[key]):
                name = f"_{current_idx}"
                child = create_empty(name, ship_col, parent)
                normalize_empty(child)
                set_child_orientation_for_group(child, key)
                current_idx += 1

        self.report({'INFO'}, f"Создано {total} локаторов пушек.")
        return {'FINISHED'}

class CSH_OT_ApplyLights(bpy.types.Operator):
    """Создать/пересоздать l001.. под 'lights'"""
    bl_idname = "csh.apply_lights"
    bl_label = "Apply Lights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        props = context.scene.csh_props
        ship_name = sanitize(props.ship_name)
        if not ship_name:
            self.report({'ERROR'}, "Введите имя корабля.")
            return {'CANCELLED'}
        ship_col = ensure_collection(ship_name)
        ensure_root_and_children(ship_col)

        lights_parent = find_in_collection(ship_col, "lights")
        if lights_parent is None:
            self.report({'ERROR'}, "Не найдена пустышка 'lights'. Сначала нажмите 'Create Ship'.")
            return {'CANCELLED'}

        clear_children_regex(lights_parent, _light_child_re)
        count = max(0, int(props.lights_count))
        for i in range(1, count + 1):
            name = f"l{str(i).zfill(3)}"
            child = create_empty(name, ship_col, lights_parent)
            normalize_empty(child)
            child.rotation_euler = (0.0, 0.0, 0.0)

        self.report({'INFO'}, f"Создано {count} локаторов света (l001..).")
        return {'FINISHED'}

class CSH_OT_AddFlare(bpy.types.Operator):
    """Добавить один локатор вспышки внутри 'flares' с авто-нумерацией по маске: f|fm + (mast) + NNN"""
    bl_idname = "csh.add_flare"
    bl_label = "Add Flare"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        props = context.scene.csh_props
        ship_name = sanitize(props.ship_name)
        if not ship_name:
            self.report({'ERROR'}, "Введите имя корабля.")
            return {'CANCELLED'}
        ship_col = ensure_collection(ship_name)
        root = ensure_root_and_children(ship_col)

        flares_parent = find_in_collection(ship_col, "flares")
        if flares_parent is None:
            flares_parent = get_or_make_empty_exact(ship_col, "flares", root)
        else:
            flares_parent.parent = root
            flares_parent.matrix_parent_inverse = root.matrix_world.inverted()
            normalize_empty(flares_parent)

        prefix = props.flares_type  # 'f' или 'fm'
        mast = int(props.flares_mast)
        pattern = re.compile(rf"^{re.escape(prefix)}{mast}(\d{{3}})$")

        max_idx = 0
        for ch in flares_parent.children:
            if ch.type != 'EMPTY':
                continue
            m = pattern.match(ch.name)
            if m:
                try:
                    idx = int(m.group(1))
                    if idx > max_idx:
                        max_idx = idx
                except ValueError:
                    pass

        next_idx = max_idx + 1
        if next_idx > 999:
            self.report({'ERROR'}, "Достигнут лимит 999 для данного типа и мачты.")
            return {'CANCELLED'}

        new_name = f"{prefix}{mast}{str(next_idx).zfill(3)}"
        child = create_empty(new_name, ship_col, flares_parent)
        normalize_empty(child)
        child.rotation_euler = (0.0, 0.0, 0.0)

        self.report({'INFO'}, f"Добавлен flare: {new_name}")
        return {'FINISHED'}

class CSH_OT_ApplyFireplace(bpy.types.Operator):
    """Создать/пересоздать locator001.. под 'fireplace'"""
    bl_idname = "csh.apply_fireplace"
    bl_label = "Apply Fireplace"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        props = context.scene.csh_props
        ship_name = sanitize(props.ship_name)
        if not ship_name:
            self.report({'ERROR'}, "Введите имя корабля.")
            return {'CANCELLED'}
        ship_col = ensure_collection(ship_name)
        ensure_root_and_children(ship_col)

        parent = find_in_collection(ship_col, "fireplace")
        if parent is None:
            self.report({'ERROR'}, "Не найдена пустышка 'fireplace'. Сначала нажмите 'Create Ship'.")
            return {'CANCELLED'}

        clear_children_regex(parent, _fireplace_child_re)
        count = max(0, int(props.fireplace_count))
        for i in range(1, count + 1):
            name = f"locator{str(i).zfill(3)}"
            child = create_empty(name, ship_col, parent)
            normalize_empty(child)
            child.rotation_euler = (0.0, 0.0, 0.0)

        self.report({'INFO'}, f"Создано {count} локаторов fireplace (locator001..).")
        return {'FINISHED'}

class CSH_OT_ApplyGeometryGroups(bpy.types.Operator):
    """Parts/Shatter/Static: создаёт указатели под 'geometry', коллекции с root; удаляет лишние parts/shatter если пустые; всем детям geometry ставит (90,0,90)"""
    bl_idname = "csh.apply_geometry_groups"
    bl_label = "Apply Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def _ensure_static_group(self, ship_name: str, ship_col, geom, group_name: str):
        col_name = f"{ship_name}_{group_name}"
        # коллекция
        if col_name in bpy.data.collections:
            col = bpy.data.collections[col_name]
            link_collection_to_scene(col)
        else:
            col = bpy.data.collections.new(col_name)
            link_collection_to_scene(col)
            if find_in_collection(col, "root") is None:
                create_empty("root", col, None)
        # указатель в geometry
        exists = next((ch for ch in geom.children if ch.type == 'EMPTY' and ch.name == group_name), None)
        if not exists:
            child = create_empty(group_name, ship_col, geom)
            normalize_empty(child)
            set_geom_child_rotation(child)
        else:
            set_geom_child_rotation(exists)

    def _safe_delete_extra_numbered(self, ship_name: str, prefix: str, keep_n: int):
        pattern = re.compile(rf"^{re.escape(ship_name)}_{re.escape(prefix)}(\d+)$")
        deleted, skipped = 0, []
        for col in list(bpy.data.collections):
            m = pattern.match(col.name)
            if not m:
                continue
            idx = int(m.group(1))
            if idx <= keep_n:
                continue
            if is_collection_empty(col):
                unlink_collection_everywhere(col)
                try:
                    bpy.data.collections.remove(col)
                    deleted += 1
                except RuntimeError:
                    skipped.append(col.name)
            else:
                skipped.append(col.name)
        return deleted, skipped

    def execute(self, context):
        props = context.scene.csh_props
        ship_name = sanitize(props.ship_name)
        if not ship_name:
            self.report({'ERROR'}, "Введите имя корабля.")
            return {'CANCELLED'}

        ship_col = ensure_collection(ship_name)
        geom = ensure_geometry_parent(ship_col)

        # -------- parts --------
        clear_geometry_children_by_regex(geom, _parts_empty_re)
        parts_n = max(0, int(props.parts_count))
        for i in range(1, parts_n + 1):
            child = create_empty(f"parts{i}", ship_col, geom)
            normalize_empty(child)
            set_geom_child_rotation(child)
        for i in range(1, parts_n + 1):
            col_name = f"{ship_name}_parts{i}"
            if col_name in bpy.data.collections:
                link_collection_to_scene(bpy.data.collections[col_name])
            else:
                new_col = bpy.data.collections.new(col_name)
                link_collection_to_scene(new_col)
                if find_in_collection(new_col, "root") is None:
                    create_empty("root", new_col, None)
        del_parts, skip_parts = self._safe_delete_extra_numbered(ship_name, "parts", parts_n)

        # -------- shatter --------
        clear_geometry_children_by_regex(geom, _shatter_empty_re)
        sh_n = max(0, int(props.shatter_count))
        for i in range(1, sh_n + 1):
            child = create_empty(f"shatter{i}", ship_col, geom)
            normalize_empty(child)
            set_geom_child_rotation(child)
        for i in range(1, sh_n + 1):
            col_name = f"{ship_name}_shatter{i}"
            if col_name in bpy.data.collections:
                link_collection_to_scene(bpy.data.collections[col_name])
            else:
                new_col = bpy.data.collections.new(col_name)
                link_collection_to_scene(new_col)
                if find_in_collection(new_col, "root") is None:
                    create_empty("root", new_col, None)
        del_sh, skip_sh = self._safe_delete_extra_numbered(ship_name, "shatter", sh_n)

        # -------- static groups --------
        static_flags = {
            "path": props.make_path,
            "wind": props.make_wind,
            "watermask": props.make_watermask,
            "fonar_day": props.make_fonar_day,
            "fonar_night": props.make_fonar_night,
            "shatter1_baller": props.make_shatter1_baller,
        }
        created_static = []
        for gname, enabled in static_flags.items():
            if enabled:
                self._ensure_static_group(ship_name, ship_col, geom, gname)
                created_static.append(gname)

        # Принудительно выровнять поворот всем детям geometry
        enforce_rotation_on_all_geom_children(geom)

        parts_info = f"parts={parts_n} (удалено пустых: {del_parts}" + (f", пропущены: {', '.join(skip_parts)})" if skip_parts else ")")
        sh_info = f"shatter={sh_n} (удалено пустых: {del_sh}" + (f", пропущены: {', '.join(skip_sh)})" if skip_sh else ")")
        static_info = f"static: {', '.join(created_static) if created_static else '—'}"
        self.report({'INFO'}, f"Geometry: {parts_info}; {sh_info}; {static_info}")
        return {'FINISHED'}

# --- MAST ---

class CSH_OT_CreateMast(bpy.types.Operator):
    """Создаёт коллекцию <Ship>_mastN с root->(geometry,hull). В основной geometry добавляет указатель mastN (90,0,90)."""
    bl_idname = "csh.create_mast"
    bl_label = "Create Mast"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        props = context.scene.csh_props
        ship_name = sanitize(props.ship_name)
        if not ship_name:
            self.report({'ERROR'}, "Введите имя корабля.")
            return {'CANCELLED'}
        mast_n = int(props.mast_number)

        # ship collection
        ship_col = ensure_collection(ship_name)
        ensure_root_and_children(ship_col)
        geom = ensure_geometry_parent(ship_col)

        # create / link mast collection
        mast_col_name = f"{ship_name}_mast{mast_n}"
        if mast_col_name in bpy.data.collections:
            mast_col = bpy.data.collections[mast_col_name]
            link_collection_to_scene(mast_col)
        else:
            mast_col = bpy.data.collections.new(mast_col_name)
            link_collection_to_scene(mast_col)

        # inside mast collection: root -> (geometry, hull)
        mast_root = find_in_collection(mast_col, "root")
        if mast_root is None:
            mast_root = create_empty("root", mast_col, None)
        for child_name in ("geometry", "hull"):
            child = next((o for o in mast_col.objects if o.name == child_name and o.type == 'EMPTY'), None)
            if child is None:
                create_empty(child_name, mast_col, mast_root)

        # add mastN empty under main geometry (with rotation 90,0,90)
        mast_ptr_name = f"mast{mast_n}"
        ptr = next((ch for ch in geom.children if ch.type == 'EMPTY' and ch.name == mast_ptr_name), None)
        if ptr is None:
            ptr = create_empty(mast_ptr_name, ship_col, geom)
            normalize_empty(ptr)
        set_geom_child_rotation(ptr)

        self.report({'INFO'}, f"Создана мачта: {mast_col_name}; указатель {mast_ptr_name} добавлен в geometry.")
        return {'FINISHED'}

# -----------
# Панель UI (сворачиваемые секции)
# -----------

def draw_fold(layout, props, prop_flag: str, title: str, icon: str = 'TRIA_RIGHT'):
    open_now = getattr(props, prop_flag)
    row = layout.row(align=True)
    row.prop(props, prop_flag, text="", icon='TRIA_DOWN' if open_now else 'TRIA_RIGHT', emboss=False)
    row.label(text=title, icon=icon)
    return open_now

class CSH_PT_Main(bpy.types.Panel):
    bl_label = "Create Ship"
    bl_idname = "CSH_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Create Ship"

    def draw(self, context):
        layout = self.layout
        props = context.scene.csh_props

        # Ship Base
        if draw_fold(layout, props, "show_ship_base", "Ship Base", icon="OUTLINER_COLLECTION"):
            box = layout.box()
            box.prop(props, "ship_name")
            box.operator("csh.create_ship", icon="ADD")

        # Cannons
        if draw_fold(layout, props, "show_cannons", "Cannons", icon="MOD_ARRAY"):
            box2 = layout.box()
            row = box2.row(align=True)
            row.prop(props, "cannonb_count"); row.prop(props, "cannonf_count")
            row = box2.row(align=True)
            row.prop(props, "cannonl_count"); row.prop(props, "cannonr_count")
            box2.operator("csh.apply_cannons", icon="OUTLINER_OB_EMPTY")

        # Lights
        if draw_fold(layout, props, "show_lights", "Lights Locators", icon="LIGHT"):
            boxL = layout.box()
            boxL.prop(props, "lights_count")
            boxL.operator("csh.apply_lights", icon="OUTLINER_OB_EMPTY")

        # Flares
        if draw_fold(layout, props, "show_flares", "Flares", icon="FORCE_FORCE"):
            boxFl = layout.box()
            row = boxFl.row(align=True)
            row.prop(props, "flares_type", expand=True)
            row = boxFl.row(align=True)
            row.prop(props, "flares_mast")
            boxFl.operator("csh.add_flare", icon="ADD")

        # Fireplace
        if draw_fold(layout, props, "show_fireplace", "Fireplace Locators", icon="ORIENTATION_LOCAL"):
            boxF = layout.box()
            boxF.prop(props, "fireplace_count")
            boxF.operator("csh.apply_fireplace", icon="OUTLINER_OB_EMPTY")

        # Geometry / Groups
        if draw_fold(layout, props, "show_geometry", "Geometry / Groups", icon="MESH_CUBE"):
            box3 = layout.box()
            row = box3.row(align=True)
            row.prop(props, "parts_count")
            row.prop(props, "shatter_count")
            col = box3.column(align=True)
            col.label(text="Static:")
            grid = col.grid_flow(columns=2, even_columns=True, even_rows=True, align=True)
            grid.prop(props, "make_path");        grid.prop(props, "make_wind")
            grid.prop(props, "make_watermask");   grid.prop(props, "make_fonar_day")
            grid.prop(props, "make_fonar_night"); grid.prop(props, "make_shatter1_baller")
            box3.operator("csh.apply_geometry_groups", icon="GROUP")

        # Mast
        if draw_fold(layout, props, "show_mast", "Mast", icon="OUTLINER_COLLECTION"):
            boxM = layout.box()
            boxM.prop(props, "mast_number")
            boxM.operator("csh.create_mast", icon="ADD")

# ----------------
# Регистрация
# ----------------

classes = (
    CSH_Props,
    CSH_OT_Create,
    CSH_OT_ApplyCannons,
    CSH_OT_ApplyLights,
    CSH_OT_AddFlare,
    CSH_OT_ApplyFireplace,
    CSH_OT_ApplyGeometryGroups,
    CSH_OT_CreateMast,
    CSH_PT_Main,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.csh_props = bpy.props.PointerProperty(type=CSH_Props)

def unregister():
    del bpy.types.Scene.csh_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
