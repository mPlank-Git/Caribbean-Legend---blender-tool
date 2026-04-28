bl_info = {
    "name": "Rope editor",
    "author": "mPlank",
    "blender": (3, 6, 0),
    "category": "Object",
}
import bpy
import bmesh
from bpy.props import IntProperty
from mathutils import Vector

class OBJECT_OT_create_curve_from_empty(bpy.types.Operator):
    """Create a curve from two empties with the same number"""
    bl_idname = "object.create_curve_from_empty"
    bl_label = "Create Curve from Empties"
    bl_options = {'REGISTER', 'UNDO'}

    number: IntProperty(
        name="Number",
        description="Number of empties to connect",
        default=1,
        min=1
    )

    def execute(self, context):
        empties = [obj for obj in context.scene.objects if obj.type == 'EMPTY' and obj.name.startswith(f"Empty.{self.number}")]
        
        if len(empties) != 2:
            self.report({'ERROR'}, f"Found {len(empties)} empties with number {self.number}, but need exactly 2.")
            return {'CANCELLED'}
        
        curve_data = bpy.data.curves.new('Curve', type='CURVE')
        curve_data.dimensions = '3D'
        
        spline = curve_data.splines.new(type='POLY')
        spline.points.add(1)  # Add one point, total two points for the spline
        
        spline.points[0].co = empties[0].location.to_4d()
        spline.points[1].co = empties[1].location.to_4d()
        
        curve_object = bpy.data.objects.new('Curve', curve_data)
        context.collection.objects.link(curve_object)
        
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(OBJECT_OT_create_curve_from_empty.bl_idname, text="Create Curve from Empties")

def register():
    bpy.utils.register_class(OBJECT_OT_create_curve_from_empty)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_create_curve_from_empty)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()