bl_info = {
    "name": "StormEngineTools",
    "author": "Wulfrein",
    "version": (1, 4, 14), # кнопка "Fix .001 names"
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > StormEngineTools",
    "description": "Color Attributes and UV Maps management tools",
    "category": "Object",
}

import bpy
from bpy.types import AddonPreferences
from bpy.props import (FloatVectorProperty, StringProperty,
                      BoolProperty, IntProperty, FloatProperty)

# Global variable for session export path
_session_export_dir = ""

# ------------------------------------------------------------------------
# Preferences
# ------------------------------------------------------------------------

class SE_AddonPreferences(AddonPreferences):
    bl_idname = __name__

    # Используется в UV Maps и Color Attributes
    default_uv_name: StringProperty(
        name="Default UV Map Name",
        default="UVMap_normals",
        description="Default name for new UV maps"
    )

    # Используется в Color Attributes
    default_color_attr_name: StringProperty(
        name="Default Color Attribute Name",
        default="Col",
        description="Default name for new color attributes"
    )

    # Используется в Color Attributes
    default_gray_color: FloatVectorProperty(
        name="Default Gray Color",
        subtype='COLOR_GAMMA',
        size=3,
        default=(0.5, 0.5, 0.5),
        min=0.0, max=1.0,
        description="Default gray color for vertex painting"
    )

    # Используется в Color Attributes
    patch_color: FloatVectorProperty(
        name="Patch Color",
        subtype='COLOR_GAMMA',
        size=3,
        default=(0.9, 0.9, 0.6),
        min=0.0, max=1.0,
        description="Patch color for vertex painting"
    )

    # Используется в Color Attributes
    watermask_color: FloatVectorProperty(
        name="Watermask Color",
        subtype='COLOR_GAMMA',
        size=3,
        default=(0.2, 0.4, 0.6),
        min=0.0, max=1.0,
        description="Watermask color for vertex painting"
    )

    # Используется в Objects (Ropes)
    rope_depth: FloatProperty(
        name="Rope Depth",
        default=0.02,
        min=0.01,
        max=1.0,
        step=0.1,
        precision=3,
        description="Bevel depth for ropes"
    )

    # Используется в Objects (Ropes)
    rope_resolution: IntProperty(
        name="Rope Resolution",
        default=0,
        min=0,
        max=4,
        description="Bevel resolution for ropes"
    )

    # Используется в Objects (Vants)
    vant_depth: FloatProperty(
        name="Vant Depth",
        default=0.03,
        min=0.01,
        max=1.0,
        step=0.1,
        precision=3,
        description="Bevel depth for vants"
    )

    # Используется в Objects (Vants)
    vant_resolution: IntProperty(
        name="Vant Resolution",
        default=1,
        min=0,
        max=4,
        description="Bevel resolution for vants"
    )

    baking_collection_color: bpy.props.EnumProperty(
        name="Baking Collection Color",
        description="Color tag for BAKING collection",
        items=[
            ('COLOR_01', "Color 1", "Red"),
            ('COLOR_02', "Color 2", "Orange"),
            ('COLOR_03', "Color 3", "Yellow"),
            ('COLOR_04', "Color 4", "Green"),
            ('COLOR_05', "Color 5", "Blue"),
            ('COLOR_06', "Color 6", "Violet"),
            ('COLOR_07', "Color 7", "Pink"),
            ('COLOR_08', "Color 8", "Brown"),
        ],
        default='COLOR_01'
    )

    # UV Maps Panel Settings
    enable_uvmaps_panel: BoolProperty(
        name="Enable UV Maps Panel",
        description="Activates the UV Maps panel in the UI\n"
                   "Contains tools for managing UV maps: renaming, creating,\n"
                   "deleting, and setting active UV layers",
        default=True
    )

    uvmaps_panel_expanded: BoolProperty(
        name="Expand UV Maps Panel Settings",
        description="Show/Hide UV Maps Panel configuration options",
        default=True
    )

    # Color Attributes Panel Settings
    enable_color_attr_panel: BoolProperty(
        name="Enable Color Attributes Panel",
        description="Activates the Color Attributes panel in the UI\n"
                   "Contains tools for managing color attributes: creating,\n"
                   "painting and displaying vertex colors",
        default=True
    )

    color_attr_panel_expanded: BoolProperty(
        name="Expand Color Attributes Panel Settings",
        description="Show/Hide Color Attributes Panel configuration options",
        default=True
    )

    # Objects Panel Settings
    enable_objects_panel: BoolProperty(
        name="Enable Objects Panel",
        description="Activates the Objects panel in the UI\n"
                   "Contains tools for object conversion and selection",
        default=True
    )

    objects_panel_expanded: BoolProperty(
        name="Expand Objects Panel Settings",
        description="Show/Hide Objects Panel configuration options",
        default=True
    )

    # Baking Panel Settings
    enable_baking_panel: BoolProperty(
        name="Enable Baking Panel",
        description="Activates the Baking panel in the UI\n"
                   "Contains tools for baking setup and time presets",
        default=True
    )

    baking_panel_expanded: BoolProperty(
        name="Expand Baking Panel Settings",
        description="Show/Hide Baking Panel configuration options",
        default=True
    )

    # Export preferences
    main_empty_name: StringProperty(
        name="Main Empty Name",
        description="Name of the root EMPTY object that resets the prefix in export filename",
        default="_main",
        maxlen=64,
    )

    save_paths_in_blend: BoolProperty(
        name="Save GM export paths in .blend file",
        description="When enabled, last GM export paths will be saved in the .blend file",
        default=False,
    )

    show_debug: BoolProperty(
        name="Show Debug Info",
        default=False,
    )

#############################################################################################################
    def draw(self, context):
        layout = self.layout

        # 2. Панель UV Maps (новая)
        uvmaps_box = layout.box()
        uvmaps_row = uvmaps_box.row(align=True)
        
        # Чекбокс включения панели UV Maps
        uvmaps_row.prop(
            self, 
            "enable_uvmaps_panel",
            text="",
            icon='CHECKBOX_HLT' if self.enable_uvmaps_panel else 'CHECKBOX_DEHLT',
            emboss=False
        )
        
        # Тонкая стрелка свернуть/развернуть
        uvmaps_row.prop(
            self,
            "uvmaps_panel_expanded",
            text="",
            icon='DOWNARROW_HLT' if self.uvmaps_panel_expanded else 'RIGHTARROW',
            emboss=False
        )
        
        # Заголовок панели
        uvmaps_row.label(text="UV Maps Panel Settings")

        # Содержимое панели настроек UV Maps
        if self.uvmaps_panel_expanded:
            uvmaps_col = uvmaps_box.column(align=True)
            
            # Настройка имени UV карты по умолчанию
            row = uvmaps_col.row(align=True)

            split = row.split(factor=0.4, align=True)
            label_col = split.column(align=True)
            label_col.alignment = 'RIGHT'
            label_col.label(text="Default UV Map Name:")
            row = split.row(align=True)

            row.prop(self, "default_uv_name", text="")
            reset = row.row(align=True)
            reset.scale_x = 1.0
            op = reset.operator("wm.context_set_value", text="", icon='LOOP_BACK')
            op.data_path = f"preferences.addons['{__name__}'].preferences.default_uv_name"
            op.value = "'UVMap_normals'"

        # 3. Панель Color Attributes
        color_attr_box = layout.box()
        color_attr_row = color_attr_box.row(align=True)
        
        # Чекбокс включения панели Color Attributes
        color_attr_row.prop(
            self, 
            "enable_color_attr_panel",
            text="",
            icon='CHECKBOX_HLT' if self.enable_color_attr_panel else 'CHECKBOX_DEHLT',
            emboss=False
        )
        
        # Тонкая стрелка свернуть/развернуть
        color_attr_row.prop(
            self,
            "color_attr_panel_expanded",
            text="",
            icon='DOWNARROW_HLT' if self.color_attr_panel_expanded else 'RIGHTARROW',
            emboss=False
        )
        
        # Заголовок панели
        color_attr_row.label(text="Color Attributes Panel Settings")

        # Содержимое панели настроек Color Attributes
        if self.color_attr_panel_expanded:
            color_attr_col = color_attr_box.column(align=True)
            
            # Настройка имени Color Attribute по умолчанию
            row = color_attr_col.row(align=True)
            
            split = row.split(factor=0.4, align=True)
            label_col = split.column(align=True)
            label_col.alignment = 'RIGHT'
            label_col.label(text="Color Attributes Default Name:")
            row = split.row(align=True)

            row.prop(self, "default_color_attr_name", text="")
            reset = row.row(align=True)
            reset.scale_x = 1.0
            op = reset.operator("wm.context_set_value", text="", icon='LOOP_BACK')
            op.data_path = f"preferences.addons['{__name__}'].preferences.default_color_attr_name"
            op.value = "'Col'"

            color_attr_col.separator()

            # Color settings
            colors = [
                ("default_gray_color", "Default Gray Color", (0.5, 0.5, 0.5)),
                ("patch_color", "Patch Color", (0.9, 0.9, 0.6)),
                ("watermask_color", "Watermask Color", (0.2, 0.4, 0.6))
            ]

            for prop, label, default in colors:
                row = color_attr_col.row(align=True)
                
                split = row.split(factor=0.4, align=True)
                label_col = split.column(align=True)
                label_col.alignment = 'RIGHT'
                label_col.label(text=f"{label}:")
                row = split.row(align=True)

                row.prop(self, prop, text="")
                reset = row.row(align=True)
                reset.scale_x = 1.0
                op = reset.operator("wm.context_set_value", text="", icon='LOOP_BACK')
                op.data_path = f"preferences.addons['{__name__}'].preferences.{prop}"
                op.value = repr(default)

        # 4. Панель Objects (новая) - содержит Create Tab и Export Tab
        objects_box = layout.box()
        objects_row = objects_box.row(align=True)
        
        # Чекбокс включения панели Objects
        objects_row.prop(
            self, 
            "enable_objects_panel",
            text="",
            icon='CHECKBOX_HLT' if self.enable_objects_panel else 'CHECKBOX_DEHLT',
            emboss=False
        )
        
        # Тонкая стрелка свернуть/развернуть
        objects_row.prop(
            self,
            "objects_panel_expanded",
            text="",
            icon='DOWNARROW_HLT' if self.objects_panel_expanded else 'RIGHTARROW',
            emboss=False
        )
        
        # Заголовок панели
        objects_row.label(text="Object Panel Settings")

        # Содержимое панели настроек Objects
        if self.objects_panel_expanded:
            objects_col = objects_box.column(align=True)
            
            # Create Tab Settings
            create_tab_row = objects_col.row(align=True)
            # Отступ для визуальной вложенности
            create_tab_row.label(text="", icon='BLANK1')
            # Иконка MESH_CUBE
            create_tab_row.label(text="", icon='MESH_CUBE')
            # Заголовок
            create_tab_row.label(text="Create Tab Settings")
            
            # Настройки Ropes
            ropes_row = objects_col.row(align=True)
            ropes_row.label(text="", icon='BLANK1')
            ropes_row.label(text="", icon='BLANK1')
            split = ropes_row.split(factor=0.4, align=True)
            split.label(text="Ropes:")
            row = split.row(align=True)
            row.prop(self, "rope_depth", text="Depth")
            row.prop(self, "rope_resolution", text="Resolution")
            
            # Настройки Vants
            vants_row = objects_col.row(align=True)
            vants_row.label(text="", icon='BLANK1')
            vants_row.label(text="", icon='BLANK1')
            split = vants_row.split(factor=0.4, align=True)
            split.label(text="Vants:")
            row = split.row(align=True)
            row.prop(self, "vant_depth", text="Depth")
            row.prop(self, "vant_resolution", text="Resolution")
            
            objects_col.separator()
            
            # Export Tab Settings
            export_tab_row = objects_col.row(align=True)
            # Отступ для визуальной вложенности
            export_tab_row.label(text="", icon='BLANK1')
            # Иконка EXPORT
            export_tab_row.label(text="", icon='EXPORT')
            # Заголовок
            export_tab_row.label(text="Export Tab Settings")
            
            # Настройки Export
            # Настройка имени Main Empty
            main_empty_row = objects_col.row(align=True)
            main_empty_row.label(text="", icon='BLANK1')
            main_empty_row.label(text="", icon='BLANK1')
            split = main_empty_row.split(factor=0.4, align=True)
            split.label(text="Main Empty Name:")
            split.prop(self, "main_empty_name", text="")
            
            # Строка с галкой сохранения путей
            save_paths_row = objects_col.row(align=True)
            save_paths_row.label(text="", icon='BLANK1')
            save_paths_row.label(text="", icon='BLANK1')
            split = save_paths_row.split(factor=0.4, align=True)
            split.prop(self, "save_paths_in_blend")
            
            # Строка сохранённого пути (показываем только если опция включена)
            if self.save_paths_in_blend:
                saved_path_row = objects_col.row(align=True)
                saved_path_row.label(text="", icon='BLANK1')
                saved_path_row.label(text="", icon='BLANK1')
                saved_path_row.label(icon='FILE_BLEND')
                
                # Отображаем путь или сообщение
                saved_path = context.scene.se_props.last_export_dir
                if saved_path:
                    saved_path_row.label(text=saved_path)
                else:
                    saved_path_row.label(text="[No saved export path]")
                
                # Кнопка обнуления пути
                op = saved_path_row.operator('se.reset_paths', text="", icon='X')
                op.path_type = 'SAVED'

        # 5. Панель Baking (новая)
        baking_box = layout.box()
        baking_row = baking_box.row(align=True)
        
        # Чекбокс включения панели Baking
        baking_row.prop(
            self, 
            "enable_baking_panel",
            text="",
            icon='CHECKBOX_HLT' if self.enable_baking_panel else 'CHECKBOX_DEHLT',
            emboss=False
        )
        
        # Тонкая стрелка свернуть/развернуть
        baking_row.prop(
            self,
            "baking_panel_expanded",
            text="",
            icon='DOWNARROW_HLT' if self.baking_panel_expanded else 'RIGHTARROW',
            emboss=False
        )
        
        # Заголовок панели
        baking_row.label(text="Baking Panel Settings")

        # Содержимое панели настроек Baking
        if self.baking_panel_expanded:
            baking_col = baking_box.column(align=True)
            
            # Baking Collection Color
            row = baking_col.row(align=True)
            
            split = row.split(factor=0.4, align=True)
            label_col = split.column(align=True)
            label_col.alignment = 'RIGHT'
            label_col.label(text="Baking Collection Color:")
            row = split.row(align=True)
            
            # Color buttons row
            colors_row = row.row(align=True)
            colors_row.scale_x = 1.0
            colors_row.scale_y = 1.2

            # Создаем кнопки для каждого цвета
            for i in range(1, 9):
                color_id = f'COLOR_0{i}'
                icon = f'COLLECTION_COLOR_0{i}'
                op = colors_row.operator(
                    "se.set_baking_collection_color",
                    text="", 
                    icon=icon
                )
                op.color = color_id

class SE_OT_SetBakingCollectionColor(bpy.types.Operator):
    """Set BAKING collection color"""
    bl_idname = "se.set_baking_collection_color"
    bl_label = "Set BAKING Collection Color"
    
    color: bpy.props.StringProperty()  # COLOR_01 - COLOR_08
    
    def execute(self, context):
        # Устанавливаем цвет в настройках аддона
        addon_name = __name__.split(".")[0]  # Получаем имя аддона из модуля
        prefs = context.preferences.addons[addon_name].preferences
        prefs.baking_collection_color = self.color
        
        # Применяем цвет к существующей коллекции BAKING
        baking_collection = bpy.data.collections.get("BAKING")
        if baking_collection:
            baking_collection.color_tag = self.color
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------
# Global variable for session export path
_session_export_dir = ""

class SE_OT_ResetPaths(bpy.types.Operator):
    """Reset export paths"""
    bl_idname = "se.reset_paths"
    bl_label = "Reset Path"
    
    path_type: bpy.props.StringProperty(default='SESSION')
    
    def execute(self, context):
        global _session_export_dir
        if self.path_type == 'SESSION':
            _session_export_dir = ""
        else:
            context.scene.se_props.last_export_dir = ""
        return {'FINISHED'}

# Update classes tuple
classes = (
    SE_AddonPreferences,
    SE_OT_SetBakingCollectionColor,
    SE_OT_ResetPaths,
)

def register():
    print("### StormEngineTools: Registering...")
    for cls in classes:
        bpy.utils.register_class(cls)
    print("### StormEngineTools: Classes registered!")

    # Scene properties
    bpy.types.Scene.se_time_preset = StringProperty(
        name="Time Preset",
        description="Current time preset",
        default="Day1"
    )
    
    bpy.types.Scene.se_uv_name = StringProperty(
        name="Name",
        default="UVMap_normals",
        description="Name for UV map operations"
    )

    bpy.types.Scene.se_color_attr_name = StringProperty(
        name="Attribute Name",
        default="Col",
        description="Name for new color attribute"
    )

    bpy.types.Scene.se_vertex_color = FloatVectorProperty(
        name="Vertex Color",
        subtype='COLOR_GAMMA',
        size=3,
        default=(0.5, 0.5, 0.5),
        min=0.0, max=1.0,
        description="Color for vertex painting"
    )

    bpy.types.Scene.se_settings_panel_collapsed = BoolProperty(
        name="Settings Panel Collapsed",
        default=True
    )

    bpy.types.Scene.se_uv_index = IntProperty(
        name="UV ID",
        default=1,
        min=1,
        max=10,
        description="UV Map index to activate (1-10)"
    )

    bpy.types.Scene.se_uv_settings_collapsed = BoolProperty(
        name="UV Advanced Panel Collapsed",
        default=True,
        description="Show/Hide UV Options"
    )

    bpy.types.Scene.se_original_shading_type = StringProperty(
        name="Original Shading Type",
        default='SOLID',
        description="Saved shading type for display mode"
    )

    bpy.types.Scene.se_original_color_type = StringProperty(
        name="Original Color Type",
        default='VERTEX',
        description="Saved color type for display mode"
    )
    
    bpy.types.Scene.se_search_prefix_suffix = BoolProperty(
        name="Search Prefix/Suffix",
        default=True,
        description="Search only at beginning or end of object names"
    )

    bpy.types.Scene.se_search_in_baking = BoolProperty(
        name="Search in BAKING",
        default=False,
        description="Include objects from BAKING collection in search results"
    )

    bpy.types.Scene.se_objects_search_text = StringProperty(
        name="Search Text",
        default="",
        description="Text to search in object names"
    )
    
    # Import submodules
    from . import uvmaps, color_attr, objects, baking
    uvmaps.register()
    color_attr.register()
    objects.register()
    baking.register()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Unregister submodules
    from . import uvmaps, color_attr, objects, baking
    uvmaps.unregister()
    color_attr.unregister()
    objects.unregister()
    baking.unregister()
    
if __name__ == "__main__":
    register()