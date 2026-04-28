import bpy
from bpy.types import Panel, Operator
from bpy.props import FloatProperty

class SE_OT_ColorAttr_FullSet(Operator):
    """Removes all color attributes and creates new ones:\n - Name: from 'Name' field\n - Color: from color picker\n - Domain: Face Corner\n - Type: Byte Color"""
    bl_idname = "se.colorattr_fullset"
    bl_label = "FullSet Color Attributes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        scene = context.scene
        prefs = context.preferences.addons[__name__.split(".")[0]].preferences
        processed = 0
        skipped = []

        color_attr_name = scene.se_color_attr_name if scene.se_color_attr_name != "Col" else prefs.default_color_attr_name

        original_mode = context.object.mode if context.object else 'OBJECT'
        original_active = context.active_object
        active_in_selection = original_active and original_active in context.selected_objects
        last_processed = None

        for obj in context.selected_objects:
            # Проверяем, можно ли применить цветовые атрибуты к объекту
            if obj.type != 'MESH' or not obj.data.polygons:
                skipped.append(obj.name)
                continue

            try:
                processed += 1
                last_processed = obj
                context.view_layer.objects.active = obj

                if obj.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

                mesh = obj.data

                while mesh.color_attributes:
                    mesh.color_attributes.remove(mesh.color_attributes[0])

                mesh.color_attributes.new(
                    name=color_attr_name,
                    type='BYTE_COLOR',
                    domain='CORNER'
                )

                bpy.ops.object.mode_set(mode='VERTEX_PAINT')
                bpy.data.brushes["Draw"].color = scene.se_vertex_color
                bpy.ops.paint.vertex_color_set()

            except Exception as e:
                skipped.append(obj.name)
                print(f"Error processing {obj.name}: {str(e)}")

        # Restore original active object and mode
        if active_in_selection and original_active:
            context.view_layer.objects.active = original_active
        elif last_processed:
            context.view_layer.objects.active = last_processed
        bpy.ops.object.mode_set(mode=original_mode)

        if processed > 0:
            self.report({'INFO'}, f"Processed {processed} objects")
        if skipped:
            self.report({'WARNING'}, f"Skipped {len(skipped)} objects: {', '.join(skipped)}")

        return {'FINISHED'}

class SE_OT_ColorAttr_ShowHide(Operator):
    """Toggle vertex colors visibility between solid mode and saved display mode"""
    bl_idname = "se.colorattr_show_hide"
    bl_label = "Show/Hide Vertex Colors"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        shading = context.space_data.shading
        scene = context.scene

        # Сохраняем текущее состояние перед изменением
        if not hasattr(scene, 'se_original_shading_type'):
            scene.se_original_shading_type = shading.type
            scene.se_original_color_type = shading.color_type

        # Переключение режима с сообщениями в Info Log
        if shading.color_type == 'VERTEX' and shading.type == 'SOLID':
            shading.type = scene.se_original_shading_type
            shading.color_type = scene.se_original_color_type
            self.report({'INFO'}, "Original display restored")
        else:
            if not (shading.color_type == 'VERTEX' and shading.type == 'SOLID'):
                scene.se_original_shading_type = shading.type
                scene.se_original_color_type = shading.color_type
            shading.type = 'SOLID'
            shading.color_type = 'VERTEX'
            self.report({'INFO'}, "Vertex colors shown")

        # Обновление интерфейса
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        return {'FINISHED'}

class SE_OT_ColorAttr_SaveDisplay(Operator):
    """Save current display mode (will be remembered even after Blender restart)"""
    bl_idname = "se.colorattr_save_display"
    bl_label = "Save Display Mode"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.se_original_shading_type = bpy.context.space_data.shading.type
        context.scene.se_original_color_type = bpy.context.space_data.shading.color_type
        self.report({'INFO'}, "Display mode saved (will persist after restart)")
        return {'FINISHED'}

class SE_OT_ColorAttr_SetDefaultGray(Operator):
    """Set default gray color"""
    bl_idname = "se.colorattr_set_default_gray"
    bl_label = "Default Gray"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_name = __name__.split(".")[0]  # Получаем имя аддона из модуля
        context.scene.se_vertex_color = context.preferences.addons[addon_name].preferences.default_gray_color
        return {'FINISHED'}

class SE_OT_ColorAttr_SetPatchColor(Operator):
    """Set PTC color"""
    bl_idname = "se.colorattr_set_patch_color"
    bl_label = "Patch"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_name = __name__.split(".")[0]  # Получаем имя аддона из модуля
        context.scene.se_vertex_color = context.preferences.addons[addon_name].preferences.patch_color
        return {'FINISHED'}

class SE_OT_ColorAttr_SetWatermaskColor(Operator):
    """Set WTR color"""
    bl_idname = "se.colorattr_set_watermask_color"
    bl_label = "Watermask"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_name = __name__.split(".")[0]  # Получаем имя аддона из модуля
        context.scene.se_vertex_color = context.preferences.addons[addon_name].preferences.watermask_color
        return {'FINISHED'}

class SE_OT_ColorAttr_AdjustColor(Operator):
    """Adjust color brightness"""
    bl_idname = "se.colorattr_adjust_color"
    bl_label = "Adjust Color"
    bl_options = {'REGISTER', 'UNDO'}

    adjustment: FloatProperty()

    def execute(self, context):
        color = list(context.scene.se_vertex_color)
        for i in range(3):
            color[i] = max(0.0, min(1.0, color[i] + self.adjustment))
        context.scene.se_vertex_color = color
        return {'FINISHED'}

class SE_OT_ColorAttr_ResetName(Operator):
    """Reset color attribute name to default from addon preferences"""
    bl_idname = "se.colorattr_reset_name"
    bl_label = "Reset Color Attribute Name"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_name = __name__.split(".")[0]  # Получаем имя аддона из модуля
        context.scene.se_color_attr_name = context.preferences.addons[addon_name].preferences.default_color_attr_name
        return {'FINISHED'}

class SE_OT_CAAdvanced_Toggle(Operator):
    """Show/Hide More Options"""
    bl_idname = "se.caadvanced_toggle"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.se_settings_panel_collapsed = not context.scene.se_settings_panel_collapsed
        return {'FINISHED'}

class SE_PT_ColorAttrPanel(Panel):
    bl_label = "Color Attributes"
    bl_idname = "SE_PT_ColorAttrPanel"
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
            return prefs.preferences.enable_color_attr_panel
        return False


    def draw(self, context):
        layout = self.layout
        scene = context.scene
        shading = context.space_data.shading

        # Основной контейнер с выравниванием
        main_col = layout.column(align=True)

        # Первая строка с кнопками
        row = main_col.row(align=True)

        # Левый столбец с двумя кнопками
        left_col = row.column(align=True)
        left_col.scale_x = 1.0

        # Кнопка Default Gray (иконка COLOR_GREEN)
        left_col.operator(
            SE_OT_ColorAttr_SetDefaultGray.bl_idname,
            text="",
            icon='COLOR_GREEN'
        )

        # Кнопка переключения CA_Advanced (новая реализация)
        left_col.operator(
            SE_OT_CAAdvanced_Toggle.bl_idname,
            text="",
            icon='DISCLOSURE_TRI_DOWN' if not scene.se_settings_panel_collapsed else 'DISCLOSURE_TRI_RIGHT',
            emboss=True
        )

        # Кнопка FullSet (высота x2)
        fullset_col = row.column(align=True)
        fullset_col.scale_y = 2.0
        fullset_col.operator(
            SE_OT_ColorAttr_FullSet.bl_idname,
            text="FullSet ColorAttributes"
        )

        # Вертикальный столбец для кнопок управления отображением
        display_col = row.column(align=True)

        # Определяем текущее состояние отображения цветов
        is_showing_colors = (shading.color_type == 'VERTEX' and shading.type == 'SOLID')

        # Кнопка Show/Hide (без текста, меняет иконку)
        show_hide_op = display_col.operator(
            SE_OT_ColorAttr_ShowHide.bl_idname,
            text="",
            icon='HIDE_OFF' if is_showing_colors else 'HIDE_ON'
        )

        # Кнопка Save Display Mode
        display_col.operator(
            SE_OT_ColorAttr_SaveDisplay.bl_idname,
            text="",
            icon='IMAGE_BACKGROUND'
        )

        # Настройки (сворачиваемая панель)
        if not scene.se_settings_panel_collapsed:
            box = main_col.box()
            settings_col = box.column(align=True)
            
            # Поле имени атрибута с кнопкой сброса
            row = settings_col.row(align=True)
            row.prop(scene, "se_color_attr_name", text="Name")

            reset_col = row.row(align=True)
            reset_col.scale_x = 1.0
            reset_col.operator(
                SE_OT_ColorAttr_ResetName.bl_idname,
                text="",
                icon='LOOP_BACK'
            )

            # Поле цвета с информацией о яркости
            row = settings_col.row(align=False)
            color = scene.se_vertex_color
            h, s, v = color.hsv
            row.label(text=f"Color   [{v:.2f}]")
            row.prop(scene, "se_vertex_color", text="")

            # Первая строка кнопок цвета
            row = settings_col.row(align=True)

            # Кнопка уменьшения яркости
            sub = row.row(align=True)
            sub.scale_x = 1.0
            op = sub.operator(
                SE_OT_ColorAttr_AdjustColor.bl_idname,
                text="",
                icon='TRIA_LEFT',
                emboss=True
            )
            op.adjustment = -0.05

            # Кнопка серого цвета по умолчанию
            row.operator(
                SE_OT_ColorAttr_SetDefaultGray.bl_idname,
                text="Default Gray"
            )

            # Кнопка увеличения яркости
            sub = row.row(align=True)
            sub.scale_x = 1.0
            op = sub.operator(
                SE_OT_ColorAttr_AdjustColor.bl_idname,
                text="",
                icon='TRIA_RIGHT',
                emboss=True
            )
            op.adjustment = 0.05

            # Вторая строка кнопок цвета
            row = settings_col.row(align=True)
            row.operator(
                SE_OT_ColorAttr_SetPatchColor.bl_idname,
                text="Patch"
            )
            row.operator(
                SE_OT_ColorAttr_SetWatermaskColor.bl_idname,
                text="Watermask"
            )

classes = (
    SE_OT_CAAdvanced_Toggle,
    SE_OT_ColorAttr_FullSet,
    SE_OT_ColorAttr_ShowHide,
    SE_OT_ColorAttr_SaveDisplay,
    SE_OT_ColorAttr_SetDefaultGray,
    SE_OT_ColorAttr_SetPatchColor,
    SE_OT_ColorAttr_SetWatermaskColor,
    SE_OT_ColorAttr_AdjustColor,
    SE_OT_ColorAttr_ResetName,
    SE_PT_ColorAttrPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Safely delete scene properties
    scene_props = [
        'se_color_attr_name',
        'se_vertex_color',
        'se_settings_panel_collapsed',
        'se_original_shading_type',
        'se_original_color_type',
    ]
    
    for prop in scene_props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)