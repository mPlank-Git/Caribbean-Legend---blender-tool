bl_info = {
    "name": "Curve to Empty",
    "blender": (3, 6, 0),
    "category": "Object",
}

import bpy
import bmesh

def get_next_name(base_name, start_index):
    counter = start_index
    while bpy.data.objects.get(f"{base_name}{counter:02d}") is not None:
        counter += 1
    return counter

def create_or_get_collection(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    else:
        new_collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(new_collection)
        return new_collection

def create_curve_with_empties(curve, mast_number, rey_number, prefix_start, prefix_end, start_index):
    # Создаем или получаем коллекцию "Rope"
    rope_collection = create_or_get_collection("Rope")

    # Создаем копию кривой
    curve_copy = curve.copy()
    curve_copy.data = curve.data.copy()
    bpy.context.collection.objects.link(curve_copy)
    
    # Конвертируем копию кривой в меш
    bpy.context.view_layer.objects.active = curve_copy
    bpy.ops.object.convert(target='MESH')
    mesh = bpy.context.object

    # Получаем вершины меша
    vertices = [v.co for v in mesh.data.vertices]

    # Устанавливаем базовые имена и номера для пустышек
    base_name = f"{mast_number}{rey_number:01d}"
    start_number = get_next_name(f"{prefix_start}{base_name}", start_index)
    end_number = get_next_name(f"{prefix_end}{base_name}", start_index)

    # Создаем пустышки на месте вершин
    for i, vert in enumerate(vertices):
        empty = bpy.data.objects.new("Empty", None)
        empty.location = curve_copy.matrix_world @ vert  # Перемещение пустышки на мировые координаты вершины
        bpy.context.collection.objects.link(empty)
        rope_collection.objects.link(empty)
        bpy.context.collection.objects.unlink(empty)

        # Устанавливаем имя пустышки
        if i == 0:
            empty.name = f"{prefix_start}{base_name}{start_number:02d}"
        elif i == len(vertices) - 1:
            empty.name = f"{prefix_end}{base_name}{end_number:02d}"
        else:
            empty.name = f"Empty_{base_name}{start_number:02d}"

        start_number += 1

    # Удаляем временную копию меша
    bpy.data.objects.remove(curve_copy)

class OBJECT_OT_curve_to_empty(bpy.types.Operator):
    """Convert Curve to Empties"""
    bl_idname = "object.curve_to_empty"
    bl_label = "Convert Curve to Empties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_curves = [obj for obj in context.selected_objects if obj.type == 'CURVE']
        if not selected_curves:
            self.report({'WARNING'}, "No curves selected")
            return {'CANCELLED'}

        mast_number = context.scene.mast_number
        rey_number = context.scene.rey_number
        prefix_start = context.scene.prefix_start
        prefix_end = context.scene.prefix_end
        start_index = context.scene.start_index

        for curve in selected_curves:
            create_curve_with_empties(curve, mast_number, rey_number, prefix_start, prefix_end, start_index)
        
        return {'FINISHED'}

class VIEW3D_PT_curve_to_empty(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Curve to Empty"
    bl_idname = "VIEW3D_PT_curve_to_empty"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Curve to Empty'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Настройки для преобразования:")
        col.prop(context.scene, "mast_number", text="Мачта")
        col.prop(context.scene, "rey_number", text="Рея")
        col.prop(context.scene, "prefix_start", text="Начальный префикс")
        col.prop(context.scene, "prefix_end", text="Конечный префикс")
        col.prop(context.scene, "start_index", text="Начальный индекс")
        col.operator("object.curve_to_empty", text="Преобразовать кривую")

def register():
    bpy.utils.register_class(OBJECT_OT_curve_to_empty)
    bpy.utils.register_class(VIEW3D_PT_curve_to_empty)
    bpy.types.Scene.mast_number = bpy.props.IntProperty(name="Mast Number", default=1, min=1)
    bpy.types.Scene.rey_number = bpy.props.IntProperty(name="Rey Number", default=1, min=1)
    bpy.types.Scene.prefix_start = bpy.props.StringProperty(name="Prefix Start", default="falb")
    bpy.types.Scene.prefix_end = bpy.props.StringProperty(name="Prefix End", default="fale")
    bpy.types.Scene.start_index = bpy.props.IntProperty(name="Start Index", default=1, min=1)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_curve_to_empty)
    bpy.utils.unregister_class(VIEW3D_PT_curve_to_empty)
    del bpy.types.Scene.mast_number
    del bpy.types.Scene.rey_number
    del bpy.types.Scene.prefix_start
    del bpy.types.Scene.prefix_end
    del bpy.types.Scene.start_index

if __name__ == "__main__":
    register()
