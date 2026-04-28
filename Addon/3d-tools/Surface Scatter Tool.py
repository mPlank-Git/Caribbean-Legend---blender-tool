bl_info = {
    "name": "Surface Scatter Tool",
    "author": "mPlank",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Scatter",
    "description": "Randomly scatters objects on a surface with slope filtering and vertex group mask support",
    "category": "Object",
}

import bpy
import bmesh
import random
import math
from mathutils import Vector, Matrix
from bpy.props import (
    PointerProperty,
    IntProperty,
    FloatProperty,
    BoolProperty,
    StringProperty,
)
from bpy.types import PropertyGroup, Panel, Operator


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def get_source_mesh_objects(collection):
    if not collection:
        return []
    return [obj for obj in collection.objects if obj.type in {'MESH', 'EMPTY', 'CURVE', 'SURFACE', 'FONT'}]


def get_vertex_group_names(self, context):
    items = []
    props = context.scene.surface_scatter_props
    surface = props.surface_object
    if surface and surface.type == 'MESH':
        for vg in surface.vertex_groups:
            items.append((vg.name, vg.name, ""))
    return items


def clamp(value, vmin, vmax):
    return max(vmin, min(value, vmax))


def lerp(a, b, t):
    return a + (b - a) * t


def ensure_scatter_collection(context):
    scene = context.scene
    props = scene.surface_scatter_props

    coll_name = props.scatter_result_collection_name.strip()
    if coll_name:
        coll = bpy.data.collections.get(coll_name)
        if coll:
            return coll

    base_name = "Scatter_Result"
    coll = bpy.data.collections.get(base_name)
    if coll is None:
        coll = bpy.data.collections.new(base_name)
        scene.collection.children.link(coll)

    props.scatter_result_collection_name = coll.name
    return coll


def clear_collection_objects(collection):
    objs = list(collection.objects)
    for obj in objs:
        bpy.data.objects.remove(obj, do_unlink=True)


def get_object_vg_weight(obj, vertex_group_index, vertex_index):
    if vertex_group_index < 0:
        return 1.0

    vertex = obj.data.vertices[vertex_index]
    for g in vertex.groups:
        if g.group == vertex_group_index:
            return g.weight
    return 0.0


def build_surface_triangles(surface_obj):
    """
    Returns:
        triangles: list of dicts with:
            verts_world: (v0, v1, v2)
            normals_world: (n0, n1, n2)
            weights: (w0, w1, w2)
            area: float
    """
    mesh = surface_obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    mw = surface_obj.matrix_world
    normal_matrix = mw.to_3x3().inverted().transposed()

    vg_index = -1
    scene = bpy.context.scene
    props = scene.surface_scatter_props

    if props.use_vertex_group and props.vertex_group_name and props.vertex_group_name in surface_obj.vertex_groups:
        vg_index = surface_obj.vertex_groups[props.vertex_group_name].index

    triangles = []

    for face in bm.faces:
        if len(face.verts) != 3:
            continue

        verts = face.verts
        v0_local = verts[0].co.copy()
        v1_local = verts[1].co.copy()
        v2_local = verts[2].co.copy()

        v0_world = mw @ v0_local
        v1_world = mw @ v1_local
        v2_world = mw @ v2_local

        edge1 = v1_world - v0_world
        edge2 = v2_world - v0_world
        cross = edge1.cross(edge2)
        area = cross.length * 0.5

        if area <= 1e-10:
            continue

        n0 = (normal_matrix @ verts[0].normal).normalized()
        n1 = (normal_matrix @ verts[1].normal).normalized()
        n2 = (normal_matrix @ verts[2].normal).normalized()

        w0 = get_object_vg_weight(surface_obj, vg_index, verts[0].index)
        w1 = get_object_vg_weight(surface_obj, vg_index, verts[1].index)
        w2 = get_object_vg_weight(surface_obj, vg_index, verts[2].index)

        triangles.append({
            "verts_world": (v0_world, v1_world, v2_world),
            "normals_world": (n0, n1, n2),
            "weights": (w0, w1, w2),
            "area": area,
        })

    bm.free()
    return triangles


def choose_triangle_by_area(triangles, total_area):
    r = random.uniform(0.0, total_area)
    acc = 0.0
    for tri in triangles:
        acc += tri["area"]
        if r <= acc:
            return tri
    return triangles[-1]


def random_point_in_triangle(v0, v1, v2):
    r1 = random.random()
    r2 = random.random()

    sqrt_r1 = math.sqrt(r1)
    a = 1.0 - sqrt_r1
    b = sqrt_r1 * (1.0 - r2)
    c = sqrt_r1 * r2

    p = (v0 * a) + (v1 * b) + (v2 * c)
    return p, (a, b, c)


def blended_alignment_rotation(normal, align_factor, random_z_degrees):
    """
    Returns rotation matrix that aligns object local Z toward the surface normal,
    blended with world up based on align_factor, then applies random Z spin.
    """
    up = Vector((0.0, 0.0, 1.0))
    target = up.lerp(normal.normalized(), align_factor).normalized()

    z_axis = target

    helper = Vector((1.0, 0.0, 0.0))
    if abs(z_axis.dot(helper)) > 0.999:
        helper = Vector((0.0, 1.0, 0.0))

    x_axis = helper.cross(z_axis).normalized()
    y_axis = z_axis.cross(x_axis).normalized()

    rot = Matrix((
        (x_axis.x, y_axis.x, z_axis.x),
        (x_axis.y, y_axis.y, z_axis.y),
        (x_axis.z, y_axis.z, z_axis.z),
    )).to_4x4()

    spin = Matrix.Rotation(math.radians(random_z_degrees), 4, 'Z')
    return rot @ spin


def can_place_with_distance(point, placed_points, min_distance):
    if min_distance <= 0.0:
        return True

    min_d2 = min_distance * min_distance
    for p in placed_points:
        if (point - p).length_squared < min_d2:
            return False
    return True


def validate_props(props):
    if props.surface_object is None:
        return False, "Surface object is not set"
    if props.surface_object.type != 'MESH':
        return False, "Surface object must be a mesh"
    if props.scatter_collection is None:
        return False, "Scatter collection is not set"

    source_objects = get_source_mesh_objects(props.scatter_collection)
    if not source_objects:
        return False, "Scatter collection has no supported source objects"

    if props.use_vertex_group:
        if not props.vertex_group_name:
            return False, "Vertex group is enabled but no group is selected"
        if props.vertex_group_name not in props.surface_object.vertex_groups:
            return False, "Selected vertex group does not exist on the surface"

    if props.min_slope > props.max_slope:
        return False, "Min slope cannot be greater than max slope"

    if props.min_scale > props.max_scale:
        return False, "Min scale cannot be greater than max scale"

    return True, ""


# ------------------------------------------------------------
# Properties
# ------------------------------------------------------------

class SurfaceScatterProperties(PropertyGroup):
    surface_object: PointerProperty(
        name="Surface",
        type=bpy.types.Object,
        description="Target surface object",
    )

    scatter_collection: PointerProperty(
        name="Scatter Collection",
        type=bpy.types.Collection,
        description="Collection with source objects to scatter",
    )

    count: IntProperty(
        name="Count",
        default=100,
        min=1,
        soft_max=10000,
        description="Desired number of scattered objects",
    )

    seed: IntProperty(
        name="Seed",
        default=0,
        min=0,
        max=999999,
        description="Random seed",
    )

    min_scale: FloatProperty(
        name="Min Scale",
        default=0.8,
        min=0.001,
        soft_max=100.0,
    )

    max_scale: FloatProperty(
        name="Max Scale",
        default=1.2,
        min=0.001,
        soft_max=100.0,
    )

    min_slope: FloatProperty(
        name="Min Slope",
        default=0.0,
        min=0.0,
        max=180.0,
        subtype='ANGLE',
        description="Minimum allowed slope angle in degrees from world up",
    )

    max_slope: FloatProperty(
        name="Max Slope",
        default=45.0,
        min=0.0,
        max=180.0,
        subtype='ANGLE',
        description="Maximum allowed slope angle in degrees from world up",
    )

    align_to_normal: FloatProperty(
        name="Align to Normal",
        default=1.0,
        min=0.0,
        max=1.0,
        description="How much the object aligns to the surface normal",
    )

    min_distance: FloatProperty(
        name="Min Distance",
        default=0.2,
        min=0.0,
        soft_max=100.0,
        description="Minimum distance between scattered objects",
    )

    random_rotation_z: BoolProperty(
        name="Random Z Rotation",
        default=True,
        description="Apply random rotation around local Z axis",
    )

    use_vertex_group: BoolProperty(
        name="Use Vertex Group",
        default=False,
        description="Use vertex group as density/probability mask",
    )

    vertex_group_name: StringProperty(
        name="Vertex Group",
        default="",
        description="Vertex group used as density mask",
    )

    invert_vertex_group: BoolProperty(
        name="Invert Mask",
        default=False,
        description="Invert vertex group mask weight",
    )

    vertex_group_threshold: FloatProperty(
        name="Weight Threshold",
        default=0.0,
        min=0.0,
        max=1.0,
        description="Ignore points below this interpolated vertex weight",
    )

    vertex_group_influence: FloatProperty(
        name="Mask Influence",
        default=1.0,
        min=0.0,
        max=1.0,
        description="How strongly the vertex group weight affects spawn probability",
    )

    clear_previous: BoolProperty(
        name="Clear Previous",
        default=True,
        description="Clear previous scatter result collection before generating",
    )

    scatter_result_collection_name: StringProperty(
        name="Result Collection Name",
        default="Scatter_Result",
    )


# ------------------------------------------------------------
# Operators
# ------------------------------------------------------------

class OBJECT_OT_surface_scatter_generate(Operator):
    bl_idname = "object.surface_scatter_generate"
    bl_label = "Generate Scatter"
    bl_description = "Generate scattered objects on the target surface"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.surface_scatter_props

        ok, message = validate_props(props)
        if not ok:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        random.seed(props.seed)

        source_objects = get_source_mesh_objects(props.scatter_collection)
        if not source_objects:
            self.report({'ERROR'}, "No valid source objects found in collection")
            return {'CANCELLED'}

        triangles = build_surface_triangles(props.surface_object)
        if not triangles:
            self.report({'ERROR'}, "Surface has no valid triangles")
            return {'CANCELLED'}

        total_area = sum(t["area"] for t in triangles)
        if total_area <= 0.0:
            self.report({'ERROR'}, "Surface area is zero")
            return {'CANCELLED'}

        result_collection = ensure_scatter_collection(context)
        if props.clear_previous:
            clear_collection_objects(result_collection)

        placed_points = []
        created_count = 0
        rejected_by_mask_only = 0
        max_attempts = max(props.count * 30, 100)

        up = Vector((0.0, 0.0, 1.0))

        for _ in range(max_attempts):
            if created_count >= props.count:
                break

            tri = choose_triangle_by_area(triangles, total_area)

            v0, v1, v2 = tri["verts_world"]
            n0, n1, n2 = tri["normals_world"]
            w0, w1, w2 = tri["weights"]

            point, bary = random_point_in_triangle(v0, v1, v2)
            a, b, c = bary

            normal = ((n0 * a) + (n1 * b) + (n2 * c)).normalized()
            weight = (w0 * a) + (w1 * b) + (w2 * c)

            if props.use_vertex_group:
                if props.invert_vertex_group:
                    weight = 1.0 - weight

                weight = clamp(weight, 0.0, 1.0)

                if weight < props.vertex_group_threshold:
                    rejected_by_mask_only += 1
                    continue

                probability = lerp(1.0, weight, props.vertex_group_influence)
                probability = clamp(probability, 0.0, 1.0)

                if random.random() > probability:
                    rejected_by_mask_only += 1
                    continue

            slope = math.degrees(normal.angle(up))
            if slope < props.min_slope or slope > props.max_slope:
                continue

            if not can_place_with_distance(point, placed_points, props.min_distance):
                continue

            src = random.choice(source_objects)
            new_obj = src.copy()
            if hasattr(src, "data") and src.data is not None:
                new_obj.data = src.data

            scale_val = random.uniform(props.min_scale, props.max_scale)

            random_z = random.uniform(0.0, 360.0) if props.random_rotation_z else 0.0
            rot_mtx = blended_alignment_rotation(normal, props.align_to_normal, random_z)
            loc_mtx = Matrix.Translation(point)
            scl_mtx = Matrix.Diagonal((scale_val, scale_val, scale_val, 1.0))

            new_obj.matrix_world = loc_mtx @ rot_mtx @ scl_mtx
            result_collection.objects.link(new_obj)

            placed_points.append(point)
            created_count += 1

        if created_count == 0:
            if props.use_vertex_group and rejected_by_mask_only > 0:
                self.report({'WARNING'}, "No objects created. Check vertex group mask, threshold, slope, or min distance")
            else:
                self.report({'WARNING'}, "No objects created. Check slope, min distance, or source settings")
            return {'CANCELLED'}

        msg = f"Created {created_count}/{props.count} scattered objects"
        if created_count < props.count:
            msg += " (generation stopped by placement constraints)"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class OBJECT_OT_surface_scatter_clear(Operator):
    bl_idname = "object.surface_scatter_clear"
    bl_label = "Clear Scatter"
    bl_description = "Clear all objects from the scatter result collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.surface_scatter_props
        coll_name = props.scatter_result_collection_name.strip()

        if not coll_name:
            self.report({'WARNING'}, "No scatter result collection set")
            return {'CANCELLED'}

        coll = bpy.data.collections.get(coll_name)
        if not coll:
            self.report({'WARNING'}, "Scatter result collection not found")
            return {'CANCELLED'}

        clear_collection_objects(coll)
        self.report({'INFO'}, "Scatter cleared")
        return {'FINISHED'}


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

class VIEW3D_PT_surface_scatter(Panel):
    bl_label = "Surface Scatter"
    bl_idname = "VIEW3D_PT_surface_scatter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Scatter"

    def draw(self, context):
        layout = self.layout
        props = context.scene.surface_scatter_props

        box = layout.box()
        box.label(text="Source")
        box.prop(props, "surface_object")
        box.prop(props, "scatter_collection")

        box = layout.box()
        box.label(text="Distribution")
        box.prop(props, "count")
        box.prop(props, "seed")
        box.prop(props, "min_distance")
        box.prop(props, "clear_previous")

        box = layout.box()
        box.label(text="Transform")
        row = box.row(align=True)
        row.prop(props, "min_scale")
        row.prop(props, "max_scale")
        box.prop(props, "random_rotation_z")
        box.prop(props, "align_to_normal")

        box = layout.box()
        box.label(text="Surface Filter")
        row = box.row(align=True)
        row.prop(props, "min_slope")
        row.prop(props, "max_slope")

        box = layout.box()
        box.label(text="Vertex Group Mask")
        box.prop(props, "use_vertex_group")

        if props.use_vertex_group:
            surface = props.surface_object
            if surface and surface.type == 'MESH':
                box.prop_search(props, "vertex_group_name", surface, "vertex_groups", text="Vertex Group")
            else:
                box.label(text="Select a mesh surface first", icon='INFO')

            box.prop(props, "invert_vertex_group")
            box.prop(props, "vertex_group_threshold")
            box.prop(props, "vertex_group_influence")

        box = layout.box()
        box.label(text="Result")
        box.prop(props, "scatter_result_collection_name", text="Collection")

        row = layout.row(align=True)
        row.operator("object.surface_scatter_generate", icon='PARTICLES')
        row.operator("object.surface_scatter_clear", icon='TRASH')


# ------------------------------------------------------------
# Registration
# ------------------------------------------------------------

classes = (
    SurfaceScatterProperties,
    OBJECT_OT_surface_scatter_generate,
    OBJECT_OT_surface_scatter_clear,
    VIEW3D_PT_surface_scatter,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.surface_scatter_props = PointerProperty(type=SurfaceScatterProperties)


def unregister():
    del bpy.types.Scene.surface_scatter_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()