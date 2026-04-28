bl_info = {
    "name": "Vertex Color Fill From Selection",
    "author": "mPlank",
    "version": (1, 3, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Vertex Paint Fill",
    "description": "Assign vertex color to selected vertices in Edit Mode and randomize G channel for selected geometry",
    "category": "Mesh",
}

import bpy
import bmesh
import random
from bpy.props import (
    FloatVectorProperty,
    StringProperty,
    EnumProperty,
)


def get_bmesh_color_layer(bm, layer_name, color_type):
    if color_type == 'FLOAT_COLOR':
        layer = bm.loops.layers.float_color.get(layer_name)
        if layer is None:
            layer = bm.loops.layers.float_color.new(layer_name)
        return layer
    else:
        layer = bm.loops.layers.color.get(layer_name)
        if layer is None:
            layer = bm.loops.layers.color.new(layer_name)
        return layer


def ensure_mesh_color_attribute(mesh, layer_name, color_type):
    attr = mesh.color_attributes.get(layer_name)
    if attr is None:
        attr = mesh.color_attributes.new(
            name=layer_name,
            type=color_type,
            domain='CORNER'
        )
    return attr


class MESH_OT_fill_selected_vertices_color(bpy.types.Operator):
    bl_idname = "mesh.fill_selected_vertices_color"
    bl_label = "Fill Selected Vertices"
    bl_description = "Assign chosen color to selected vertices"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return (
            obj is not None and
            obj.type == 'MESH' and
            context.mode == 'EDIT_MESH'
        )

    def execute(self, context):
        scene = context.scene
        obj = context.object
        mesh = obj.data

        color = scene.vcf_fill_color
        layer_name = scene.vcf_color_layer_name.strip()
        color_type = scene.vcf_color_type

        if not layer_name:
            self.report({'ERROR'}, "Color Attribute name cannot be empty")
            return {'CANCELLED'}

        ensure_mesh_color_attribute(mesh, layer_name, color_type)

        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        selected_verts = [v for v in bm.verts if v.select]
        if not selected_verts:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        color_layer = get_bmesh_color_layer(bm, layer_name, color_type)

        painted_loops = 0

        for face in bm.faces:
            for loop in face.loops:
                if loop.vert.select:
                    loop[color_layer] = (
                        color[0],
                        color[1],
                        color[2],
                        color[3],
                    )
                    painted_loops += 1

        bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

        try:
            attr = mesh.color_attributes.get(layer_name)
            if attr is not None:
                mesh.color_attributes.active_color = attr
        except Exception:
            pass

        self.report(
            {'INFO'},
            f"Painted {len(selected_verts)} vertices, affected {painted_loops} face corners"
        )
        return {'FINISHED'}


class MESH_OT_random_sid_g_selected(bpy.types.Operator):
    bl_idname = "mesh.random_sid_g_selected"
    bl_label = "Random Sid G Channel"
    bl_description = "Assign one random G value to the whole selected geometry without changing R/B"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return (
            obj is not None and
            obj.type == 'MESH' and
            context.mode == 'EDIT_MESH'
        )

    def execute(self, context):
        scene = context.scene
        obj = context.object
        mesh = obj.data

        layer_name = scene.vcf_color_layer_name.strip()
        color_type = scene.vcf_color_type

        if not layer_name:
            self.report({'ERROR'}, "Color Attribute name cannot be empty")
            return {'CANCELLED'}

        ensure_mesh_color_attribute(mesh, layer_name, color_type)

        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        selected_faces = [f for f in bm.faces if f.select]
        selected_verts = [v for v in bm.verts if v.select]

        if not selected_faces and not selected_verts:
            self.report({'WARNING'}, "No geometry selected")
            return {'CANCELLED'}

        color_layer = get_bmesh_color_layer(bm, layer_name, color_type)

        g_value = random.random()
        changed = 0

        for face in bm.faces:
            for loop in face.loops:
                if loop.vert.select or face.select:
                    col = list(loop[color_layer])
                    col[1] = g_value  # меняем только G
                    loop[color_layer] = col
                    changed += 1

        bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

        try:
            attr = mesh.color_attributes.get(layer_name)
            if attr is not None:
                mesh.color_attributes.active_color = attr
        except Exception:
            pass

        self.report(
            {'INFO'},
            f"Assigned random G={g_value:.3f} to selected geometry, affected {changed} face corners"
        )
        return {'FINISHED'}


class VIEW3D_PT_vertex_color_fill_panel(bpy.types.Panel):
    bl_label = "Vertex Paint Fill"
    bl_idname = "VIEW3D_PT_vertex_color_fill_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Vertex Paint Fill"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object

        col = layout.column(align=True)
        col.label(text="Color Attribute Name:")
        col.prop(scene, "vcf_color_layer_name", text="")

        col.separator()
        col.label(text="Color Type:")
        col.prop(scene, "vcf_color_type", text="")

        if obj and obj.type == 'MESH':
            attrs = obj.data.color_attributes
            if attrs:
                box = col.box()
                box.label(text="Existing Attributes:")
                for attr in attrs:
                    row = box.row()
                    row.label(text=f"{attr.name}  ({attr.data_type})")

        col.separator()
        col.label(text="Fill Color:")
        col.prop(scene, "vcf_fill_color", text="")

        col.separator()

        if context.mode != 'EDIT_MESH':
            box = col.box()
            box.label(text="Switch to Edit Mode", icon='INFO')
            box.label(text="and select geometry")
        else:
            bm = bmesh.from_edit_mesh(obj.data)
            selected_vert_count = sum(1 for v in bm.verts if v.select)
            selected_face_count = sum(1 for f in bm.faces if f.select)
            col.label(text=f"Selected Vertices: {selected_vert_count}")
            col.label(text=f"Selected Faces: {selected_face_count}")

        col.separator()
        col.operator("mesh.fill_selected_vertices_color", icon='BRUSH_DATA')
        col.operator("mesh.random_sid_g_selected", icon='RNDCURVE')


classes = (
    MESH_OT_fill_selected_vertices_color,
    MESH_OT_random_sid_g_selected,
    VIEW3D_PT_vertex_color_fill_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.vcf_fill_color = FloatVectorProperty(
        name="Fill Color",
        description="Color assigned to selected vertices",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 0.0, 0.0, 1.0)
    )

    bpy.types.Scene.vcf_color_layer_name = StringProperty(
        name="Color Attribute Name",
        description="Name of the Color Attribute to paint into",
        default="Col"
    )

    bpy.types.Scene.vcf_color_type = EnumProperty(
        name="Color Type",
        description="Type of color attribute to create/use",
        items=[
            ('FLOAT_COLOR', "Face Color", "Float color attribute"),
            ('BYTE_COLOR', "Byte Color", "Byte color attribute"),
        ],
        default='BYTE_COLOR'
    )


def unregister():
    del bpy.types.Scene.vcf_fill_color
    del bpy.types.Scene.vcf_color_layer_name
    del bpy.types.Scene.vcf_color_type

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()