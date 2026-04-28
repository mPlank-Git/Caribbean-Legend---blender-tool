import bpy
import re
import os
from bpy.types import Panel, Operator
from bpy.props import (
    StringProperty, BoolProperty, IntProperty, FloatProperty, 
    CollectionProperty, EnumProperty, PointerProperty
)
from bpy_extras.io_utils import ExportHelper

# Глобальные переменные
properties_registered = False
last_known_objects = set()

# Названия пунктов выпадающего списка (по умолчанию)
DEFAULT_SET_NAMES = ["Set1", "Set2", "Set3"]

# Функция для обновления списка выпадающего меню
def update_selectlist_items(self, context):
    items = []
    # Если список имен пуст, используем значения по умолчанию
    if not hasattr(context.scene, 'se_selectlist_names') or len(context.scene.se_selectlist_names) == 0:
        for i, name in enumerate(DEFAULT_SET_NAMES):
            items.append((str(i), name, f"Selection Set {i+1}"))
    else:
        for i, item in enumerate(context.scene.se_selectlist_names):
            items.append((str(i), item.name, f"Selection Set {i+1}"))
    return items

# Функция для обновления имен (добавьте это в самое начало)
def update_selectlist_names(context):
    """Обновляет имена в наборах при изменении имен в списке"""
    if len(context.scene.se_selectlist_names) >= 3:
        # Обновляем имена в se_selectlist_sets
        if len(context.scene.se_selectlist_sets) >= 1:
            context.scene.se_selectlist_sets[0].name = context.scene.se_selectlist_names[0].name
        if len(context.scene.se_selectlist_sets) >= 2:
            context.scene.se_selectlist_sets[1].name = context.scene.se_selectlist_names[1].name
        if len(context.scene.se_selectlist_sets) >= 3:
            context.scene.se_selectlist_sets[2].name = context.scene.se_selectlist_names[2].name
        
        # Принудительно обновляем enum property
        context.scene.se_selectlist_index = context.scene.se_selectlist_index

def init_last_known_objects(scene):
    """Инициализирует множество известных объектов"""
    global last_known_objects
    try:
        last_known_objects = {obj.name for obj in bpy.data.objects}
        
        # Инициализация имен по умолчанию при первой загрузке
        if scene and not scene.se_selectlist_names:
            for name in DEFAULT_SET_NAMES:
                item = scene.se_selectlist_names.add()
                item.name = name
        
        if scene and not scene.se_selectlist_sets:
            for name in DEFAULT_SET_NAMES:
                set_item = scene.se_selectlist_sets.add()
                set_item.name = name
                
    except AttributeError:
        last_known_objects = set()

############################################################################################################

class SelectListSet(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Set Name", default="Set")
    object_names: bpy.props.StringProperty(default="")
    is_hidden: bpy.props.BoolProperty(default=False)

class SelectListName(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="List Name", 
        default="Set",
        update=lambda self, context: update_selectlist_names(context)
    )

class SE_OT_Objects_MakeRope(Operator):
    """Convert selected objects to rope curves with round bevel profile and apply RopeVar1 material"""
    bl_idname = "se.objects_make_rope"
    bl_label = "Make Rope"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects


    def execute(self, context):
        prefs = context.preferences.addons[__name__.split(".")[0]].preferences
        processed = 0
        skipped = []
        material_missing = False

        for obj in context.selected_objects:
            # Проверяем можно ли конвертировать объект в кривую
            if obj.type not in {'MESH', 'CURVE', 'FONT', 'SURFACE'}:
                skipped.append(obj.name)
                continue

            try:
                # Конвертируем в кривую если нужно
                if obj.type != 'CURVE':
                    context.view_layer.objects.active = obj
                    bpy.ops.object.convert(target='CURVE')
                
                # Применяем параметры веревки
                if obj.data.bevel_mode == 'ROUND':
                    obj.data.bevel_depth = prefs.rope_depth
                    obj.data.bevel_resolution = prefs.rope_resolution
                
                # Применяем материал RopeVar1
                mat = bpy.data.materials.get("RopeVar1")
                if mat:
                    if obj.data.materials:
                        obj.data.materials[0] = mat
                    else:
                        obj.data.materials.append(mat)
                else:
                    material_missing = True
                
                processed += 1
            except Exception as e:
                skipped.append(obj.name)
                print(f"Error processing {obj.name}: {str(e)}")

        # Обновляем Shader Editor
        for area in context.screen.areas:
            if area.type == 'SHADER_EDITOR':
                area.tag_redraw()

        # Формируем сообщение
        msg = f"Rope setup: {processed} objects"
        if material_missing:
            msg += " (RopeVar1 material missing)"
        if skipped:
            msg += f". Skipped {len(skipped)} objects"
        
        self.report({'WARNING' if material_missing or skipped else 'INFO'}, msg)
        return {'FINISHED'}

class SE_OT_Objects_MakeVant(Operator):
    """Convert selected objects to vant curves with round bevel profile and apply RopeVant material"""
    bl_idname = "se.objects_make_vant"
    bl_label = "Make Vant"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        prefs = context.preferences.addons[__name__.split(".")[0]].preferences
        processed = 0
        skipped = []
        material_missing = False

        for obj in context.selected_objects:
            # Проверяем можно ли конвертировать объект в кривую
            if obj.type not in {'MESH', 'CURVE', 'FONT', 'SURFACE'}:
                skipped.append(obj.name)
                continue

            try:
                # Конвертируем в кривую если нужно
                if obj.type != 'CURVE':
                    context.view_layer.objects.active = obj
                    bpy.ops.object.convert(target='CURVE')
                
                # Применяем параметры ванта
                if obj.data.bevel_mode == 'ROUND':
                    obj.data.bevel_depth = prefs.vant_depth
                    obj.data.bevel_resolution = prefs.vant_resolution
                
                # Применяем материал RopeVant
                mat = bpy.data.materials.get("RopeVant")
                if mat:
                    if obj.data.materials:
                        obj.data.materials[0] = mat
                    else:
                        obj.data.materials.append(mat)
                else:
                    material_missing = True
                
                processed += 1
            except Exception as e:
                skipped.append(obj.name)
                print(f"Error processing {obj.name}: {str(e)}")

        # Обновляем Shader Editor
        for area in context.screen.areas:
            if area.type == 'SHADER_EDITOR':
                area.tag_redraw()

        # Формируем сообщение
        msg = f"Vant setup: {processed} objects"
        if material_missing:
            msg += " (RopeVant material missing)"
        if skipped:
            msg += f". Skipped {len(skipped)} objects"
        
        self.report({'WARNING' if material_missing or skipped else 'INFO'}, msg)
        return {'FINISHED'}

class SE_OT_Objects_FindSelect(Operator):
    """Select objects whose names contain the search text\nHidden or excluded objects will be skipped with warning\nWorks only in Object Mode"""
    bl_idname = "se.objects_find_select"
    bl_label = "Find and Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        search_text = context.scene.se_objects_search_text.lower()
        if not search_text:
            return {'CANCELLED'}

        # Получаем все объекты сцены
        all_objects = bpy.data.objects
        selected_objects = []
        not_in_view_layer = []
        
        # Проверяем, нужно ли искать в BAKING коллекции
        search_in_baking = context.scene.se_search_in_baking
        baking_collection = bpy.data.collections.get("BAKING")

        # Снимаем выделение со всех объектов
        # лишнее bpy.ops.object.select_all(action='DESELECT')

        for obj in all_objects:
            # Пропускаем объекты из BAKING коллекции, если поиск в ней отключен
            if not search_in_baking and baking_collection and obj.name in baking_collection.objects:
                continue

            obj_name = obj.name.lower()
            if context.scene.se_search_prefix_suffix:
                # Поиск только по префиксу или постфиксу
                if obj_name.startswith(search_text) or obj_name.endswith(search_text):
                    if obj.name in context.view_layer.objects:
                        selected_objects.append(obj)
                    else:
                        not_in_view_layer.append(obj.name)
            else:
                # Поиск по всему имени
                if search_text in obj_name:
                    if obj.name in context.view_layer.objects:
                        selected_objects.append(obj)
                    else:
                        not_in_view_layer.append(obj.name)

        # Выбираем найденные объекты
        for obj in selected_objects:
            obj.select_set(True)

        # Делаем последний найденный объект активным, если нет активного
        if selected_objects:
            if not context.active_object or context.active_object not in selected_objects:
                context.view_layer.objects.active = selected_objects[-1]

        # Формируем сообщение
        msg = f"Selected {len(selected_objects)} objects"
        if not_in_view_layer:
            msg += f" ({len(not_in_view_layer)} not in current view layer)"
        
        self.report({'INFO' if not not_in_view_layer else 'WARNING'}, msg)
        return {'FINISHED'}

class SE_OT_Objects_FindSelect2(Operator):
    """Select objects whose names contain the search text\nHidden or excluded objects will be skipped with warning\nWorks only in Object Mode"""
    bl_idname = "se.objects_find_select2"
    bl_label = "Find and Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        search_text = context.scene.se_objects_search_text2.lower()
        if not search_text:
            return {'CANCELLED'}

        all_objects = bpy.data.objects
        selected_objects = []
        not_in_view_layer = []
        
        search_in_baking = context.scene.se_search_in_baking2
        baking_collection = bpy.data.collections.get("BAKING")

        for obj in all_objects:
            if not search_in_baking and baking_collection and obj.name in baking_collection.objects:
                continue

            obj_name = obj.name.lower()
            if context.scene.se_search_prefix_suffix2:
                if obj_name.startswith(search_text) or obj_name.endswith(search_text):
                    if obj.name in context.view_layer.objects:
                        selected_objects.append(obj)
                    else:
                        not_in_view_layer.append(obj.name)
            else:
                if search_text in obj_name:
                    if obj.name in context.view_layer.objects:
                        selected_objects.append(obj)
                    else:
                        not_in_view_layer.append(obj.name)

        for obj in selected_objects:
            obj.select_set(True)

        if selected_objects:
            if not context.active_object or context.active_object not in selected_objects:
                context.view_layer.objects.active = selected_objects[-1]

        msg = f"Selected {len(selected_objects)} objects"
        if not_in_view_layer:
            msg += f" ({len(not_in_view_layer)} not in current view layer)"
        
        self.report({'INFO' if not not_in_view_layer else 'WARNING'}, msg)
        return {'FINISHED'}

class SE_OT_Objects_FindSelect3(Operator):
    """Select objects whose names contain the search text\nHidden or excluded objects will be skipped with warning\nWorks only in Object Mode"""
    bl_idname = "se.objects_find_select3"
    bl_label = "Find and Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        search_text = context.scene.se_objects_search_text3.lower()
        if not search_text:
            return {'CANCELLED'}

        all_objects = bpy.data.objects
        selected_objects = []
        not_in_view_layer = []
        
        search_in_baking = context.scene.se_search_in_baking3
        baking_collection = bpy.data.collections.get("BAKING")

        for obj in all_objects:
            if not search_in_baking and baking_collection and obj.name in baking_collection.objects:
                continue

            obj_name = obj.name.lower()
            if context.scene.se_search_prefix_suffix3:
                if obj_name.startswith(search_text) or obj_name.endswith(search_text):
                    if obj.name in context.view_layer.objects:
                        selected_objects.append(obj)
                    else:
                        not_in_view_layer.append(obj.name)
            else:
                if search_text in obj_name:
                    if obj.name in context.view_layer.objects:
                        selected_objects.append(obj)
                    else:
                        not_in_view_layer.append(obj.name)

        for obj in selected_objects:
            obj.select_set(True)

        if selected_objects:
            if not context.active_object or context.active_object not in selected_objects:
                context.view_layer.objects.active = selected_objects[-1]

        msg = f"Selected {len(selected_objects)} objects"
        if not_in_view_layer:
            msg += f" ({len(not_in_view_layer)} not in current view layer)"
        
        self.report({'INFO' if not not_in_view_layer else 'WARNING'}, msg)
        return {'FINISHED'}

class SE_OT_SelectListAdd(Operator):
    """Add selected objects to current set"""
    bl_idname = "se.selectlist_add"
    bl_label = "Add"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Кнопка активна только если есть выделенные объекты
        return context.selected_objects

    def execute(self, context):
        if context.scene.se_auto_clean_sets:
            bpy.ops.se.clean_all_sets()
        scene = context.scene
        set_index = int(scene.se_selectlist_index)
        
        # Проверяем и инициализируем наборы, если они пусты
        if len(scene.se_selectlist_sets) <= set_index:
            for i in range(len(scene.se_selectlist_sets), set_index + 1):
                new_set = scene.se_selectlist_sets.add()
                new_set.name = f"Set{i+1}"
        
        selection_set = scene.se_selectlist_sets[set_index]
        
        # Get current object names in set
        current_names = set(selection_set.object_names.split(',')) if selection_set.object_names else set()
        
        # Add new objects
        for obj in context.selected_objects:
            if obj.name not in current_names:
                current_names.add(obj.name)
                # Если набор скрыт, скрываем и добавляемый объект
                if selection_set.is_hidden:
                    obj.hide_viewport = True
        
        # Update the set
        selection_set.object_names = ','.join(sorted(current_names))
        
        self.report({'INFO'}, f"Added {len(context.selected_objects)} objects to {selection_set.name}")
        return {'FINISHED'}

class SE_OT_SelectListRemove(Operator):
    """Remove selected objects from current set"""
    bl_idname = "se.selectlist_remove"
    bl_label = "Remove"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Кнопка активна только если есть выделенные объекты и они есть в текущем наборе
        if not context.selected_objects:
            return False
            
        set_index = int(context.scene.se_selectlist_index)
        if len(context.scene.se_selectlist_sets) <= set_index:
            return False
            
        selection_set = context.scene.se_selectlist_sets[set_index]
        if not selection_set.object_names:
            return False
            
        current_names = set(selection_set.object_names.split(','))
        return any(obj.name in current_names for obj in context.selected_objects)

    def execute(self, context):
        if context.scene.se_auto_clean_sets:
            bpy.ops.se.clean_all_sets()
        set_index = int(context.scene.se_selectlist_index)
        selection_set = context.scene.se_selectlist_sets[set_index]
        
        current_names = set(selection_set.object_names.split(','))
        removed = 0
        
        for obj in context.selected_objects:
            if obj.name in current_names:
                current_names.remove(obj.name)
                removed += 1
        
        selection_set.object_names = ','.join(sorted(current_names))
        
        self.report({'INFO'}, f"Removed {removed} objects from {selection_set.name}")
        return {'FINISHED'}

class SE_OT_SelectListClear(Operator):
    """Clear current set"""
    bl_idname = "se.selectlist_clear"
    bl_label = "Clear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        set_index = int(context.scene.se_selectlist_index)
        selection_set = context.scene.se_selectlist_sets[set_index]
        
        if not selection_set.object_names:
            return {'CANCELLED'}
        
        # 1. Получаем все объекты из текущего набора
        current_set_objects = set(selection_set.object_names.split(','))
        
        # 2. Собираем объекты из всех других наборов, которые скрыты
        objects_in_other_sets = {}
        for i, other_set in enumerate(context.scene.se_selectlist_sets):
            if i != set_index and other_set.object_names and other_set.is_hidden:
                for obj_name in other_set.object_names.split(','):
                    objects_in_other_sets[obj_name] = True
        
        # 3. Определяем объекты, которые нужно показать
        objects_to_show = []
        for obj_name in current_set_objects:
            # Показываем только если объект не скрыт в других наборах
            if obj_name not in objects_in_other_sets:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    objects_to_show.append(obj)
        
        # 4. Показываем объекты
        for obj in objects_to_show:
            obj.hide_viewport = False
        
        # 5. Очищаем набор
        selection_set.object_names = ""
        selection_set.is_hidden = False
        
        self.report({'INFO'}, f"Cleared {selection_set.name} and showed {len(objects_to_show)} objects")
        return {'FINISHED'}

class SE_OT_CleanAllSets(Operator):
    """Remove all missing objects from all selection sets"""
    bl_idname = "se.clean_all_sets"
    bl_label = "Clean All Sets"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        total_removed = 0
        
        for scene in bpy.data.scenes:
            if hasattr(scene, 'se_selectlist_sets'):
                for selection_set in scene.se_selectlist_sets:
                    if selection_set.object_names:
                        original_names = set(selection_set.object_names.split(','))
                        cleaned_names = {name for name in original_names if name in bpy.data.objects}
                        
                        removed = len(original_names) - len(cleaned_names)
                        if removed > 0:
                            selection_set.object_names = ','.join(sorted(cleaned_names))
                            total_removed += removed
        
        self.report({'INFO'}, f"Removed {total_removed} missing objects from all sets")
        return {'FINISHED'}

class SE_OT_SelectListSelect(Operator):
    """Select all objects in current set"""
    bl_idname = "se.selectlist_select"
    bl_label = "Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        set_index = int(context.scene.se_selectlist_index)
        if len(context.scene.se_selectlist_sets) <= set_index:
            return False
        selection_set = context.scene.se_selectlist_sets[set_index]
        return bool(selection_set.object_names)
        
    def execute(self, context):
        if context.scene.se_auto_clean_sets:
            bpy.ops.se.clean_all_sets()
        set_index = int(context.scene.se_selectlist_index)
        selection_set = context.scene.se_selectlist_sets[set_index]
        
        if not selection_set.object_names:
            return {'CANCELLED'}
            
        # Deselect all first
        bpy.ops.object.select_all(action='DESELECT')
        
        selected_objects = []
        missing_objects = []
        excluded_objects = []  # список для объектов, исключенных из View Layer
        total_items = len(selection_set.object_names.split(','))
        
        for obj_name in selection_set.object_names.split(','):
            obj = bpy.data.objects.get(obj_name)
            if obj:
                if obj.name in context.view_layer.objects:
                    obj.select_set(True)
                    selected_objects.append(obj)
                else:
                    excluded_objects.append(obj_name)  # Добавляем в список исключенных
            else:
                missing_objects.append(obj_name)
        
        # Делаем последний объект активным, если есть выбранные объекты
        if selected_objects:
            context.view_layer.objects.active = selected_objects[-1]
        
        # Формируем сообщение
        if len(selected_objects) == total_items:
            self.report({'INFO'}, f"Selected {len(selected_objects)} objects from {selection_set.name}")
        else:
            msg = f"Selected: {len(selected_objects)}"
            if excluded_objects:
                msg += f", excluded from View Layer: {len(excluded_objects)}"
            if missing_objects:
                msg += f", missing: {len(missing_objects)} (click Clean button)"
            
            self.report({'WARNING'}, msg)
        
        return {'FINISHED'}

class SE_OT_Objects_ShowHideSelected(Operator):
    """Show/Hide objects in set
    Note: Alt+H will not make these objects visible
    Note: Unhide before GM-export"""
    bl_idname = "se.objects_show_hide_selected"
    bl_label = "Show/Hide"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.scene.se_auto_clean_sets:
            bpy.ops.se.clean_all_sets()
        scene = context.scene
        set_index = int(scene.se_selectlist_index)
        
        # Создаем набор, если его нет
        while len(scene.se_selectlist_sets) <= set_index:
            new_set = scene.se_selectlist_sets.add()
            new_set.name = f"Set{len(scene.se_selectlist_sets)}"
            new_set.is_hidden = False
        
        selection_set = scene.se_selectlist_sets[set_index]
        
        if not selection_set.object_names:
            self.report({'WARNING'}, "Set is empty")
            return {'CANCELLED'}
        
        # Определяем новое состояние (инвертируем текущее)
        new_hidden_state = not selection_set.is_hidden
        
        # Применяем новое состояние ко всем объектам
        processed_count = 0
        missing_objects = []
        total_items = len(selection_set.object_names.split(','))
        
        for obj_name in selection_set.object_names.split(','):
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.hide_viewport = new_hidden_state
                if new_hidden_state:
                    obj.select_set(False)  # Снимаем выделение при скрытии
                processed_count += 1
            else:
                missing_objects.append(obj_name)
        
        # Обновляем состояние в наборе
        selection_set.is_hidden = new_hidden_state
        
        action = "Shown" if not new_hidden_state else "Hidden"
        
        # Формируем сообщение
        if processed_count == total_items:
            self.report({'INFO'}, f"{action} {processed_count} objects in {selection_set.name}")
        else:
            self.report({'WARNING'}, 
                f"{action} {processed_count} objects in {selection_set.name}, {len(missing_objects)} missing (click Clean button)")
        
        return {'FINISHED'}

class SE_OT_SelectListInfo(Operator):
    """Tools for managing named selection sets:
    
    Dropdown Menu - Select which of the 3 available sets to work with
    Settings (Gear Icon) - Rename sets and manage visibility
    Select (Cursor Icon) - Select all objects in current set
    Show/Hide (Eye Icon) - Toggle visibility of objects in current set

    + (Add) - Add selected objects to current set
    – (Remove) - Remove selected objects from current set
    x (Clear) - Clear current set and show all objects
    
    Note: Clicking this info button displays detailed information about current selection set"""
    bl_idname = "se.selectlist_info_button"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        set_index = int(context.scene.se_selectlist_index)
        
        if len(context.scene.se_selectlist_sets) <= set_index:
            self.report({'INFO'}, "No selection set available")
            self.report({'INFO'}, "(Click here for detailed information)")
            return {'CANCELLED'}
            
        selection_set = context.scene.se_selectlist_sets[set_index]
        
        if not selection_set.object_names:
            self.report({'INFO'}, f"Set '{selection_set.name}' is empty")
            self.report({'INFO'}, "(Click here for detailed information)")
            return {'CANCELLED'}
        
        obj_names = selection_set.object_names.split(',')
        existing_objects = []
        missing_objects = []
        
        for name in obj_names:
            if name in bpy.data.objects:
                existing_objects.append(name)
            else:
                missing_objects.append(name)
        
        msg = f"Set '{selection_set.name}': {len(existing_objects)} objects"
        if missing_objects:
            msg += f" ({len(missing_objects)} missing)"
        
        msg += f"\nVisibility: {'HIDDEN' if selection_set.is_hidden else 'VISIBLE'}"
        
        # Показываем первые 30 существующих объектов
        max_show = 30
        if existing_objects:
            msg += "\n\nExisting objects:"
            for i, name in enumerate(existing_objects[:max_show]):
                msg += f"\n  {i+1}. {name}"
            if len(existing_objects) > max_show:
                msg += f"\n  ... and {len(existing_objects) - max_show} more"
        
        # Показываем первые 5 отсутствующих объектов
        if missing_objects:
            msg += "\n\nMissing objects:"
            for i, name in enumerate(missing_objects[:5]):
                msg += f"\n  {i+1}. {name}"
            if len(missing_objects) > 5:
                msg += f"\n  ... and {len(missing_objects) - 5} more"
            msg += "\n\nConsider cleaning the set"
        
        self.report({'INFO'}, msg.strip())
        self.report({'INFO'}, "(Click here for detailed information)")
        return {'FINISHED'}

class SE_OT_SelectListSettings(Operator):
    """List settings"""
    bl_idname = "se.selectlist_settings"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Открываем диалоговое окно для редактирования названий
        bpy.ops.se.selectlist_settings_dialog('INVOKE_DEFAULT')
        return {'FINISHED'}

class SE_OT_ResetVisibility(bpy.types.Operator):
    """Reset visibility for all sets"""
    bl_idname = "se.reset_visibility"
    bl_label = "Reset Visibility"
    bl_options = {'INTERNAL', 'UNDO'}
    
    def execute(self, context):
        for i in range(3):
            # Проверяем, существует ли набор
            if len(context.scene.se_selectlist_sets) > i:
                selection_set = context.scene.se_selectlist_sets[i]
                
                # Показываем все объекты в наборе
                if selection_set.object_names:
                    for obj_name in selection_set.object_names.split(','):
                        obj = bpy.data.objects.get(obj_name)
                        if obj:
                            obj.hide_viewport = False
                    
                    # Обновляем состояние кнопки
                    selection_set.is_hidden = False
        
        self.report({'INFO'}, "Reset visibility for all sets")
        # Обновляем интерфейс
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}

class SE_OT_SelectListSettingsDialog(bpy.types.Operator):
    bl_idname = "se.selectlist_settings_dialog"
    bl_label = "Edit List Names"
    
    list1: bpy.props.StringProperty(name="List 1", default=DEFAULT_SET_NAMES[0])
    list2: bpy.props.StringProperty(name="List 2", default=DEFAULT_SET_NAMES[1])
    list3: bpy.props.StringProperty(name="List 3", default=DEFAULT_SET_NAMES[2])
    
    def reset_visibility(self, context):
        """Принудительно показывает все объекты во всех списках"""
        for i in range(3):
            # Проверяем, существует ли набор
            if len(context.scene.se_selectlist_sets) > i:
                selection_set = context.scene.se_selectlist_sets[i]
                
                # Показываем все объекты в наборе
                if selection_set.object_names:
                    for obj_name in selection_set.object_names.split(','):
                        obj = bpy.data.objects.get(obj_name)
                        if obj:
                            obj.hide_viewport = False
                    
                    # Обновляем состояние кнопки
                    selection_set.is_hidden = False
        
        self.report({'INFO'}, "Reset visibility for all sets")
        # Обновляем интерфейс
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    
    def execute(self, context):
        # Обновляем глобальные переменные с новыми значениями
        global DEFAULT_SET_NAMES
        DEFAULT_SET_NAMES = [self.list1, self.list2, self.list3]
        
        # Проверяем и инициализируем данные при необходимости
        if len(context.scene.se_selectlist_names) == 0:
            for i in range(3):
                item = context.scene.se_selectlist_names.add()
                item.name = DEFAULT_SET_NAMES[i]
        
        if len(context.scene.se_selectlist_sets) == 0:
            for i in range(3):
                set_item = context.scene.se_selectlist_sets.add()
                set_item.name = DEFAULT_SET_NAMES[i]
        
        # Обновляем имена
        if len(context.scene.se_selectlist_names) < 3:
            context.scene.se_selectlist_names.clear()
            for name in DEFAULT_SET_NAMES:
                item = context.scene.se_selectlist_names.add()
                item.name = name
        else:
            context.scene.se_selectlist_names[0].name = self.list1
            context.scene.se_selectlist_names[1].name = self.list2
            context.scene.se_selectlist_names[2].name = self.list3
        
        # Обновляем имена в se_selectlist_sets
        if len(context.scene.se_selectlist_sets) >= 1:
            context.scene.se_selectlist_sets[0].name = self.list1
        if len(context.scene.se_selectlist_sets) >= 2:
            context.scene.se_selectlist_sets[1].name = self.list2
        if len(context.scene.se_selectlist_sets) >= 3:
            context.scene.se_selectlist_sets[2].name = self.list3
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Проверяем и инициализируем данные при необходимости
        if len(context.scene.se_selectlist_names) == 0:
            for i in range(3):
                item = context.scene.se_selectlist_names.add()
                item.name = DEFAULT_SET_NAMES[i]
        
        if len(context.scene.se_selectlist_names) >= 3:
            self.list1 = context.scene.se_selectlist_names[0].name
            self.list2 = context.scene.se_selectlist_names[1].name
            self.list3 = context.scene.se_selectlist_names[2].name
        else:
            self.list1 = DEFAULT_SET_NAMES[0]
            self.list2 = DEFAULT_SET_NAMES[1]
            self.list3 = DEFAULT_SET_NAMES[2]
        
        return context.window_manager.invoke_props_dialog(self, width=300)
    
    # Отрисовка всплывающего окна с настройками ############################################################################
    def draw(self, context):
        layout = self.layout
        
        # Поля ввода для имен
        layout.prop(self, "list1")
        layout.prop(self, "list2")
        layout.prop(self, "list3")
        
        layout.separator()
        
        # Кнопка Reset Visibility в отдельной строке
        row = layout.row()
        row.operator("se.reset_visibility", text="Reset Visibility", icon='HIDE_OFF')
        
        # Строка с кнопками Clean и Auto
        row = layout.row(align=True)
        
        # Кнопка очистки наборов
        row.operator("se.clean_all_sets", text="Clean Missing", icon='BRUSH_DATA')
        
        # Кнопка Auto Clean с иконкой и уменьшенной шириной
        auto_btn = row.row(align=True)
        auto_btn.scale_x = 0.5
        auto_btn.prop(
            context.scene, 
            "se_auto_clean_sets", 
            text="Auto", 
            toggle=True, 
            icon='CHECKBOX_HLT' if context.scene.se_auto_clean_sets else 'CHECKBOX_DEHLT'
        )
        
        layout.separator()


class SE_OT_Objects_FindMultiMaterial(Operator):
    """Select objects with more than one material slot
    Only searches visible objects in the current view layer"""
    bl_idname = "se.objects_find_multi_material"
    bl_label = "Find Multi-Material"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        selected_objects = []
        hidden_objects = []  # Скрытые вьюпортом
        excluded_objects = []  # Выключенные в слое
        view_layer = context.view_layer
        
        # Снимаем выделение со всех объектов
        bpy.ops.object.select_all(action='DESELECT')
        
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or len(obj.material_slots) <= 1:
                continue  # Пропускаем не-меши и объекты с 1 материалом
            
            # Проверяем, включён ли объект в текущий слой
            if obj.name not in view_layer.objects:
                excluded_objects.append(obj.name)
                continue
            
            # Проверяем, не скрыт ли объект
            if obj.hide_viewport:
                hidden_objects.append(obj.name)
                continue
            
            # Если объект видим и в слое — выделяем
            obj.select_set(True)
            selected_objects.append(obj)
        
        # Делаем последний найденный объект активным
        if selected_objects:
            context.view_layer.objects.active = selected_objects[-1]
        
        # Формируем отчёт
        report_msg = f"Selected {len(selected_objects)} objects"
        
        # Добавляем информацию о скрытых и исключённых объектах (если есть)
        if hidden_objects or excluded_objects:
            report_msg += "\n(Skipped: "
            if hidden_objects:
                report_msg += f"{len(hidden_objects)} hidden objects, "
            if excluded_objects:
                report_msg += f"{len(excluded_objects)} excluded from View Layer"
            report_msg = report_msg.rstrip(", ") + ")"
        
        # Отправляем отчёт (всегда INFO, даже если есть скрытые/исключённые)
        self.report({'INFO'}, report_msg)
        return {'FINISHED'}

class SE_OT_Objects_FindEmptyMeshes(Operator):
    """Select all mesh objects with zero vertices\nOnly searches visible objects in the current view layer"""
    bl_idname = "se.objects_find_empty_meshes"
    bl_label = "Find Empty Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        selected_objects = []
        view_layer = context.view_layer
        
        # Снимаем выделение со всех объектов
        bpy.ops.object.select_all(action='DESELECT')
        
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or obj.hide_viewport or obj.name not in view_layer.objects:
                continue  # Пропускаем не-меши, скрытые и исключённые объекты
            
            # Проверяем количество вершин
            if len(obj.data.vertices) == 0:
                obj.select_set(True)
                selected_objects.append(obj)
        
        # Делаем последний найденный объект активным
        if selected_objects:
            context.view_layer.objects.active = selected_objects[-1]
        
        self.report({'INFO'}, f"Selected {len(selected_objects)} empty meshes")
        return {'FINISHED'}

class SE_OT_FixNamesSettings(bpy.types.PropertyGroup):
    """Storage for fix names settings"""
    find_text: bpy.props.StringProperty(
        name="Find",
        description="Text to find in object names",
        default="."
    )
    replace_text: bpy.props.StringProperty(
        name="Replace",
        description="Text to replace with",
        default="_"
    )
    rename_empty: bpy.props.BoolProperty(
        name="Rename Empty",
        description="Also rename Empty objects (if disabled, only Mesh, Curve, etc. will be renamed)",
        default=False
    )

class SE_OT_FixNamesSettingsDialog(bpy.types.Operator):
    """Settings for Fix .001 names"""
    bl_idname = "se.fix_names_settings_dialog"
    bl_label = "Fix Names Settings"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        # Dialog automatically saves values when OK is pressed
        # Values are bound directly to the scene property
        self.report({'INFO'}, f"Settings saved: Find '{context.scene.se_fix_names_settings.find_text}' → Replace '{context.scene.se_fix_names_settings.replace_text}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.se_fix_names_settings
        
        col = layout.column(align=True)
        col.prop(settings, "find_text")
        col.prop(settings, "replace_text")
        
        layout.separator()
        
        # Checkbox for Empty objects
        layout.prop(settings, "rename_empty")

class SE_OT_FixDotZeroZeroOneNames(Operator):
    """Fix .001 names in object names according to Find/Replace rules\nOnly processes visible objects in current View Layer\nWorks only in Object Mode"""
    bl_idname = "se.fix_dot_zero_zero_one_names"
    bl_label = "Fix .001 names"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        settings = context.scene.se_fix_names_settings
        find_text = settings.find_text
        replace_text = settings.replace_text
        rename_empty = settings.rename_empty
        
        if not find_text:
            self.report({'WARNING'}, "Find text is empty, nothing to replace")
            return {'CANCELLED'}
        
        # Get objects in current view layer
        view_layer = context.view_layer
        processed = 0
        renamed = []
        skipped_hidden = []
        skipped_empty = []
        
        for obj in view_layer.objects:
            # Skip hidden objects
            if obj.hide_viewport:
                skipped_hidden.append(obj.name)
                continue
            
            # Skip Empty objects if rename_empty is False
            if not rename_empty and obj.type == 'EMPTY':
                skipped_empty.append(obj.name)
                continue
            
            old_name = obj.name
            # Check if find_text is in the name
            if find_text in old_name:
                new_name = old_name.replace(find_text, replace_text)
                
                # Handle name conflicts
                base_name = new_name
                counter = 1
                while bpy.data.objects.get(new_name) and bpy.data.objects.get(new_name) != obj:
                    new_name = f"{base_name}.{counter:03d}"
                    counter += 1
                
                if new_name != old_name:
                    obj.name = new_name
                    renamed.append(f"{old_name} → {new_name}")
                    processed += 1
        
        # Report results
        if processed > 0:
            msg = f"Renamed {processed} objects: {find_text} → {replace_text}"
            if skipped_empty:
                msg += f" (skipped {len(skipped_empty)} Empty objects)"
            if skipped_hidden:
                msg += f" (skipped {len(skipped_hidden)} hidden objects)"
            self.report({'INFO'}, msg)
        else:
            msg = f"No objects found containing '{find_text}'"
            if skipped_empty:
                msg += f" (skipped {len(skipped_empty)} Empty objects)"
            if skipped_hidden:
                msg += f" (skipped {len(skipped_hidden)} hidden objects)"
            self.report({'INFO'}, msg)
        
        return {'FINISHED'}

class SE_OT_ObjectsPanel_Toggle(Operator):
    """Show/Hide More Options"""
    bl_idname = "se.objects_panel_toggle"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.se_objects_panel_collapsed = not context.scene.se_objects_panel_collapsed
        return {'FINISHED'}

class SE_OT_Objects_AddMirrorY(Operator):
    """Add Mirror modifier with Y axis to selected objects"""
    bl_idname = "se.objects_add_mirror_y"
    bl_label = "Add Mirror Y"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects #and context.mode == 'OBJECT'

    def execute(self, context):
        processed = 0
        view_layer = context.view_layer
        
        for obj in context.selected_objects:
            if obj.hide_viewport or obj.name not in view_layer.objects or obj.type != 'MESH':
                continue
                
            mirror_mod = None
            for mod in obj.modifiers:
                if mod.type == 'MIRROR':
                    mirror_mod = mod
                    break
            
            if not mirror_mod:
                mirror_mod = obj.modifiers.new(name="Mirror", type='MIRROR')
                processed += 1
            
            mirror_mod.use_axis[0] = False  # X
            mirror_mod.use_axis[1] = True   # Y
            mirror_mod.use_axis[2] = False  # Z
            
            # Устанавливаем разумные значения по умолчанию
            mirror_mod.use_clip = True
            mirror_mod.show_viewport = True
        
        self.report({'INFO'}, f"Mirror Y added to {processed} objects")
        return {'FINISHED'}

class SE_OT_Objects_ToggleMirrorClipping(Operator):
    """Toggle clipping for Mirror modifiers on selected objects"""
    bl_idname = "se.objects_toggle_mirror_clipping"
    bl_label = "Toggle Mirror Clipping"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Доступно только если есть выделенные объекты с Mirror модификаторами
        return any(
            mod.type == 'MIRROR'
            for obj in context.selected_objects
            if obj.type == 'MESH' and not obj.hide_viewport
            for mod in obj.modifiers
        ) #and context.mode == 'OBJECT'

    def execute(self, context):
        processed = 0
        view_layer = context.view_layer
        
        # Определяем состояние на основе активного или последнего выделенного объекта
        active_obj = context.active_object
        if active_obj and active_obj.select_get() and active_obj.type == 'MESH':
            ref_obj = active_obj
        else:
            ref_obj = context.selected_objects[-1] if context.selected_objects else None
        
        # Получаем целевое состояние из первого найденного Mirror модификатора
        new_state = None
        if ref_obj and ref_obj.type == 'MESH':
            for mod in ref_obj.modifiers:
                if mod.type == 'MIRROR':
                    new_state = not mod.use_clip
                    break
        
        if new_state is None:
            new_state = True  # Значение по умолчанию, если не нашли модификатор
        
        # Применяем ко всем выделенным объектам
        for obj in context.selected_objects:
            if obj.hide_viewport or obj.name not in view_layer.objects or obj.type != 'MESH':
                continue
                
            for mod in obj.modifiers:
                if mod.type == 'MIRROR':
                    mod.use_clip = new_state
                    processed += 1
        
        self.report({'INFO'}, f"Mirror clipping {'enabled' if new_state else 'disabled'} on {processed} objects")
        return {'FINISHED'}

class SE_OT_Objects_ToggleMirrorRealtime(Operator):
    """Toggle viewport visibility for Mirror modifiers on selected objects"""
    bl_idname = "se.objects_toggle_mirror_realtime"
    bl_label = "Toggle Mirror Realtime"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Доступно только если есть выделенные объекты с Mirror модификаторами
        return any(
            mod.type == 'MIRROR'
            for obj in context.selected_objects
            if obj.type == 'MESH' and not obj.hide_viewport
            for mod in obj.modifiers
        ) #and context.mode == 'OBJECT'

    def execute(self, context):
        processed = 0
        view_layer = context.view_layer
        
        # Определяем состояние на основе активного или последнего выделенного объекта
        active_obj = context.active_object
        if active_obj and active_obj.select_get() and active_obj.type == 'MESH':
            ref_obj = active_obj
        else:
            ref_obj = context.selected_objects[-1] if context.selected_objects else None
        
        # Получаем целевое состояние из первого найденного Mirror модификатора
        new_state = None
        if ref_obj and ref_obj.type == 'MESH':
            for mod in ref_obj.modifiers:
                if mod.type == 'MIRROR':
                    new_state = not mod.show_viewport
                    break
        
        if new_state is None:
            new_state = False  # Значение по умолчанию, если не нашли модификатор
        
        # Применяем ко всем выделенным объектам
        for obj in context.selected_objects:
            if obj.hide_viewport or obj.name not in view_layer.objects or obj.type != 'MESH':
                continue
                
            for mod in obj.modifiers:
                if mod.type == 'MIRROR':
                    mod.show_viewport = new_state
                    processed += 1
        
        self.report({'INFO'}, f"Mirror viewport {'enabled' if new_state else 'disabled'} on {processed} objects")
        return {'FINISHED'}

class SE_OT_Objects_ApplyMirror(Operator):
    """Apply all Mirror modifiers on selected objects"""
    bl_idname = "se.objects_apply_mirror"
    bl_label = "Apply Mirror"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Только если есть выделенные меш-объекты с модификаторами Mirror
        return any(
            mod.type == 'MIRROR' 
            for obj in context.selected_objects 
            if obj.type == 'MESH' and not obj.hide_viewport
            for mod in obj.modifiers
        ) #and context.mode == 'OBJECT'

    def execute(self, context):
        processed = 0
        view_layer = context.view_layer
        
        for obj in context.selected_objects:
            if obj.hide_viewport or obj.name not in view_layer.objects or obj.type != 'MESH':
                continue
                
            # Применяем все Mirror модификаторы (с конца списка)
            for mod in reversed(obj.modifiers[:]):
                if mod.type == 'MIRROR':
                    try:
                        bpy.ops.object.modifier_apply(
                            {"object": obj},
                            modifier=mod.name
                        )
                        processed += 1
                    except Exception as e:
                        print(f"Error applying Mirror modifier on {obj.name}: {str(e)}")
        
        self.report({'INFO'}, f"Applied Mirror modifiers on {processed} objects")
        return {'FINISHED'}

class SE_OT_Objects_RemoveMirror(Operator):
    """Remove all Mirror modifiers from selected objects"""
    bl_idname = "se.objects_remove_mirror"
    bl_label = "Remove Mirror"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Только если есть выделенные меш-объекты с модификаторами Mirror
        return any(
            mod.type == 'MIRROR' 
            for obj in context.selected_objects 
            if obj.type == 'MESH' and not obj.hide_viewport
            for mod in obj.modifiers
        ) #and context.mode == 'OBJECT'

    def execute(self, context):
        processed = 0
        removed = 0
        view_layer = context.view_layer
        
        for obj in context.selected_objects:
            if obj.hide_viewport or obj.name not in view_layer.objects or obj.type != 'MESH':
                continue
                
            # Удаляем все Mirror модификаторы
            for mod in obj.modifiers[:]:
                if mod.type == 'MIRROR':
                    obj.modifiers.remove(mod)
                    removed += 1
            if removed > 0:
                processed += 1
        
        self.report({'INFO'}, f"Removed {removed} Mirror modifiers from {processed} objects")
        return {'FINISHED'}

class SE_OT_Objects_ClearGeomData(Operator):
    """Clear geometry data (split normals, bevel weights) from selected objects"""
    bl_idname = "se.objects_clear_geom_data"
    bl_label = "Clear GeomData"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects and context.mode == 'OBJECT'

    def execute(self, context):
        processed = 0
        for obj in context.selected_objects:
            if obj.type != 'MESH' or obj.hide_viewport:
                continue
            
            try:
                # Clear custom split normal data
                bpy.ops.mesh.customdata_custom_splitnormals_clear({'object': obj})
                
                # Clear bevel weights
                bpy.ops.mesh.customdata_bevel_weight_edge_clear({'object': obj})
                bpy.ops.mesh.customdata_bevel_weight_vertex_clear({'object': obj})
                
                processed += 1
            except Exception as e:
                print(f"Error processing {obj.name}: {str(e)}")
        
        self.report({'INFO'}, f"Cleared geometry data on {processed} objects")
        return {'FINISHED'}

# кнопки выбора текстуры в материале
class SE_OT_SelectMixNode(Operator):
    """Select and make active nodes connected to Mix node's input A (index 6) for all selected objects"""
    bl_idname = "se.select_mix_node"
    bl_label = "Select Mix Node"
    bl_options = {'REGISTER', 'UNDO'}
    
    blend_type: bpy.props.StringProperty(default="MULTIPLY")

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        found_nodes = []
        processed_objects = 0
        processed_materials = 0

        # Сначала собираем все найденные ноды
        for obj in selected_objects:
            if not hasattr(obj, 'material_slots') or not obj.material_slots:
                continue
            
            obj_processed = False
            
            for slot in obj.material_slots:
                if not slot.material or not slot.material.use_nodes:
                    continue
                
                node_tree = slot.material.node_tree
                nodes = node_tree.nodes
                
                for mix_node in nodes:
                    if mix_node.bl_idname == 'ShaderNodeMix' and mix_node.blend_type == self.blend_type:
                        if len(mix_node.inputs) > 6 and mix_node.inputs[6].is_linked:
                            connected_node = mix_node.inputs[6].links[0].from_node
                            found_nodes.append((node_tree, connected_node))
                            obj_processed = True
            
            if obj_processed:
                processed_objects += 1
                processed_materials += len([ms for ms in obj.material_slots 
                                        if ms.material and ms.material.use_nodes])
        
        if not found_nodes:
            self.report({'WARNING'}, f"No nodes connected to {self.blend_type} mix node's input A")
            return {'CANCELLED'}
        
        # Снимаем выделение со всех нод во всех материалах
        for obj in selected_objects:
            for slot in obj.material_slots:
                if slot.material and slot.material.use_nodes:
                    for node in slot.material.node_tree.nodes:
                        node.select = False
        
        # Выделяем и делаем активными найденные ноды
        last_node_tree = None
        last_node = None
        
        for node_tree, node in found_nodes:
            node.select = True
            node_tree.nodes.active = node  # Делаем ноду активной в её нод-группе
            last_node_tree = node_tree
            last_node = node
        
        self.report({'INFO'}, 
                f"Selected and activated {len(found_nodes)} nodes | "
                f"{processed_objects} objects | "
                f"{processed_materials} materials")
        return {'FINISHED'}

class SE_OT_SelectMultiplyNode(Operator):
    """Color Layer\nSelect and activate nodes connected to Multiply mix node's input A\nAlso sets UV1 as active"""
    bl_idname = "se.select_multiply_node"
    bl_label = "Select Multiply"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Устанавливаем настройки отображения
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.light = 'FLAT'
        context.space_data.shading.color_type = 'TEXTURE'
        
        # Выбираем все объекты только в объектном режиме
        if context.mode == 'OBJECT':
            bpy.ops.object.select_all(action='SELECT')
        
        # Проверяем, есть ли UV у объектов
        has_uv = False
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                has_uv = True
                break
        
        if has_uv:
            try:
                bpy.ops.se.uvmap_set_active1()
            except:
                self.report({'WARNING'}, "Could not set UV1 as active")
        
        result = bpy.ops.se.select_mix_node(blend_type='MULTIPLY')
        
        # Снимаем выделение только в объектном режиме
        if context.mode == 'OBJECT':
            bpy.ops.object.select_all(action='DESELECT')
        
        return result

class SE_OT_SelectDivideNode(Operator):
    """Shadow Layer\nSelect and activate nodes connected to Divide mix node's input A\nAlso sets UV2 as active"""
    bl_idname = "se.select_divide_node"
    bl_label = "Select Divide"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Устанавливаем настройки отображения
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.light = 'FLAT'
        context.space_data.shading.color_type = 'TEXTURE'
        
        # Выбираем все объекты только в объектном режиме
        if context.mode == 'OBJECT':
            bpy.ops.object.select_all(action='SELECT')
        
        # Проверяем, есть ли вторая UV у объектов
        has_uv2 = False
        for obj in context.selected_objects:
            if obj.type == 'MESH' and len(obj.data.uv_layers) > 1:
                has_uv2 = True
                break
        
        if has_uv2:
            try:
                bpy.ops.se.uvmap_set_active2()
            except:
                self.report({'WARNING'}, "Could not set UV2 as active (some objects may have only one UV map)")
        else:
            self.report({'WARNING'}, "No objects with second UV map found")
        
        result = bpy.ops.se.select_mix_node(blend_type='DIVIDE')
        
        # Снимаем выделение только в объектном режиме
        if context.mode == 'OBJECT':
            bpy.ops.object.select_all(action='DESELECT')
        
        return result

class SE_OT_SetAttributeDisplay(Operator):
    """Set viewport display to Attribute (Vertex Color) mode with Studio lighting"""
    bl_idname = "se.set_attribute_display"
    bl_label = "Attribute Display"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Устанавливаем режим отображения
        context.space_data.shading.light = 'STUDIO'
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.color_type = 'VERTEX'
        
        self.report({'INFO'}, "Viewport set to Attribute display mode")
        return {'FINISHED'}
        
class SE_OT_LinkSecondLayer(Operator):
    """Link second material layer (Divide input A) from active object to all selected objects"""
    bl_idname = "se.link_second_layer"
    bl_label = "Link Layer2"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects and context.active_object and context.active_object.select_get()

    def execute(self, context):
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'MESH' or not active_obj.material_slots:
            self.report({'WARNING'}, "Active object must be a mesh with materials")
            return {'CANCELLED'}

        # Находим текстуру второго слоя (Divide input A) в активном объекте
        source_texture = None
        for slot in active_obj.material_slots:
            if slot.material and slot.material.use_nodes:
                node_tree = slot.material.node_tree
                for node in node_tree.nodes:
                    if node.bl_idname == 'ShaderNodeMix' and node.blend_type == 'DIVIDE' and len(node.inputs) > 6 and node.inputs[6].is_linked:
                        connected_node = node.inputs[6].links[0].from_node
                        if connected_node.bl_idname == 'ShaderNodeTexImage':
                            source_texture = connected_node.image
                            break
                if source_texture:
                    break

        if not source_texture:
            self.report({'WARNING'}, "Active object has no texture in second material layer (Divide input A)")
            return {'CANCELLED'}

        processed = 0
        for obj in context.selected_objects:
            if obj == active_obj or obj.type != 'MESH' or not obj.material_slots:
                continue

            for slot in obj.material_slots:
                if not slot.material or not slot.material.use_nodes:
                    continue

                node_tree = slot.material.node_tree
                for node in node_tree.nodes:
                    if node.bl_idname == 'ShaderNodeMix' and node.blend_type == 'DIVIDE' and len(node.inputs) > 6 and node.inputs[6].is_linked:
                        texture_node = node.inputs[6].links[0].from_node
                        if texture_node.bl_idname == 'ShaderNodeTexImage':
                            texture_node.image = source_texture
                            processed += 1

        self.report({'INFO'}, f"Linked second layer texture to {processed} objects")
        return {'FINISHED'}

class SE_SceneProperties(bpy.types.PropertyGroup):
    gm_name: StringProperty(
        name="GM Name",
        description="Model name for export",
        default="test_model",
        maxlen=64,
    )
    
    last_export_dir: StringProperty(
        name="Last Export Directory",
        description="Stores the last used export directory for GM files",
        default="",
        subtype='DIR_PATH',
        options={'HIDDEN'},
    )

# -------------------------------------------------------------------------
# Оператор для переключения вкладок
# -------------------------------------------------------------------------

class SE_OT_set_tab(bpy.types.Operator):
    """Switch tab"""
    bl_idname = "se.set_tab"
    bl_label = "Set Tab"
    
    tab_name: bpy.props.EnumProperty(
        name="Tab",
        items=[
            ('HOME', "Home", ""),
            ('MODIFIERS', "Modifiers", ""),
            ('MATERIALS', "Materials", ""),
            ('CREATE', "Create", ""),
            ('CLEANUP', "Cleanup", ""),
            ('EXPORT', "Export", ""),
        ],
        default='HOME'
    )
    
    def execute(self, context):
        context.scene.se_active_tab = self.tab_name
        return {'FINISHED'}


# -------------------------------------------------------------------------
# Кастомная кнопка для вкладок с иконкой и возможностью подсветки
# -------------------------------------------------------------------------

class SE_OT_tab_button(bpy.types.Operator):
    """Tab button with icon"""
    bl_idname = "se.tab_button"
    bl_label = ""
    bl_options = {'INTERNAL'}
    
    tab_name: bpy.props.StringProperty()
    icon: bpy.props.StringProperty()
    
    def execute(self, context):
        context.scene.se_active_tab = self.tab_name
        return {'FINISHED'}
    
    @classmethod
    def description(cls, context, properties):
        return f"Switch to {properties.tab_name} tab"

# -------------------------------------------------------------------------
# Кнопка информации
# -------------------------------------------------------------------------

class SE_OT_info(bpy.types.Operator):
    """You can add buttons from these tabs to Favorites to optimize your workflow"""
    bl_idname = "se.info"
    bl_label = "Info"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Ничего не делаем при нажатии
        return {'FINISHED'}

# -------------------------------------------------------------------------
# Export Panel (moved from StormEngineImportExportPanel)
# -------------------------------------------------------------------------

# Global variable for session export path (will be shared from __init__)
_session_export_dir = ""

class SE_OT_ExportGM(Operator, ExportHelper):
    """Export GM model with automatic filename generation

Filename generation rules:
1. If selected ROOT is named "{prefs.main_empty_name}" - uses [GM Name].gm
2. Otherwise uses [GM Name][Root Name].gm

Note: select an EMPTY object for export"""

    bl_idname = "se.export_gm"
    bl_label = "Export GM"
    
    filename_ext = ".gm"
    filter_glob: StringProperty(default="*.gm", options={'HIDDEN'}, maxlen=255)
    triangulate: BoolProperty(name="Triangulate", default=True)
    
    # Добавляем остальные опции для экспорта
    smooth_out_normals: BoolProperty(name="Smooth all normals (experimental)", default=False)
    smooth_out_normals_marked: BoolProperty(name="Smooth marked normals (experimental)", default=False)
    prepare_uv: BoolProperty(name="Prepare UV (experimental)", default=False)
    patch_start_pose: BoolProperty(name="Patch start pose (experimental)", default=False)
    set_bsp_flag: BoolProperty(name="Set BSP flag (experimental)", default=False)
    save_origin_positions: BoolProperty(name="Save origin positions (experimental)", default=False)
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects and all(obj.type == 'EMPTY' for obj in context.selected_objects)
    
    @classmethod
    def description(cls, context, properties):
        """Dynamic description that shows actual main_empty_name from preferences"""
        addon_name = __name__.split(".")[0]
        if addon_name in context.preferences.addons:
            prefs = context.preferences.addons[addon_name].preferences
            main_empty_name = prefs.main_empty_name
        else:
            main_empty_name = "ROOT"
        
        return f"""Export GM model with automatic filename generation

Filename generation rules:
1. If selected ROOT is named "{main_empty_name}" - uses [GM Name].gm
2. Otherwise uses [GM Name][Root Name].gm
Note: The "{main_empty_name}" suffix can be changed in addon preferences

Note: select an EMPTY object for export"""
    
    def invoke(self, context, event):
        global _session_export_dir
        scene_props = context.scene.se_props
        addon_name = __name__.split(".")[0]
        prefs = context.preferences.addons[addon_name].preferences
        
        # Получаем базовое имя файла
        root_obj = context.active_object
        if root_obj and root_obj.type == 'EMPTY':
            clean_name = re.sub(r'\.\d{3}$', '', root_obj.name)
            if clean_name == prefs.main_empty_name:
                base_name = f"{scene_props.gm_name}.gm"
            else:
                base_name = f"{scene_props.gm_name}{clean_name}.gm"
        else:
            base_name = f"{scene_props.gm_name}.gm"
        
        # Формируем полный путь
        if _session_export_dir:
            self.filepath = os.path.join(_session_export_dir, base_name)
        elif scene_props.last_export_dir and prefs.save_paths_in_blend:
            self.filepath = os.path.join(scene_props.last_export_dir, base_name)
        else:
            if bpy.data.filepath:
                self.filepath = os.path.join(os.path.dirname(bpy.data.filepath), base_name)
            else:
                self.filepath = base_name
        
        return super().invoke(context, event)
    
    def execute(self, context):
        global _session_export_dir
        scene_props = context.scene.se_props
        addon_name = __name__.split(".")[0]
        prefs = context.preferences.addons[addon_name].preferences
        
        # Сохраняем только директорию
        export_dir = os.path.dirname(self.filepath)
        _session_export_dir = export_dir
        
        if prefs.save_paths_in_blend:
            scene_props.last_export_dir = export_dir
        else:
            scene_props.last_export_dir = ""
        
        # Вызываем оператор export.gm со всеми параметрами
        return bpy.ops.export.gm(
            filepath=self.filepath,
            triangulate=self.triangulate,
            smooth_out_normals=self.smooth_out_normals,
            smooth_out_normals_marked=self.smooth_out_normals_marked,
            prepare_uv=self.prepare_uv,
            patch_start_pose=self.patch_start_pose,
            set_bsp_flag=self.set_bsp_flag,
            save_origin_positions=self.save_origin_positions
        )

class SE_OT_ToggleSearchRow(Operator):
    """Toggle search row visibility"""
    bl_idname = "se.toggle_search_row"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    row_index: bpy.props.IntProperty(
        default=1,
        options={'SKIP_SAVE', 'HIDDEN'}  # Добавляем эти опции
    )
    
    def execute(self, context):
        if self.row_index == 1:
            # Переключаем видимость второй строки
            context.scene.se_show_search_row2 = not context.scene.se_show_search_row2
            # Если скрываем вторую строку, то автоматически скрываем и третью
            if not context.scene.se_show_search_row2:
                context.scene.se_show_search_row3 = False
        elif self.row_index == 2:
            # Переключаем видимость третьей строки
            context.scene.se_show_search_row3 = not context.scene.se_show_search_row3
        else:  # row_index == 3 - сворачиваем всё
            context.scene.se_show_search_row2 = False
            context.scene.se_show_search_row3 = False
        
        # Обновляем интерфейс
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Вызываем execute без отображения диалога
        return self.execute(context)

class SE_OT_OpenExportFolder(Operator):
    """Open last export folder in file browser
Opens saved folder if available, otherwise temporary session folder
    
Note: Saving folder path can be enabled in addon preferences"""
    bl_idname = "se.open_export_folder"
    bl_label = "Open Export Folder"
    
    @classmethod
    def poll(cls, context):
        # Кнопка активна если есть либо сохраненный путь, либо временный
        scene_props = context.scene.se_props
        return bool(scene_props.last_export_dir) or bool(_session_export_dir)
    
    def execute(self, context):
        import subprocess
        import sys
        global _session_export_dir
        
        # Определяем какую папку открывать (приоритет у сохраненной в .blend)
        export_dir = context.scene.se_props.last_export_dir or _session_export_dir
        
        try:
            # Для разных ОС
            if os.name == 'nt':  # Windows
                os.startfile(export_dir)
            elif os.name == 'posix':  # macOS и Linux
                subprocess.run(['open', export_dir] if sys.platform == 'darwin' else ['xdg-open', export_dir])
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open folder: {str(e)}")
            return {'CANCELLED'}

# -------------------------------------------------------------------------
# Export Panel UI (for Objects panel's Export tab)
# -------------------------------------------------------------------------

def draw_export_tab(self, context, col):
    """Draw Export tab content - GM export tools"""
    # Создаем box с темным фоном
    box = col.box()
    box.use_property_split = True
    box.use_property_decorate = False
    
    # Создаем основной column внутри box с align=True
    box_col = box.column(align=True)
    
    # Проверяем наличие свойства se_props
    if not hasattr(context.scene, 'se_props'):
        box_col.label(text="Export properties not initialized", icon='ERROR')
        return
    
    scene_props = context.scene.se_props
    global _session_export_dir
    
    # Основная строка с именем модели и кнопками
    main_row = box_col.row(align=True)
    
    # Метка "Name:" (ширина 0.5)
    label_col = main_row.row(align=True)
    label_col.scale_x = 0.5
    label_col.label(text="Name:")
    
    # Поле ввода (ширина 2.0)
    input_col = main_row.row(align=True)
    input_col.scale_x = 2.0
    input_col.prop(scene_props, "gm_name", text="")
    
    # Кнопка экспорта (ширина 1.0)
    btn_col = main_row.row(align=True)
    btn_col.scale_x = 1.0
    btn_col.enabled = bool(SE_OT_ExportGM.poll(context))
    btn_col.operator(SE_OT_ExportGM.bl_idname, icon='EXPORT', text="")
    
    # Кнопка открытия папки
    folder_btn = main_row.row(align=True)
    folder_btn.scale_x = 1.0
    folder_btn.enabled = bool(scene_props.last_export_dir) or bool(_session_export_dir)
    folder_btn.operator(SE_OT_OpenExportFolder.bl_idname, text="", icon='FILE_FOLDER')


##############################################################################################################################
### ПАНЕЛЬ ###################################################################################################################
##############################################################################################################################
class SE_PT_ObjectsPanel(Panel):
    """Object conversion tools panel"""
    bl_label = "Objects"
    bl_idname = "SE_PT_ObjectsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "StormEngineTools"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        # Панель отображается только если включена в настройках аддона
        addon_name = __name__.split(".")[0]  # Получаем имя аддона из модуля
        prefs = context.preferences.addons.get(addon_name)
        if prefs:
            return prefs.preferences.enable_objects_panel
        return False

    def draw(self, context):
        addon_name = __name__.split(".")[0]
        if addon_name not in context.preferences.addons:
            self.layout.label(text="Addon preferences not loaded!", icon='ERROR')
            return
        
        prefs = context.preferences.addons[addon_name].preferences

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        current_mode = context.mode
        
        # Если мы в режиме редактирования, показываем бокс с надписью Edit Mode и кнопками
        if current_mode == 'EDIT_MESH':
            # Создаем box с темным фоном
            edit_box = layout.box()
            edit_box.use_property_split = True
            edit_box.use_property_decorate = False
            
            edit_col = edit_box.column(align=True)
            
            # Добавляем надпись "Edit Mode"
            edit_col.label(text="Edit Mode", icon='EDITMODE_HLT')
            
            tool_settings = context.tool_settings
            
            # Correct Face Attributes
            is_active_correct_face = tool_settings.use_transform_correct_face_attributes
            
            row = edit_col.row()
            if is_active_correct_face:
                row.alert = True
            
            op = row.operator(
                "wm.context_toggle",
                text="Correct Face Attributes",
                icon='CHECKBOX_HLT' if is_active_correct_face else 'CHECKBOX_DEHLT'
            )
            op.data_path = "tool_settings.use_transform_correct_face_attributes"
            
            # Auto Merge Vertices
            is_active_auto_merge = tool_settings.use_mesh_automerge
            
            row = edit_col.row()
            if is_active_auto_merge:
                row.alert = True
            
            op = row.operator(
                "wm.context_toggle",
                text="Auto Merge Vertices",
                icon='CHECKBOX_HLT' if is_active_auto_merge else 'CHECKBOX_DEHLT'
            )
            op.data_path = "tool_settings.use_mesh_automerge"
            
            # Добавляем разделитель после кнопки
            #layout.separator()
        
        # Верхняя строка с вкладками и кнопкой информации
        top_row = layout.row(align=True)
        
        # Рисуем вкладки с иконками
        row = top_row.row(align=True)
        
        active_tab = context.scene.se_active_tab
        
        # Словарь с данными для вкладок (EDIT удален)
        tabs = {
            'HOME': ('HOME', "Home"),
            'MODIFIERS': ('MODIFIER', "Modifiers"),
            'MATERIALS': ('MATERIAL', "Materials"),
            'CREATE': ('MESH_CUBE', "Create"),
            'CLEANUP': ('TOOL_SETTINGS', "Cleanup"),
            'EXPORT': ('EXPORT', "Export"),
        }
        
        # Создаем кнопки-вкладки с иконками и подсветкой
        for tab_id, (icon, tooltip) in tabs.items():
            if active_tab == tab_id:
                op = row.operator("se.tab_button", text="", icon=icon, depress=True)
                op.tab_name = tab_id
                op.icon = icon
            else:
                op = row.operator("se.tab_button", text="", icon=icon)
                op.tab_name = tab_id
                op.icon = icon
        
        # Добавляем кнопку информации справа
        top_row.operator("se.info", text="", icon='INFO')
        
        # Основной контейнер с выравниванием
        col = layout.column(align=True)

        # Содержимое в зависимости от выбранной вкладки (EDIT удален)
        if active_tab == 'HOME':
            self.draw_home_tab(context, col, prefs)
        elif active_tab == 'MODIFIERS':
            self.draw_modifiers_tab(context, col)
        elif active_tab == 'MATERIALS':
            self.draw_materials_tab(context, col)
        elif active_tab == 'CREATE':
            self.draw_create_tab(context, col)
        elif active_tab == 'CLEANUP':
            self.draw_cleanup_tab(context, col)
        elif active_tab == 'EXPORT':
            self.draw_export_tab(context, col)
    
    def draw_home_tab(self, context, col, prefs):
        """Draw Home tab content"""
        # Создаем box с темным фоном
        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False
        
        # Создаем основной column внутри box с align=True
        box_col = box.column(align=True)
        
        # Helper function to draw a single search row with toggle button
        def draw_search_row(box_col, row_num, show_toggle=False, toggle_icon='TRIA_RIGHT', toggle_row_index=1):
            """Draw a single search row
            row_num: 1, 2 or 3
            show_toggle: показывать ли кнопку-стрелку
            toggle_icon: иконка для кнопки
            toggle_row_index: индекс строки для оператора
            """
            if row_num == 1:
                prefix_suffix = context.scene.se_search_prefix_suffix
                search_in_baking = context.scene.se_search_in_baking
                search_text = context.scene.se_objects_search_text
                find_operator = SE_OT_Objects_FindSelect.bl_idname
            elif row_num == 2:
                prefix_suffix = context.scene.se_search_prefix_suffix2
                search_in_baking = context.scene.se_search_in_baking2
                search_text = context.scene.se_objects_search_text2
                find_operator = "se.objects_find_select2"
            else:  # row_num == 3
                prefix_suffix = context.scene.se_search_prefix_suffix3
                search_in_baking = context.scene.se_search_in_baking3
                search_text = context.scene.se_objects_search_text3
                find_operator = "se.objects_find_select3"
            
            row = box_col.row(align=True)
            
            # Toggle button (если нужно)
            if show_toggle:
                toggle_btn = row.row(align=True)
                toggle_btn.scale_x = 1.0
                op = toggle_btn.operator(SE_OT_ToggleSearchRow.bl_idname, text="", icon=toggle_icon)
                op.row_index = toggle_row_index
            else:
                # Если кнопки нет, добавляем пустое место для выравнивания
                placeholder = row.row(align=True)
                placeholder.scale_x = 1.0
                placeholder.label(text="", icon='BLANK1')
            
            # Filter button (prefix/suffix toggle)
            filter_btn = row.row(align=True)
            filter_btn.scale_x = 1.0
            filter_btn.prop(context.scene, 
                            "se_search_prefix_suffix" if row_num == 1 else 
                            "se_search_prefix_suffix2" if row_num == 2 else 
                            "se_search_prefix_suffix3", 
                            text="", 
                            icon='FILTER')
            
            # Baking collection button
            if prefs.enable_baking_panel:
                baking_color_icon = f'COLLECTION_COLOR_0{int(prefs.baking_collection_color[-1])}'
                baking_btn = row.row(align=True)
                baking_btn.scale_x = 1.0
                baking_btn.prop(context.scene,
                                "se_search_in_baking" if row_num == 1 else
                                "se_search_in_baking2" if row_num == 2 else
                                "se_search_in_baking3",
                                text="",
                                icon=baking_color_icon)
            
            # Search text field
            search_field = row.row(align=True)
            search_field.prop(context.scene,
                            "se_objects_search_text" if row_num == 1 else
                            "se_objects_search_text2" if row_num == 2 else
                            "se_objects_search_text3",
                            text="",
                            icon='VIEWZOOM')
            
            # Search button
            search_btn = row.row(align=True)
            search_btn.scale_x = 1.0
            search_btn.operator(find_operator, text="", icon='VIEWZOOM')
        
        # Рисуем первую строку (всегда видима)
        # Стрелка показывает состояние второй строки
        first_toggle_icon = 'TRIA_DOWN' if context.scene.se_show_search_row2 else 'TRIA_RIGHT'
        draw_search_row(box_col, 1, show_toggle=True, toggle_icon=first_toggle_icon, toggle_row_index=1)
        
        # Вторая строка (видима только если se_show_search_row2 = True)
        if context.scene.se_show_search_row2:
            # Стрелка показывает состояние третьей строки
            second_toggle_icon = 'TRIA_DOWN' if context.scene.se_show_search_row3 else 'TRIA_RIGHT'
            draw_search_row(box_col, 2, show_toggle=True, toggle_icon=second_toggle_icon, toggle_row_index=2)
        
        # Третья строка (видима только если se_show_search_row3 = True)
        if context.scene.se_show_search_row3:
            # Третья строка имеет кнопку сворачивания вверх, которая закрывает всё
            draw_search_row(box_col, 3, show_toggle=True, toggle_icon='TRIA_UP', toggle_row_index=3)
        
        # Разделитель
        box_col.separator()
        
        # 2. Управление списками выделения (верхняя часть)
        row = box_col.row(align=True)
        
        # Кнопка Info
        info_btn = row.row(align=True)
        info_btn.scale_x = 1.0
        info_btn.operator(SE_OT_SelectListInfo.bl_idname, text="", icon='INFO')
        
        # Выпадающий список наборов
        row.prop(context.scene, "se_selectlist_index", text="")
        
        # Кнопка настроек
        settings_btn = row.row(align=True)
        settings_btn.scale_x = 1.0
        settings_btn.operator("se.selectlist_settings", text="", icon='PREFERENCES')
        
        # Кнопка Select
        select_btn = row.row(align=True)
        select_btn.scale_x = 1.0
        
        set_index = int(context.scene.se_selectlist_index)
        if len(context.scene.se_selectlist_sets) > set_index:
            selection_set = context.scene.se_selectlist_sets[set_index]
            
            if selection_set.is_hidden or not selection_set.object_names:
                select_btn.enabled = False
                select_btn.operator(SE_OT_SelectListSelect.bl_idname, text="", icon='RESTRICT_SELECT_OFF')
            else:
                select_btn.enabled = True
                select_btn.operator(SE_OT_SelectListSelect.bl_idname, text="", icon='RESTRICT_SELECT_OFF')
        else:
            select_btn.enabled = False
            select_btn.operator(SE_OT_SelectListSelect.bl_idname, text="", icon='RESTRICT_SELECT_OFF')
        
        # Кнопка Show/Hide
        show_hide_btn = row.row(align=True)
        show_hide_btn.scale_x = 1.0
        
        if len(context.scene.se_selectlist_sets) > set_index:
            selection_set = context.scene.se_selectlist_sets[set_index]
            if selection_set.object_names:
                show_icon = 'HIDE_ON' if selection_set.is_hidden else 'HIDE_OFF'
                show_hide_btn.enabled = True
                show_hide_btn.operator(SE_OT_Objects_ShowHideSelected.bl_idname, text="", icon=show_icon, depress=False)
            else:
                show_hide_btn.enabled = False
                show_hide_btn.operator(SE_OT_Objects_ShowHideSelected.bl_idname, text="", icon='HIDE_OFF', depress=False)
        else:
            show_hide_btn.enabled = False
            show_hide_btn.operator(SE_OT_Objects_ShowHideSelected.bl_idname, text="", icon='HIDE_OFF', depress=False)
        
        # 3. Управление списками выделения (нижняя часть)
        row = box_col.row(align=True)
        
        # Кнопка Clean Missing
        clean_btn = row.row(align=True)
        clean_btn.scale_x = 1.0
        clean_btn.operator(SE_OT_CleanAllSets.bl_idname, text="", icon='BRUSH_DATA')
        
        # Метка с количеством объектов
        if len(context.scene.se_selectlist_sets) > set_index:
            selection_set = context.scene.se_selectlist_sets[set_index]
            item_count = len(selection_set.object_names.split(',')) if selection_set.object_names else 0
            row.label(text=f"  Items: {item_count}")
        else:
            row.label(text="  Items: 0")
        
        # Кнопка Add
        add_btn = row.row(align=True)
        add_btn.scale_x = 1.0
        add_btn.enabled = bool(context.selected_objects)
        add_btn.operator(SE_OT_SelectListAdd.bl_idname, text="", icon='ADD')
        
        # Кнопка Remove
        remove_btn = row.row(align=True)
        remove_btn.scale_x = 1.0
        remove_btn.enabled = bool(context.selected_objects) and any(
            obj.name in set(context.scene.se_selectlist_sets[set_index].object_names.split(','))
            for obj in context.selected_objects
        ) if (len(context.scene.se_selectlist_sets) > set_index and 
            context.scene.se_selectlist_sets[set_index].object_names) else False
        remove_btn.operator(SE_OT_SelectListRemove.bl_idname, text="", icon='REMOVE')
        
        # Кнопка Clear
        clear_btn = row.row(align=True)
        clear_btn.scale_x = 1.0
        if len(context.scene.se_selectlist_sets) > set_index:
            selection_set = context.scene.se_selectlist_sets[set_index]
            clear_btn.enabled = bool(selection_set.object_names)
        else:
            clear_btn.enabled = False
        clear_btn.operator(SE_OT_SelectListClear.bl_idname, text="", icon='X')

    def draw_modifiers_tab(self, context, col):
        """Draw Modifiers tab content - строка с Mirror:Y целиком"""
        # Создаем box с темным фоном
        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False
        
        # Создаем основной column внутри box с align=True
        box_col = box.column(align=True)
        
        # Строка с кнопками Mirror
        row = box_col.row(align=True)
        row.operator(SE_OT_Objects_AddMirrorY.bl_idname, text="Mirror:Y", icon='MOD_MIRROR')
        
        # Проверяем, есть ли Mirror модификаторы у выделенных объектов
        has_mirror = any(
            mod.type == 'MIRROR'
            for obj in context.selected_objects
            if obj.type == 'MESH' and not obj.hide_viewport
            for mod in obj.modifiers
        )
        
        # Clip (без текста)
        clipping_state = False
        if has_mirror:
            # Получаем состояние из активного или последнего выделенного объекта
            active_obj = context.active_object
            if active_obj and active_obj.select_get() and active_obj.type == 'MESH':
                for mod in active_obj.modifiers:
                    if mod.type == 'MIRROR':
                        clipping_state = mod.use_clip
                        break
            else:
                for obj in reversed(context.selected_objects):
                    if obj.type != 'MESH' or obj.hide_viewport:
                        continue
                    for mod in obj.modifiers:
                        if mod.type == 'MIRROR':
                            clipping_state = mod.use_clip
                            break
        
        row.operator(SE_OT_Objects_ToggleMirrorClipping.bl_idname, text="",
            icon='CHECKBOX_HLT' if clipping_state and has_mirror else 'CHECKBOX_DEHLT',
            depress=clipping_state if has_mirror else False
        )
        
        # Realtime
        realtime_state = False
        if has_mirror:
            active_obj = context.active_object
            if active_obj and active_obj.select_get() and active_obj.type == 'MESH':
                for mod in active_obj.modifiers:
                    if mod.type == 'MIRROR':
                        realtime_state = mod.show_viewport
                        break
            else:
                for obj in reversed(context.selected_objects):
                    if obj.type != 'MESH' or obj.hide_viewport:
                        continue
                    for mod in obj.modifiers:
                        if mod.type == 'MIRROR':
                            realtime_state = mod.show_viewport
                            break
        
        row.operator(
            SE_OT_Objects_ToggleMirrorRealtime.bl_idname,
            text="",
            icon='RESTRICT_VIEW_OFF' if realtime_state and has_mirror else 'RESTRICT_VIEW_ON',
            depress=realtime_state if has_mirror else False
        )
        
        # Apply Mirror
        row.operator(SE_OT_Objects_ApplyMirror.bl_idname, text="", icon='CHECKMARK', depress=False)
        # Remove Mirror
        row.operator(SE_OT_Objects_RemoveMirror.bl_idname, text="", icon='X', depress=False)

    def draw_materials_tab(self, context, col):
        """Draw Materials tab content - Link Material, Link Layer2 и кнопки в столбец"""
        # Создаем box с темным фоном
        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False
        
        # Создаем основной column внутри box с align=True
        box_col = box.column(align=True)
        
        # Строка Link Material (новая кнопка)
        row = box_col.row(align=True)
        link_mat_op = row.operator(
            "object.make_links_data",
            text="Link Material",
            icon='LINK_BLEND'
        )
        link_mat_op.type = 'MATERIAL'
        # Кнопка неактивна, если нет выделенных объектов
        row.enabled = bool(context.selected_objects)
        
        # Строка Link Layer2
        row = box_col.row(align=True)
        row.operator(
            SE_OT_LinkSecondLayer.bl_idname,
            text="Link Layer2",
            icon='LINKED'
        )
        
        # Разделитель
        box_col.separator()
        
        # Метка "Show:"
        box_col.label(text="Show:")
        
        # Кнопка Attribute
        box_col.operator(
            "se.set_attribute_display",
            text="Color Attribute",
        )
        
        # Кнопка Color (Multiply)
        box_col.operator(
            SE_OT_SelectMultiplyNode.bl_idname,
            text="BaseColor (Layer1)",
            depress=False
        )
        
        # Кнопка Shadow (Divide)
        box_col.operator(
            SE_OT_SelectDivideNode.bl_idname,
            text="AO/Shadow (Layer2)",
            depress=False
        )

    def draw_create_tab(self, context, col):
        """Draw Create tab content - Make Rope и Make Vant в столбец"""
        # Создаем box с темным фоном
        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False
        
        # Создаем основной column внутри box с align=True
        box_col = box.column(align=True)
        
        # Строка с кнопками веревок/вантов в столбец
        box_col.operator(SE_OT_Objects_MakeRope.bl_idname, text="Make Rope", icon='MOD_CURVE')
        box_col.operator(SE_OT_Objects_MakeVant.bl_idname, text="Make Vant", icon='OUTLINER_OB_CURVE')

    def draw_cleanup_tab(self, context, col):
        """Draw Cleanup tab content - Clear Geometry Data, MultiMat, Empty, Fix .001 names в столбец"""
        # Создаем box с темным фоном
        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False
        
        # Создаем основной column внутри box с align=True
        box_col = box.column(align=True)
        
        box_col.operator(SE_OT_Objects_ClearGeomData.bl_idname, text="Clear Geometry Data", icon='X')
        box_col.separator()
        box_col.operator(SE_OT_Objects_FindMultiMaterial.bl_idname, text="MultiMat", icon='LONGDISPLAY')
        box_col.operator(SE_OT_Objects_FindEmptyMeshes.bl_idname, text="Empty", icon='BORDERMOVE')
        
        # Разделитель
        box_col.separator()
        
        # Строка с кнопкой Fix .001 names и кнопкой настроек
        row = box_col.row(align=True)
        row.operator(SE_OT_FixDotZeroZeroOneNames.bl_idname, text="Fix .001 names", icon='SORTALPHA')
        row.operator("se.fix_names_settings_dialog", text="", icon='PREFERENCES')

    def draw_export_tab(self, context, col):
        """Draw Export tab content - GM export tools"""
        # Создаем box с темным фоном
        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False
        
        # Создаем основной column внутри box с align=True
        box_col = box.column(align=True)
        
        scene_props = context.scene.se_props
        global _session_export_dir
        
        # Основная строка с именем модели и кнопками
        main_row = box_col.row(align=True)
        
        # Метка "Name:" (ширина 0.5)
        label_col = main_row.row(align=True)
        label_col.scale_x = 0.5
        label_col.label(text="Name:")
        
        # Поле ввода (ширина 2.0)
        input_col = main_row.row(align=True)
        input_col.scale_x = 2.0
        input_col.prop(scene_props, "gm_name", text="")
        
        # Кнопка экспорта (ширина 1.0)
        btn_col = main_row.row(align=True)
        btn_col.scale_x = 1.0
        btn_col.enabled = bool(SE_OT_ExportGM.poll(context))
        btn_col.operator(SE_OT_ExportGM.bl_idname, icon='EXPORT', text="")
        
        # Кнопка открытия папки
        folder_btn = main_row.row(align=True)
        folder_btn.scale_x = 1.0
        folder_btn.enabled = bool(scene_props.last_export_dir) or bool(_session_export_dir)
        folder_btn.operator(SE_OT_OpenExportFolder.bl_idname, text="", icon='FILE_FOLDER')


classes = (
    SE_OT_ResetVisibility,
    SelectListName,
    SelectListSet,
    SE_SceneProperties,
    SE_OT_ObjectsPanel_Toggle,
    SE_OT_Objects_MakeRope,
    SE_OT_Objects_MakeVant,
    SE_OT_Objects_FindSelect,
    SE_OT_Objects_FindSelect2,
    SE_OT_Objects_FindSelect3,
    SE_OT_ToggleSearchRow,
    SE_OT_SelectListAdd,
    SE_OT_SelectListRemove,
    SE_OT_SelectListClear,
    SE_OT_CleanAllSets,
    SE_OT_SelectListSelect,
    SE_OT_SelectListInfo,
    SE_OT_SelectListSettings,
    SE_OT_SelectListSettingsDialog,
    SE_OT_Objects_ShowHideSelected,
    SE_OT_Objects_FindMultiMaterial,
    SE_OT_Objects_FindEmptyMeshes,
    SE_OT_Objects_AddMirrorY,
    SE_OT_Objects_ToggleMirrorClipping,
    SE_OT_Objects_ToggleMirrorRealtime,
    SE_OT_Objects_ApplyMirror,
    SE_OT_Objects_RemoveMirror,
    SE_OT_Objects_ClearGeomData,
    SE_OT_SelectMixNode,
    SE_OT_SelectMultiplyNode,
    SE_OT_SelectDivideNode,
    SE_OT_LinkSecondLayer,
    SE_OT_SetAttributeDisplay,
    SE_OT_set_tab,
    SE_OT_tab_button,
    SE_OT_ExportGM,
    SE_OT_OpenExportFolder,
    SE_OT_info,
    SE_OT_FixNamesSettings,
    SE_OT_FixNamesSettingsDialog,
    SE_OT_FixDotZeroZeroOneNames,
    SE_PT_ObjectsPanel,
)

####################################################################################################################
def register():
    global properties_registered, last_known_objects
    
    # Регистрируем классы
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            print(f"Warning: {cls.__name__} already registered - {e}")

    # Регистрируем свойства сцены только если они еще не зарегистрированы
    if not properties_registered:
        # Создаем свойства сцены
        bpy.types.Scene.se_selectlist_names = bpy.props.CollectionProperty(
            type=SelectListName,
            name="Selection List Names"
        )
        
        bpy.types.Scene.se_selectlist_sets = bpy.props.CollectionProperty(
            type=SelectListSet,
            name="Selection Sets"
        )
        
        bpy.types.Scene.se_selectlist_index = bpy.props.EnumProperty(
            items=update_selectlist_items,
            name="Selection Set",
            description="Select which set to work with"
        )
        
        bpy.types.Scene.se_obj_to_hide = bpy.props.StringProperty(default="")
        bpy.types.Scene.se_mirror_realtime = bpy.props.BoolProperty(default=True)
        bpy.types.Scene.se_objects_panel_collapsed = bpy.props.BoolProperty(default=False)
        
        bpy.types.Scene.se_auto_clean_sets = bpy.props.BoolProperty(
            name="Auto Clean",
            description="Automatically clean missing objects before operations.\nDisable if experiencing performance issues with selection sets",
            default=True
        )
        
        # Свойство для активной вкладки (EDIT удален)
        bpy.types.Scene.se_active_tab = bpy.props.EnumProperty(
            name="Tab",
            description="Choose a tab",
            items=[
                ('HOME', "Home", ""),
                ('MODIFIERS', "Modifiers", ""),
                ('MATERIALS', "Materials", ""),
                ('CREATE', "Create", ""),
                ('CLEANUP', "Cleanup", ""),
                ('EXPORT', "Export", ""),
            ],
            default='HOME'
        )
        
        # Регистрируем se_props как PointerProperty
        bpy.types.Scene.se_props = bpy.props.PointerProperty(type=SE_SceneProperties)

        # Регистрируем настройки для Fix .001 names
        bpy.types.Scene.se_fix_names_settings = bpy.props.PointerProperty(type=SE_OT_FixNamesSettings)
        
        properties_registered = True

    # Добавляем обработчик для загрузки файла
    bpy.app.handlers.load_post.append(init_last_known_objects)

    # Property to track if multiple search rows are expanded
    bpy.types.Scene.se_search_rows_expanded = bpy.props.BoolProperty(
        name="Expand Search Rows",
        description="Expand to show multiple search rows",
        default=False
    )

    # Properties for additional search rows
    bpy.types.Scene.se_objects_search_text2 = bpy.props.StringProperty(
        name="Search Text 2",
        description="Text to search for in object names",
        default=""
    )

    bpy.types.Scene.se_objects_search_text3 = bpy.props.StringProperty(
        name="Search Text 3",
        description="Text to search for in object names",
        default=""
    )

    bpy.types.Scene.se_search_prefix_suffix2 = bpy.props.BoolProperty(
        name="Search Prefix/Suffix Only 2",
        description="Search only at beginning or end of object name",
        default=False
    )

    bpy.types.Scene.se_search_prefix_suffix3 = bpy.props.BoolProperty(
        name="Search Prefix/Suffix Only 3",
        description="Search only at beginning or end of object name",
        default=False
    )

    bpy.types.Scene.se_search_in_baking2 = bpy.props.BoolProperty(
        name="Search in BAKING Collection 2",
        description="Include objects from BAKING collection in search",
        default=False
    )

    bpy.types.Scene.se_search_in_baking3 = bpy.props.BoolProperty(
        name="Search in BAKING Collection 3",
        description="Include objects from BAKING collection in search",
        default=False
    )

    # Property to track if search row 2 is expanded
    bpy.types.Scene.se_search_row2_expanded = bpy.props.BoolProperty(
        name="Expand Search Row 2",
        description="Show third search row",
        default=False
    )

    # Property to track if search row 2 is visible
    bpy.types.Scene.se_show_search_row2 = bpy.props.BoolProperty(
        name="Show Search Row 2",
        description="Show second search row",
        default=False
    )

    # Property to track if search row 3 is visible
    bpy.types.Scene.se_show_search_row3 = bpy.props.BoolProperty(
        name="Show Search Row 3",
        description="Show third search row",
        default=False
    )
    
    # Инициализируем last_known_objects
    init_last_known_objects(None)

def unregister():
    global properties_registered
    
    # Показываем все объекты и сбрасываем состояние кнопок
    for scene in bpy.data.scenes:
        if hasattr(scene, 'se_selectlist_sets'):
            for selection_set in scene.se_selectlist_sets:
                if selection_set.object_names:
                    # Делаем все объекты видимыми
                    for obj_name in selection_set.object_names.split(','):
                        obj = bpy.data.objects.get(obj_name)
                        if obj:
                            obj.hide_viewport = False
                
                # Сбрасываем состояние кнопки в "Показано"
                selection_set.is_hidden = False
    
    # Удаляем обработчики загрузки
    if init_last_known_objects in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(init_last_known_objects)
    
    # Удаляем классы в обратном порядке
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    
    # Удаляем свойства сцены только если они зарегистрированы
    if properties_registered:
        scene_props = [
            'se_selectlist_names',
            'se_selectlist_sets',
            'se_selectlist_index',
            'se_objects_panel_collapsed',
            'se_mirror_realtime',
            'se_obj_to_hide',
            'se_active_tab',
            'se_auto_clean_sets',
            'se_props',
            'se_fix_names_settings'
        ]
        
        for prop in scene_props:
            if hasattr(bpy.types.Scene, prop):
                delattr(bpy.types.Scene, prop)
        
        properties_registered = False