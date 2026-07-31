bl_info = {
    "name": "Sailor Points Exporter and Importer",
    "author": "mPlank",
    "blender": (3, 6, 0),
    "category": "Object",
}

import bpy
import os


SAILOR_POINT_TYPES = {
    0: "00_Normal",
    1: "01_CanL",
    2: "02_CanR",
    3: "03_CanF",
    4: "04_CanB",
    5: "05_Mast_1",
    6: "06_Mast_2",
    7: "07_Mast_3",
    8: "08_Mast_4",
    9: "09_Mast_5",
    10: "10_Non_Target",
    11: "11_Action_1_Rope",
    12: "12_Action_2_Bort",
    13: "13_Action_3_Deck",
    14: "14_Exit_Sailor",
    15: "15_Nest_Mars_Sailor",
}


SAILOR_POINT_DESCRIPTIONS = {
    0: {
        "en": "Normal sailor navigation point.",
        "ru": "Обычная навигационная точка матроса.",
    },
    1: {
        "en": "Left cannon area sailor point.",
        "ru": "Точка матроса для зоны левых пушек.",
    },
    2: {
        "en": "Right cannon area sailor point.",
        "ru": "Точка матроса для зоны правых пушек.",
    },
    3: {
        "en": "Forward cannon area sailor point.",
        "ru": "Точка матроса для зоны передних пушек.",
    },
    4: {
        "en": "Rear cannon area sailor point.",
        "ru": "Точка матроса для зоны задних пушек.",
    },
    5: {
        "en": "Mast 1 sailor point.",
        "ru": "Точка матроса для мачты 1.",
    },
    6: {
        "en": "Mast 2 sailor point.",
        "ru": "Точка матроса для мачты 2.",
    },
    7: {
        "en": "Mast 3 sailor point.",
        "ru": "Точка матроса для мачты 3.",
    },
    8: {
        "en": "Mast 4 sailor point.",
        "ru": "Точка матроса для мачты 4.",
    },
    9: {
        "en": "Mast 5 sailor point.",
        "ru": "Точка матроса для мачты 5.",
    },
    10: {
        "en": "Non-target sailor point.",
        "ru": "Служебная точка матроса, не являющаяся целью.",
    },
    11: {
        "en": "Action point 1: rope action.",
        "ru": "Точка действия 1: действие с верёвками.",
    },
    12: {
        "en": "Action point 2: bort action.",
        "ru": "Точка действия 2: действие у борта.",
    },
    13: {
        "en": "Action point 3: deck action.",
        "ru": "Точка действия 3: действие на палубе.",
    },
    14: {
        "en": "Exit point for sailor.",
        "ru": "Точка выхода матроса.",
    },
    15: {
        "en": "Nest / mars sailor point.",
        "ru": "Точка матроса для марса.",
    },
}


# ------------------------------------------------------------
# Localization helpers
# ------------------------------------------------------------

def use_russian_tooltips(context=None):
    try:
        prefs = context.preferences if context else bpy.context.preferences
        view = prefs.view

        language = getattr(view, "language", "")
        use_tooltips = getattr(view, "use_translate_tooltips", True)

        return bool(use_tooltips and str(language).lower().startswith("ru"))
    except Exception:
        return False


def localized(context, ru_text, en_text):
    return ru_text if use_russian_tooltips(context) else en_text


def get_point_type_description(context, animation_value):
    data = SAILOR_POINT_DESCRIPTIONS.get(
        animation_value,
        {
            "en": "Unknown sailor point type.",
            "ru": "Неизвестный тип точки матроса.",
        }
    )

    return data["ru"] if use_russian_tooltips(context) else data["en"]


# ------------------------------------------------------------
# Collections
# ------------------------------------------------------------

def get_or_create_collection(name, parent=None):
    collection = bpy.data.collections.get(name)

    if collection is None:
        collection = bpy.data.collections.new(name)

    if parent is None:
        scene_collection = bpy.context.scene.collection

        if collection.name not in scene_collection.children.keys():
            try:
                scene_collection.children.link(collection)
            except RuntimeError:
                pass
    else:
        if collection.name not in parent.children.keys():
            try:
                parent.children.link(collection)
            except RuntimeError:
                pass

    return collection


def get_sailor_root_collection():
    return get_or_create_collection("SailorPoints")


def get_type_collection(animation_value):
    root = get_sailor_root_collection()
    collection_name = SAILOR_POINT_TYPES.get(animation_value, f"{animation_value:02d}_Unknown")
    return get_or_create_collection(collection_name, root)


def get_links_collection():
    root = get_sailor_root_collection()
    return get_or_create_collection("Links", root)


def move_object_to_collection(obj, target_collection):
    if obj.name not in target_collection.objects.keys():
        target_collection.objects.link(obj)

    for coll in list(obj.users_collection):
        if coll != target_collection:
            try:
                coll.objects.unlink(obj)
            except RuntimeError:
                pass


# ------------------------------------------------------------
# Point utils
# ------------------------------------------------------------

def is_sailor_point(obj):
    return obj and obj.type == 'EMPTY' and obj.name.startswith("SP_")


def get_next_point_index():
    max_index = -1

    for obj in bpy.data.objects:
        if is_sailor_point(obj):
            index = obj.get("original_index", None)

            if index is not None:
                try:
                    max_index = max(max_index, int(index))
                    continue
                except ValueError:
                    pass

            parts = obj.name.split("_")
            if len(parts) >= 2:
                try:
                    max_index = max(max_index, int(parts[1]))
                except ValueError:
                    pass

    return max_index + 1


def set_point_name(obj, point_index, animation_value):
    obj.name = f"SP_{point_index}_{animation_value}"


def get_point_index_from_name(obj):
    if "original_index" in obj:
        try:
            return int(obj["original_index"])
        except ValueError:
            pass

    parts = obj.name.split("_")

    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            pass

    return get_next_point_index()


def get_point_animation(obj):
    if "animation" in obj:
        try:
            return int(obj["animation"])
        except ValueError:
            return 0

    parts = obj.name.split("_")

    if len(parts) >= 3:
        try:
            return int(parts[2].split(".")[0])
        except ValueError:
            return 0

    return 0


def update_link_references(old_name, new_name):
    if old_name == new_name:
        return

    for obj in bpy.data.objects:
        if is_sailor_point(obj):
            for link in obj.sailor_links:
                if link.target == old_name:
                    link.target = new_name


def setup_point_object(obj, animation_value=0, point_index=None):
    if point_index is None:
        point_index = get_next_point_index()

    old_name = obj.name

    obj.empty_display_type = 'ARROWS'
    obj.empty_display_size = 0.6
    obj.show_name = True

    obj["animation"] = int(animation_value)
    obj["original_index"] = int(point_index)

    set_point_name(obj, point_index, animation_value)
    update_link_references(old_name, obj.name)

    move_object_to_collection(obj, get_type_collection(animation_value))

    return obj


# ------------------------------------------------------------
# Old label cleanup
# ------------------------------------------------------------

def delete_old_label_objects():
    removed = 0

    for obj in list(bpy.data.objects):
        is_old_label = obj.get("is_sailor_label", False) or obj.name.startswith("label_SP_")

        if is_old_label:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)

            if data and data.users == 0:
                try:
                    bpy.data.curves.remove(data)
                except RuntimeError:
                    pass

            removed += 1

    return removed


# ------------------------------------------------------------
# Links
# ------------------------------------------------------------

def has_link(obj, target_name):
    for link in obj.sailor_links:
        if link.target == target_name:
            return True

    return False


def add_unique_link(obj, target_name):
    if not has_link(obj, target_name):
        link = obj.sailor_links.add()
        link.target = target_name
        return True

    return False


def remove_link_to_target(obj, target_name):
    removed = 0

    for i in range(len(obj.sailor_links) - 1, -1, -1):
        if obj.sailor_links[i].target == target_name:
            obj.sailor_links.remove(i)
            removed += 1

    return removed


def remove_bidirectional_link(ob1, ob2):
    removed = 0
    removed += remove_link_to_target(ob1, ob2.name)
    removed += remove_link_to_target(ob2, ob1.name)
    return removed


def get_link_curve_name(ob1, ob2, link_index):
    p1 = ob1.name.split("_")
    p2 = ob2.name.split("_")

    a = f"{p1[0]}_{p1[1]}"
    b = f"{p2[0]}_{p2[1]}"

    return f"line_{link_index}({a},{b})"


def delete_all_link_objects():
    removed = 0

    for obj in list(bpy.data.objects):
        if obj.name.startswith("line_") or obj.get("is_sailor_link_line", False):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)

            if data and data.users == 0:
                if hasattr(data, "splines"):
                    try:
                        bpy.data.curves.remove(data)
                    except RuntimeError:
                        pass
                elif hasattr(data, "vertices"):
                    try:
                        bpy.data.meshes.remove(data)
                    except RuntimeError:
                        pass

            removed += 1

    return removed


def create_dynamic_link_curve(ob1, ob2, link_index):
    link_name = get_link_curve_name(ob1, ob2, link_index)

    curve = bpy.data.curves.new(link_name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 0
    curve.render_resolution_u = 0

    spline = curve.splines.new('POLY')
    spline.points.add(1)

    spline.points[0].co = (ob1.location.x, ob1.location.y, ob1.location.z, 1.0)
    spline.points[1].co = (ob2.location.x, ob2.location.y, ob2.location.z, 1.0)

    curve.bevel_depth = 0.015
    curve.bevel_resolution = 0

    link_obj = bpy.data.objects.new(link_name, curve)
    link_obj.display_type = 'WIRE'

    get_links_collection().objects.link(link_obj)

    hook_start = link_obj.modifiers.new("Hook_Start", 'HOOK')
    hook_start.object = ob1
    hook_start.vertex_indices_set([0])
    hook_start.matrix_inverse = ob1.matrix_world.inverted()

    hook_end = link_obj.modifiers.new("Hook_End", 'HOOK')
    hook_end.object = ob2
    hook_end.vertex_indices_set([1])
    hook_end.matrix_inverse = ob2.matrix_world.inverted()

    link_obj["is_sailor_link_line"] = True
    link_obj["link_start"] = ob1.name
    link_obj["link_end"] = ob2.name

    return link_obj


def rebuild_sailor_link_curves():
    delete_all_link_objects()

    points = [
        obj for obj in bpy.data.objects
        if is_sailor_point(obj)
    ]

    point_map = {obj.name: obj for obj in points}
    created_links = set()
    link_index = 0

    for point in points:
        for link in point.sailor_links:
            target = point_map.get(link.target)

            if target is None:
                continue

            key = tuple(sorted((point.name, target.name)))

            if key in created_links:
                continue

            created_links.add(key)
            create_dynamic_link_curve(point, target, link_index)
            link_index += 1

    return link_index


def cleanup_broken_and_duplicate_links():
    points = [
        obj for obj in bpy.data.objects
        if is_sailor_point(obj)
    ]

    point_names = {obj.name for obj in points}
    removed = 0

    for point in points:
        seen = set()

        for i in range(len(point.sailor_links) - 1, -1, -1):
            target_name = point.sailor_links[i].target

            if target_name not in point_names:
                point.sailor_links.remove(i)
                removed += 1
                continue

            if target_name == point.name:
                point.sailor_links.remove(i)
                removed += 1
                continue

            if target_name in seen:
                point.sailor_links.remove(i)
                removed += 1
                continue

            seen.add(target_name)

    return removed


def ensure_links_are_bidirectional():
    points = [
        obj for obj in bpy.data.objects
        if is_sailor_point(obj)
    ]

    point_map = {obj.name: obj for obj in points}
    added = 0

    for point in points:
        for link in point.sailor_links:
            target = point_map.get(link.target)

            if target is None:
                continue

            if add_unique_link(target, point.name):
                added += 1

    return added


# ------------------------------------------------------------
# Property group
# ------------------------------------------------------------

class SailorLink(bpy.types.PropertyGroup):
    target: bpy.props.StringProperty(name="Target")


# ------------------------------------------------------------
# Operators
# ------------------------------------------------------------

class AddSailorPoint(bpy.types.Operator):
    bl_idname = "object.add_sailor_point"
    bl_label = "Add Sailor Point"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return localized(
            context,
            "Создать новую обычную точку матроса типа 0 - Normal.",
            "Create a new normal sailor point of type 0 - Normal."
        )

    def execute(self, context):
        point_index = get_next_point_index()

        bpy.ops.object.empty_add(type='ARROWS')
        obj = context.object

        setup_point_object(obj, animation_value=0, point_index=point_index)
        obj.sailor_links.clear()

        return {'FINISHED'}


class LinkSailorPoints(bpy.types.Operator):
    bl_idname = "object.link_sailor_points"
    bl_label = "Link Sailor Points"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return localized(
            context,
            "Связать две выбранные точки матросов и создать между ними динамическую линию.",
            "Link two selected sailor points and create a dynamic line between them."
        )

    def execute(self, context):
        selected_objects = [
            obj for obj in context.selected_objects
            if is_sailor_point(obj)
        ]

        if len(selected_objects) != 2:
            self.report({'WARNING'}, "Select exactly 2 sailor points to link")
            return {'FINISHED'}

        ob1, ob2 = selected_objects

        if ob1.name == ob2.name:
            self.report({'WARNING'}, "Cannot link point to itself")
            return {'FINISHED'}

        already_linked = has_link(ob1, ob2.name) and has_link(ob2, ob1.name)

        add_unique_link(ob1, ob2.name)
        add_unique_link(ob2, ob1.name)

        cleanup_broken_and_duplicate_links()
        ensure_links_are_bidirectional()
        rebuild_sailor_link_curves()

        if already_linked:
            self.report({'INFO'}, f"{ob1.name} and {ob2.name} are already linked")
        else:
            self.report({'INFO'}, f"Linked {ob1.name} and {ob2.name}")

        return {'FINISHED'}


class UnlinkSailorPoints(bpy.types.Operator):
    bl_idname = "object.unlink_sailor_points"
    bl_label = "Unlink Sailor Points"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return localized(
            context,
            "Удалить связь между двумя выбранными точками матросов и пересобрать линии.",
            "Remove the link between two selected sailor points and rebuild the link lines."
        )

    def execute(self, context):
        selected_objects = [
            obj for obj in context.selected_objects
            if is_sailor_point(obj)
        ]

        if len(selected_objects) != 2:
            self.report({'WARNING'}, "Select exactly 2 sailor points to unlink")
            return {'FINISHED'}

        ob1, ob2 = selected_objects

        if ob1.name == ob2.name:
            self.report({'WARNING'}, "Cannot unlink point from itself")
            return {'FINISHED'}

        removed = remove_bidirectional_link(ob1, ob2)

        cleanup_broken_and_duplicate_links()
        ensure_links_are_bidirectional()
        rebuild_sailor_link_curves()

        if removed > 0:
            self.report({'INFO'}, f"Unlinked {ob1.name} and {ob2.name}")
        else:
            self.report({'INFO'}, f"No link found between {ob1.name} and {ob2.name}")

        return {'FINISHED'}


class ExportSailorPoints(bpy.types.Operator):
    bl_idname = "object.export_sailor_points"
    bl_label = "Export Sailor Points"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def description(cls, context, properties):
        return localized(
            context,
            "Экспортировать все точки матросов и их связи в INI-файл.",
            "Export all sailor points and their links to an INI file."
        )

    def execute(self, context):
        points = []
        links = []
        links_set = set()

        cleanup_broken_and_duplicate_links()
        ensure_links_are_bidirectional()

        for obj in bpy.data.objects:
            if is_sailor_point(obj):
                points.append(obj)

        points.sort(key=lambda obj: int(obj.get("original_index", 999999)))

        point_index_map = {point.name: i for i, point in enumerate(points)}

        for obj in points:
            for link in obj.sailor_links:
                if link.target not in point_index_map:
                    continue

                key = tuple(sorted((obj.name, link.target)))

                if key in links_set:
                    continue

                links_set.add(key)
                links.append((obj.name, link.target))

        if not self.filepath:
            self.report({'ERROR'}, "No file path specified")
            return {'CANCELLED'}

        if not self.filepath.lower().endswith('.ini'):
            self.filepath += '.ini'

        with open(bpy.path.abspath(self.filepath), 'w') as file:
            file.write("[SIZE]\n")
            file.write(f"points = {len(points)}\n")
            file.write(f"links = {len(links)}\n\n")

            file.write("[POINT_DATA]\n")
            for i, point in enumerate(points):
                x, y, z = point.location
                animation_value = get_point_animation(point)
                file.write(f"point {i} = {-y:.6f},{z:.6f},{x:.6f},{animation_value}\n")

            file.write("\n[LINK_DATA]\n")
            for i, (point_name, target_name) in enumerate(links):
                idx1 = point_index_map[point_name]
                idx2 = point_index_map[target_name]
                file.write(f"link {i} = {idx1},{idx2}\n")

        self.report({'INFO'}, f"Exported {len(points)} points and {len(links)} links to {self.filepath}")
        return {'FINISHED'}


class ImportSailorPoints(bpy.types.Operator):
    bl_idname = "object.import_sailor_points"
    bl_label = "Import Sailor Points"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def description(cls, context, properties):
        return localized(
            context,
            "Импортировать точки матросов и связи из INI-файла.",
            "Import sailor points and links from an INI file."
        )

    def execute(self, context):
        if not os.path.exists(bpy.path.abspath(self.filepath)):
            self.report({'ERROR'}, "File path does not exist")
            return {'CANCELLED'}

        with open(bpy.path.abspath(self.filepath), 'r') as file:
            data = file.readlines()

        points = []
        links = []
        point_data = False
        link_data = False

        get_sailor_root_collection()
        get_links_collection()

        for line in data:
            line = line.strip()

            if line.startswith("[POINT_DATA]"):
                point_data = True
                link_data = False
                continue

            if line.startswith("[LINK_DATA]"):
                point_data = False
                link_data = True
                continue

            if line.startswith("[SIZE]") or line == "" or "=" not in line:
                continue

            if point_data:
                parts = line.split("=")
                coords = parts[1].strip().split(",")

                x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                animation_value = int(coords[3]) if len(coords) > 3 else 0

                bpy.ops.object.empty_add(type='ARROWS', location=(z, -x, y))
                point = context.object

                setup_point_object(point, animation_value=animation_value, point_index=len(points))
                point.sailor_links.clear()

                points.append(point)

            elif link_data:
                parts = line.split("=")
                indices = parts[1].strip().split(",")

                idx1, idx2 = int(indices[0]), int(indices[1])
                links.append((idx1, idx2))

        for idx1, idx2 in links:
            if idx1 < 0 or idx2 < 0 or idx1 >= len(points) or idx2 >= len(points):
                continue

            point1 = points[idx1]
            point2 = points[idx2]

            add_unique_link(point1, point2.name)
            add_unique_link(point2, point1.name)

        cleanup_broken_and_duplicate_links()
        ensure_links_are_bidirectional()
        rebuild_sailor_link_curves()

        self.report({'INFO'}, f"Imported {len(points)} points and {len(links)} links from {self.filepath}")
        return {'FINISHED'}


class SetAnimationValue(bpy.types.Operator):
    bl_idname = "object.set_animation_value"
    bl_label = "Set Animation Value"

    animation_value: bpy.props.IntProperty()

    @classmethod
    def description(cls, context, properties):
        animation_value = int(getattr(properties, "animation_value", 0))

        point_description = get_point_type_description(context, animation_value)

        if use_russian_tooltips(context):
            return (
                f"{point_description} "
                f"Если выбрана точка SP_, изменить её тип на {animation_value}. "
                f"Если ничего не выбрано, создать новую точку этого типа."
            )

        return (
            f"{point_description} "
            f"If an SP_ point is selected, change its type to {animation_value}. "
            f"If nothing is selected, create a new point of this type."
        )

    def execute(self, context):
        selected_objects = [
            obj for obj in context.selected_objects
            if is_sailor_point(obj)
        ]

        if not selected_objects:
            point_index = get_next_point_index()

            bpy.ops.object.empty_add(type='ARROWS')
            obj = context.object

            setup_point_object(obj, animation_value=self.animation_value, point_index=point_index)
            obj.sailor_links.clear()

        else:
            for obj in selected_objects:
                point_index = get_point_index_from_name(obj)
                old_name = obj.name

                obj["animation"] = int(self.animation_value)
                obj["original_index"] = int(point_index)

                set_point_name(obj, point_index, self.animation_value)
                update_link_references(old_name, obj.name)

                obj.empty_display_type = 'ARROWS'
                obj.empty_display_size = 0.6
                obj.show_name = True

                move_object_to_collection(obj, get_type_collection(self.animation_value))

            cleanup_broken_and_duplicate_links()
            ensure_links_are_bidirectional()
            rebuild_sailor_link_curves()

        return {'FINISHED'}


class RefreshSailorLabels(bpy.types.Operator):
    bl_idname = "object.refresh_sailor_labels"
    bl_label = "Refresh Sailor Labels"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return localized(
            context,
            "Обновить папки, имена, связи и динамические линии. Также удаляет старые label-объекты.",
            "Refresh folders, names, links and dynamic lines. Also removes old label objects."
        )

    def execute(self, context):
        point_count = 0

        for obj in bpy.data.objects:
            if is_sailor_point(obj):
                animation_value = get_point_animation(obj)
                point_index = get_point_index_from_name(obj)
                old_name = obj.name

                obj["animation"] = int(animation_value)
                obj["original_index"] = int(point_index)

                set_point_name(obj, point_index, animation_value)
                update_link_references(old_name, obj.name)

                obj.empty_display_type = 'ARROWS'
                obj.empty_display_size = 0.6
                obj.show_name = True

                move_object_to_collection(obj, get_type_collection(animation_value))

                point_count += 1

        removed_labels = delete_old_label_objects()
        removed_links = delete_all_link_objects()
        removed_bad_links = cleanup_broken_and_duplicate_links()
        added_reverse_links = ensure_links_are_bidirectional()
        link_count = rebuild_sailor_link_curves()

        self.report(
            {'INFO'},
            f"Refreshed {point_count} points, {link_count} links, removed {removed_links} old lines, {removed_labels} labels, {removed_bad_links} bad links, added {added_reverse_links} reverse links"
        )

        return {'FINISHED'}


class CleanRebuildSailorPoints(bpy.types.Operator):
    bl_idname = "object.clean_rebuild_sailor_points"
    bl_label = "Clean / Rebuild SailorPoints"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return localized(
            context,
            "Полностью очистить и пересобрать структуру SailorPoints: папки, индексы, связи, линии и старые label-объекты.",
            "Fully clean and rebuild the SailorPoints structure: folders, indices, links, lines and old label objects."
        )

    def execute(self, context):
        points = [
            obj for obj in bpy.data.objects
            if is_sailor_point(obj)
        ]

        used_indices = set()
        next_index = 0

        for obj in points:
            index = get_point_index_from_name(obj)

            if index in used_indices:
                while next_index in used_indices:
                    next_index += 1

                index = next_index

            used_indices.add(index)

            animation_value = get_point_animation(obj)
            old_name = obj.name

            obj["animation"] = int(animation_value)
            obj["original_index"] = int(index)

            set_point_name(obj, index, animation_value)
            update_link_references(old_name, obj.name)

            obj.empty_display_type = 'ARROWS'
            obj.empty_display_size = 0.6
            obj.show_name = True

            move_object_to_collection(obj, get_type_collection(animation_value))

        removed_labels = delete_old_label_objects()
        removed_lines = delete_all_link_objects()
        removed_bad_links = cleanup_broken_and_duplicate_links()
        added_reverse_links = ensure_links_are_bidirectional()
        rebuilt_links = rebuild_sailor_link_curves()

        self.report(
            {'INFO'},
            f"Clean rebuild: {len(points)} points, {rebuilt_links} links, removed {removed_lines} lines, {removed_labels} labels, {removed_bad_links} bad links, added {added_reverse_links} reverse links"
        )

        return {'FINISHED'}


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

class SailorPointsPanel(bpy.types.Panel):
    bl_label = "Sailor Points"
    bl_idname = "OBJECT_PT_sailor_points"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sailor Points'

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("object.add_sailor_point")

        row = layout.row()
        row.operator("object.link_sailor_points")

        row = layout.row()
        row.operator("object.unlink_sailor_points")

        row = layout.row()
        row.operator("object.refresh_sailor_labels", text="Refresh Folders / Links")

        row = layout.row()
        row.operator("object.clean_rebuild_sailor_points", text="Clean / Rebuild SailorPoints")

        row = layout.row()
        row.operator("object.export_sailor_points", text="Export Sailor Points").filepath = context.scene.export_filepath

        row = layout.row()
        row.operator("object.import_sailor_points", text="Import Sailor Points").filepath = context.scene.import_filepath

        row = layout.row()
        row.label(text="Set Animation Value:")

        row = layout.row()
        row.operator("object.set_animation_value", text="0 - Normal").animation_value = 0
        row.operator("object.set_animation_value", text="1 - CanL").animation_value = 1

        row = layout.row()
        row.operator("object.set_animation_value", text="2 - CanR").animation_value = 2
        row.operator("object.set_animation_value", text="3 - CanF").animation_value = 3

        row = layout.row()
        row.operator("object.set_animation_value", text="4 - CanB").animation_value = 4
        row.operator("object.set_animation_value", text="5 - Mast 1").animation_value = 5

        row = layout.row()
        row.operator("object.set_animation_value", text="6 - Mast 2").animation_value = 6
        row.operator("object.set_animation_value", text="7 - Mast 3").animation_value = 7

        row = layout.row()
        row.operator("object.set_animation_value", text="8 - Mast 4").animation_value = 8
        row.operator("object.set_animation_value", text="9 - Mast 5").animation_value = 9

        row = layout.row()
        row.operator("object.set_animation_value", text="10 - Non Target").animation_value = 10

        row = layout.row()
        row.operator("object.set_animation_value", text="11 - Action 1 - Rope Action").animation_value = 11

        row = layout.row()
        row.operator("object.set_animation_value", text="12 - Action 2 - Bort Action").animation_value = 12

        row = layout.row()
        row.operator("object.set_animation_value", text="13 - Action 3 - Deck Action").animation_value = 13

        row = layout.row()
        row.operator("object.set_animation_value", text="14 - Exit - Exit Sailor").animation_value = 14

        row = layout.row()
        row.operator("object.set_animation_value", text="15 - Nest - Mars Sailor").animation_value = 15

        row = layout.row()
        row.prop(context.scene, "export_filepath", text="Export Filepath")

        row = layout.row()
        row.prop(context.scene, "import_filepath", text="Import Filepath")


# ------------------------------------------------------------
# Menu
# ------------------------------------------------------------

def menu_func_export(self, context):
    self.layout.operator(ExportSailorPoints.bl_idname, text="Export Sailor Points")


def menu_func_import(self, context):
    self.layout.operator(ImportSailorPoints.bl_idname, text="Import Sailor Points")


classes = (
    SailorLink,
    AddSailorPoint,
    LinkSailorPoints,
    UnlinkSailorPoints,
    ExportSailorPoints,
    ImportSailorPoints,
    SetAnimationValue,
    RefreshSailorLabels,
    CleanRebuildSailorPoints,
    SailorPointsPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.sailor_links = bpy.props.CollectionProperty(type=SailorLink)

    bpy.types.Scene.export_filepath = bpy.props.StringProperty(
        name="Export Filepath",
        description="Filepath for exporting sailor points data",
        default="//sailor_points.ini",
        subtype='FILE_PATH'
    )

    bpy.types.Scene.import_filepath = bpy.props.StringProperty(
        name="Import Filepath",
        description="Filepath for importing sailor points data",
        default="//sailor_points.ini",
        subtype='FILE_PATH'
    )

    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    try:
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    except Exception:
        pass

    try:
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    except Exception:
        pass

    if hasattr(bpy.types.Object, "sailor_links"):
        del bpy.types.Object.sailor_links

    if hasattr(bpy.types.Scene, "export_filepath"):
        del bpy.types.Scene.export_filepath

    if hasattr(bpy.types.Scene, "import_filepath"):
        del bpy.types.Scene.import_filepath

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


if __name__ == "__main__":
    register()