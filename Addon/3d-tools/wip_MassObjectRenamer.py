"""
================================================================================
MASS OBJECTS RENAMER - Аддон для Blender
================================================================================
НАЗНАЧЕНИЕ:
    Массовое переименование выбранных объектов с автоматической нумерацией.

ПРИНЦИП РАБОТЫ:
    1. Без пользовательского имени (галка выключена):
        - Запоминается имя АКТИВНОГО объекта
        - Отбрасываются постфиксы Blender (.001, .002 и т.д.)
        - Отбрасываются постфиксы с подчёркиванием и цифрами (_1, _2, _01, _02 и т.д.)
        - Все выбранные объекты переименовываются в порядке аутлайнера:
          "Имя_1", "Имя_2", "Имя_3"...
       
    2. С пользовательским именем (галка включена):
        - Используется текст из поля ввода
        - Все выбранные объекты переименовываются:
          "Текст_1", "Текст_2", "Текст_3"...
================================================================================
"""

bl_info = {
    "name": "Mass Objects Renamer",
    "author": "Wulfrein",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "3D Viewport > Sidebar > StormEngineWIP",
    "description": "Bulk rename objects with numbering",
    "category": "Object",
}

import bpy
import re

# Функция для очистки имени от постфиксов
def clean_object_name(name):
    """
        Removes suffixes from object name:
        - .001, .002 (Blender auto-numbering)
        - _1, _2, _01, _02 (manual numbering)
    """
    # Удаляем суффикс Blender вида .001, .002 и т.д.
    name = re.sub(r"\.\d{3,}$", "", name)
    
    # Удаляем суффикс с подчёркиванием и цифрами: _1, _2, _01, _02, _123 и т.д.
    name = re.sub(r"_\d+$", "", name)
    
    return name


# Оператор переименования объектов
class MASSRENAMER_OT_rename_objects(bpy.types.Operator):
    """Rename selected objects according to the settings"""
    bl_idname = "object.mass_renamer_rename"
    bl_label = "Rename"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.mass_renamer_props

        # Получаем список выбранных объектов
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        # Получаем активный объект
        active_obj = context.active_object
        if not active_obj or active_obj not in selected_objects:
            self.report({'WARNING'}, "Active object must be among selected objects")
            return {'CANCELLED'}

        # Сортируем выбранные объекты по порядку в аутлайнере (по имени)
        selected_sorted = sorted(selected_objects, key=lambda obj: obj.name)

        # Определяем базовое имя для переименования
        if props.use_custom_name:
            # Режим с пользовательским именем
            base_name = props.custom_name.strip()
            if not base_name:
                self.report({'ERROR'}, "Custom name field is empty")
                return {'CANCELLED'}
        else:
            # Режим с именем активного объекта (очищаем от всех постфиксов)
            base_name = clean_object_name(active_obj.name)
            # Дополнительная проверка: если имя стало пустым, используем "Object"
            if not base_name:
                base_name = "Object"

        # Выполняем переименование с добавлением порядкового номера
        for idx, obj in enumerate(selected_sorted, start=1):
            new_name = f"{base_name}_{idx}"
            obj.name = new_name

        self.report({'INFO'}, f"Renamed {len(selected_sorted)} objects. Base: {base_name}")
        return {'FINISHED'}


# Панель в боковой панели 3D Viewport
class MASSRENAMER_PT_panel(bpy.types.Panel):
    """Panel in the 3D Viewport sidebar"""
    bl_label = "Mass Objects Renamer"
    bl_idname = "OBJECT_PT_mass_renamer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "StormEngineWIP"  # Отдельная вкладка на боковой панели

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.mass_renamer_props

        # Строка с галкой (только иконка) и полем ввода
        row = layout.row(align=True)
        
        # Галка без текста, только иконка
        row.prop(props, "use_custom_name", text="", icon='CHECKBOX_HLT' if props.use_custom_name else 'CHECKBOX_DEHLT')
        
        # Поле ввода (становится неактивным, если галка выключена)
        col = row.column(align=True)
        col.prop(props, "custom_name", text="")
        col.enabled = props.use_custom_name

        # Разделитель
        layout.separator()
        
        # Кнопка запуска переименования
        layout.operator("object.mass_renamer_rename", text="Rename", icon='SORTALPHA')


# Свойства аддона
class MASSRENAMER_Props(bpy.types.PropertyGroup):
    use_custom_name: bpy.props.BoolProperty(
        name="Use Custom Name",
        description="Enable to use custom base name instead of active object name",
        default=False
    )
    custom_name: bpy.props.StringProperty(
        name="New Name",
        description="Base name for renaming (suffix _1, _2, ... will be added)",
        default="Object"
    )


# Регистрация классов
classes = [
    MASSRENAMER_Props,
    MASSRENAMER_OT_rename_objects,
    MASSRENAMER_PT_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mass_renamer_props = bpy.props.PointerProperty(type=MASSRENAMER_Props)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mass_renamer_props

if __name__ == "__main__":
    register()