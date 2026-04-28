bl_info = {
    "name": "Vines and Ivy Generator",
    "author": "mPlank",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Vine/Ivy",
    "description": "Build hanging vines from point objects and generate ivy planes along any curve",
    "category": "Object",
}

import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup, UIList


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def ensure_object_mode(context):
    if context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


def unique_name(base):
    i = 1
    name = base
    while bpy.data.objects.get(name) or bpy.data.curves.get(name) or bpy.data.meshes.get(name):
        name = f"{base}.{i:03d}"
        i += 1
    return name


def object_exists(name):
    return name in bpy.data.objects


def get_point_objects(scene):
    result = []
    for item in scene.vineivy_point_items:
        obj = bpy.data.objects.get(item.object_name)
        if obj:
            result.append(obj)
    return result


def clear_generated_ivy_for_curve(curve_obj):
    to_remove = []
    for obj in bpy.data.objects:
        if obj.get("vineivy_generated_ivy") and obj.get("vineivy_source_curve") == curve_obj.name:
            to_remove.append(obj)

    for obj in to_remove:
        # unlink from all collections first
        for coll in list(obj.users_collection):
            coll.objects.unlink(obj)
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data:
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Curve) and data.users == 0:
                bpy.data.curves.remove(data)


def link_object_to_active_collection(context, obj):
    collection = context.collection
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def build_vine_point_list(anchor_positions, settings):
    """
    Returns a list of points:
    A, mid_sag, B, mid_sag, C ...
    """
    pts = []
    rng = random.Random(settings.seed)

    if len(anchor_positions) < 2:
        return pts

    pts.append(anchor_positions[0])

    for i in range(len(anchor_positions) - 1):
        a = anchor_positions[i]
        b = anchor_positions[i + 1]
        seg = b - a
        dist = seg.length

        mid = (a + b) * 0.5

        # Base sag depends on segment length
        base_sag = dist * settings.sag_amount
        rand_factor = 1.0 + rng.uniform(-settings.sag_randomness, settings.sag_randomness)

        # Limit sag for near-vertical segments to avoid ugly loops
        horizontal_len = Vector((seg.x, seg.y, 0.0)).length
        vertical_factor = 1.0 if horizontal_len > 0.001 else 0.25

        sag_value = max(0.0, base_sag * rand_factor * vertical_factor)

        sag_point = mid + Vector((0.0, 0.0, -sag_value))

        # Slight random XY drift for more natural result
        drift = dist * settings.midpoint_side_jitter
        sag_point.x += rng.uniform(-drift, drift)
        sag_point.y += rng.uniform(-drift, drift)

        pts.append(sag_point)
        pts.append(b)

    return pts


def create_vine_curve_object(context, points_world, settings):
    curve_data = bpy.data.curves.new(unique_name("VineCurve"), type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = settings.curve_resolution
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = settings.bevel_depth
    curve_data.bevel_resolution = settings.bevel_resolution

    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(len(points_world) - 1)

    for i, p in enumerate(points_world):
        bp = spline.bezier_points[i]
        bp.co = p
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    obj = bpy.data.objects.new(unique_name("Vine"), curve_data)
    obj["vineivy_generated_vine"] = True
    link_object_to_active_collection(context, obj)

    return obj


def build_adjacency_from_edges(edge_pairs):
    adj = {}
    for a, b in edge_pairs:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    return adj


def ordered_paths_from_curve_mesh(vertices, edges):
    """
    Reconstructs ordered vertex index chains from a curve converted to mesh.
    Works well for typical open splines. Closed loops are supported too.
    """
    adj = build_adjacency_from_edges(edges)
    visited_edges = set()
    paths = []

    def edge_key(a, b):
        return tuple(sorted((a, b)))

    endpoints = [idx for idx, nbrs in adj.items() if len(nbrs) == 1]
    starts = endpoints[:]

    # For closed loops, pick any unvisited vertex later
    used_vertices = set()

    def walk(start):
        path = [start]
        prev = None
        current = start

        while True:
            neighbors = adj.get(current, [])
            next_candidates = []
            for n in neighbors:
                ek = edge_key(current, n)
                if ek not in visited_edges:
                    next_candidates.append(n)

            if not next_candidates:
                break

            # Prefer continuing away from previous
            next_v = next_candidates[0]
            visited_edges.add(edge_key(current, next_v))
            prev = current
            current = next_v
            path.append(current)

            if current == start:
                break

        for v in path:
            used_vertices.add(v)
        return path

    for s in starts:
        if s in used_vertices:
            continue
        p = walk(s)
        if len(p) > 1:
            paths.append(p)

    # Handle closed loops or isolated unvisited chains
    for v in adj.keys():
        if v in used_vertices:
            continue
        p = walk(v)
        if len(p) > 1:
            paths.append(p)

    result = []
    for path in paths:
        result.append([vertices[i].copy() for i in path])

    return result


def get_curve_paths_world(curve_obj, depsgraph):
    """
    Evaluates any curve as mesh and reconstructs world-space point paths.
    """
    eval_obj = curve_obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()

    try:
        verts_world = [curve_obj.matrix_world @ v.co for v in mesh.vertices]
        edges = [(e.vertices[0], e.vertices[1]) for e in mesh.edges]
        paths = ordered_paths_from_curve_mesh(verts_world, edges)
        return paths
    finally:
        eval_obj.to_mesh_clear()


def polyline_length(points):
    total = 0.0
    for i in range(len(points) - 1):
        total += (points[i + 1] - points[i]).length
    return total


def resample_polyline(points, spacing):
    """
    Returns evenly spaced points and tangents along a polyline.
    """
    if len(points) < 2:
        return []

    if spacing <= 0.0001:
        spacing = 0.0001

    segments = []
    total_length = 0.0
    for i in range(len(points) - 1):
        a = points[i]
        b = points[i + 1]
        seg = b - a
        length = seg.length
        if length > 1e-8:
            segments.append((a, b, seg.normalized(), length))
            total_length += length

    if total_length <= 1e-8:
        return []

    result = []
    d = 0.0
    seg_idx = 0
    seg_accum = 0.0

    while d <= total_length + 1e-8 and seg_idx < len(segments):
        while seg_idx < len(segments):
            a, b, tangent, seg_len = segments[seg_idx]
            if d <= seg_accum + seg_len + 1e-8:
                local = max(0.0, min(seg_len, d - seg_accum))
                t = local / seg_len if seg_len > 1e-8 else 0.0
                p = a.lerp(b, t)
                result.append((p, tangent))
                break
            seg_accum += seg_len
            seg_idx += 1
        d += spacing

    # Ensure end point exists
    a, b, tangent, seg_len = segments[-1]
    if not result or (result[-1][0] - points[-1]).length > spacing * 0.25:
        result.append((points[-1], tangent))

    return result


def tangent_frame(tangent, roll):
    tangent = tangent.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(tangent.dot(up)) > 0.98:
        up = Vector((1.0, 0.0, 0.0))

    side = tangent.cross(up)
    if side.length < 1e-8:
        side = Vector((1.0, 0.0, 0.0))
    side.normalize()

    normal = side.cross(tangent).normalized()

    rot = Matrix.Rotation(roll, 3, tangent)
    side = rot @ side
    normal = rot @ normal

    return tangent, side, normal


def create_leaf_quad(verts, faces, center, tangent, side, normal, length, width):
    """
    Plane aligned by tangent/side, offset outward by normal.
    """
    v0 = center - tangent * (length * 0.5) - side * (width * 0.5)
    v1 = center - tangent * (length * 0.5) + side * (width * 0.5)
    v2 = center + tangent * (length * 0.5) + side * (width * 0.5)
    v3 = center + tangent * (length * 0.5) - side * (width * 0.5)

    idx = len(verts)
    verts.extend([v0, v1, v2, v3])
    faces.append((idx, idx + 1, idx + 2, idx + 3))


def generate_ivy_mesh_data(paths, settings):
    rng = random.Random(settings.ivy_seed)
    verts = []
    faces = []

    for path in paths:
        sampled = resample_polyline(path, settings.leaf_spacing)
        if not sampled:
            continue

        for p, tangent in sampled:
            size = rng.uniform(settings.leaf_size_min, settings.leaf_size_max)
            width = size * settings.leaf_width_ratio
            roll = math.radians(rng.uniform(-settings.random_roll_deg, settings.random_roll_deg))
            tangent, side, normal = tangent_frame(tangent, roll)

            outward = rng.uniform(settings.offset_normal_min, settings.offset_normal_max)
            sideways = rng.uniform(-settings.offset_side, settings.offset_side)
            along = rng.uniform(-settings.offset_along, settings.offset_along)

            center = (
                p
                + normal * outward
                + side * sideways
                + tangent * along
            )

            create_leaf_quad(
                verts,
                faces,
                center=center,
                tangent=tangent,
                side=side,
                normal=normal,
                length=size,
                width=width,
            )

    return verts, faces


def create_ivy_mesh_object(context, curve_obj, verts, faces):
    mesh = bpy.data.meshes.new(unique_name(f"IvyMesh_{curve_obj.name}"))
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(unique_name(f"Ivy_{curve_obj.name}"), mesh)
    obj["vineivy_generated_ivy"] = True
    obj["vineivy_source_curve"] = curve_obj.name
    link_object_to_active_collection(context, obj)

    return obj


# ------------------------------------------------------------
# Properties
# ------------------------------------------------------------

class VINEIVY_PointItem(PropertyGroup):
    object_name: StringProperty(name="Object Name")


class VINEIVY_Settings(PropertyGroup):
    mode: EnumProperty(
        name="Mode",
        items=[
            ('VINE', "Vines", "Build hanging vine curve from point objects"),
            ('IVY', "Ivy", "Generate ivy planes along any curve"),
        ],
        default='VINE',
    )

    # Vine settings
    sag_amount: FloatProperty(
        name="Sag Amount",
        description="Sag amount relative to segment length",
        default=0.18,
        min=0.0,
        soft_max=2.0,
    )
    sag_randomness: FloatProperty(
        name="Sag Randomness",
        description="Random variation of sag",
        default=0.25,
        min=0.0,
        max=1.0,
    )
    midpoint_side_jitter: FloatProperty(
        name="Side Jitter",
        description="Small random XY drift for sag points",
        default=0.03,
        min=0.0,
        soft_max=1.0,
    )
    seed: IntProperty(
        name="Seed",
        default=0,
        min=0,
    )
    curve_resolution: IntProperty(
        name="Resolution",
        default=16,
        min=1,
        max=64,
    )
    bevel_depth: FloatProperty(
        name="Bevel Depth",
        default=0.0,
        min=0.0,
        soft_max=1.0,
    )
    bevel_resolution: IntProperty(
        name="Bevel Resolution",
        default=2,
        min=0,
        max=12,
    )
    select_result_curve: BoolProperty(
        name="Select Result",
        default=True,
    )

    # Ivy settings
    target_curve: PointerProperty(
        name="Target Curve",
        type=bpy.types.Object,
        poll=lambda self, obj: obj and obj.type == 'CURVE',
    )
    leaf_spacing: FloatProperty(
        name="Leaf Spacing",
        default=0.15,
        min=0.001,
        soft_max=5.0,
    )
    leaf_size_min: FloatProperty(
        name="Leaf Size Min",
        default=0.06,
        min=0.001,
        soft_max=2.0,
    )
    leaf_size_max: FloatProperty(
        name="Leaf Size Max",
        default=0.14,
        min=0.001,
        soft_max=2.0,
    )
    leaf_width_ratio: FloatProperty(
        name="Width Ratio",
        default=0.7,
        min=0.05,
        soft_max=2.0,
    )
    random_roll_deg: FloatProperty(
        name="Random Roll",
        description="Random rotation around curve tangent",
        default=70.0,
        min=0.0,
        max=180.0,
    )
    offset_normal_min: FloatProperty(
        name="Outward Min",
        default=0.0,
        min=0.0,
        soft_max=1.0,
    )
    offset_normal_max: FloatProperty(
        name="Outward Max",
        default=0.03,
        min=0.0,
        soft_max=1.0,
    )
    offset_side: FloatProperty(
        name="Side Offset",
        default=0.02,
        min=0.0,
        soft_max=1.0,
    )
    offset_along: FloatProperty(
        name="Along Offset",
        default=0.01,
        min=0.0,
        soft_max=1.0,
    )
    ivy_seed: IntProperty(
        name="Seed",
        default=0,
        min=0,
    )
    recalc_normals: BoolProperty(
        name="Recalculate Normals",
        default=True,
    )
    shade_smooth: BoolProperty(
        name="Shade Smooth",
        default=False,
    )


# ------------------------------------------------------------
# UI List
# ------------------------------------------------------------

class VINEIVY_UL_points(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = bpy.data.objects.get(item.object_name)
        if obj:
            layout.label(text=obj.name, icon='EMPTY_DATA' if obj.type == 'EMPTY' else 'OBJECT_DATA')
        else:
            layout.label(text=f"{item.object_name} (missing)", icon='ERROR')


# ------------------------------------------------------------
# Operators - Vine
# ------------------------------------------------------------

class VINEIVY_OT_capture_selected_points(Operator):
    bl_idname = "vineivy.capture_selected_points"
    bl_label = "Use Selected Objects as Points"
    bl_description = "Store currently selected objects as ordered vine points"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ensure_object_mode(context)
        scene = context.scene
        selected = list(context.selected_objects)

        if len(selected) < 2:
            self.report({'WARNING'}, "Select at least 2 objects")
            return {'CANCELLED'}

        # Order by selection order is not available reliably in Blender,
        # so use current selection list order.
        scene.vineivy_point_items.clear()
        for obj in selected:
            item = scene.vineivy_point_items.add()
            item.object_name = obj.name

        scene.vineivy_point_index = max(0, min(scene.vineivy_point_index, len(scene.vineivy_point_items) - 1))
        self.report({'INFO'}, f"Captured {len(selected)} point objects")
        return {'FINISHED'}


class VINEIVY_OT_add_active_object_point(Operator):
    bl_idname = "vineivy.add_active_object_point"
    bl_label = "Add Active Object"
    bl_description = "Append active object to point list"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ensure_object_mode(context)
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        scene = context.scene
        for item in scene.vineivy_point_items:
            if item.object_name == obj.name:
                self.report({'WARNING'}, "Object already in point list")
                return {'CANCELLED'}

        item = scene.vineivy_point_items.add()
        item.object_name = obj.name
        scene.vineivy_point_index = len(scene.vineivy_point_items) - 1

        self.report({'INFO'}, f"Added point: {obj.name}")
        return {'FINISHED'}


class VINEIVY_OT_remove_point(Operator):
    bl_idname = "vineivy.remove_point"
    bl_label = "Remove Point"
    bl_description = "Remove selected point from list"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        idx = scene.vineivy_point_index
        items = scene.vineivy_point_items

        if idx < 0 or idx >= len(items):
            self.report({'WARNING'}, "No point selected")
            return {'CANCELLED'}

        items.remove(idx)
        scene.vineivy_point_index = min(max(0, idx - 1), len(items) - 1)
        self.report({'INFO'}, "Point removed")
        return {'FINISHED'}


class VINEIVY_OT_move_point(Operator):
    bl_idname = "vineivy.move_point"
    bl_label = "Move Point"
    bl_description = "Move point up or down in list"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
        ]
    )

    def execute(self, context):
        scene = context.scene
        idx = scene.vineivy_point_index
        items = scene.vineivy_point_items

        if idx < 0 or idx >= len(items):
            self.report({'WARNING'}, "No point selected")
            return {'CANCELLED'}

        if self.direction == 'UP' and idx > 0:
            items.move(idx, idx - 1)
            scene.vineivy_point_index = idx - 1
        elif self.direction == 'DOWN' and idx < len(items) - 1:
            items.move(idx, idx + 1)
            scene.vineivy_point_index = idx + 1

        return {'FINISHED'}


class VINEIVY_OT_clear_points(Operator):
    bl_idname = "vineivy.clear_points"
    bl_label = "Clear Points"
    bl_description = "Clear point list"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.vineivy_point_items.clear()
        scene.vineivy_point_index = 0
        self.report({'INFO'}, "Points cleared")
        return {'FINISHED'}


class VINEIVY_OT_build_vine(Operator):
    bl_idname = "vineivy.build_vine"
    bl_label = "Build Vine"
    bl_description = "Create hanging vine curve from stored point objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ensure_object_mode(context)

        scene = context.scene
        settings = scene.vineivy_settings
        point_objects = get_point_objects(scene)

        if len(point_objects) < 2:
            self.report({'WARNING'}, "Need at least 2 valid point objects")
            return {'CANCELLED'}

        anchor_positions = [obj.matrix_world.translation.copy() for obj in point_objects]
        curve_points = build_vine_point_list(anchor_positions, settings)

        if len(curve_points) < 2:
            self.report({'WARNING'}, "Failed to build vine points")
            return {'CANCELLED'}

        obj = create_vine_curve_object(context, curve_points, settings)

        if settings.select_result_curve:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj

        self.report({'INFO'}, f"Vine created: {obj.name}")
        return {'FINISHED'}


# ------------------------------------------------------------
# Operators - Ivy
# ------------------------------------------------------------

class VINEIVY_OT_use_active_curve(Operator):
    bl_idname = "vineivy.use_active_curve"
    bl_label = "Use Active Curve"
    bl_description = "Set active curve as ivy target"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'CURVE':
            self.report({'WARNING'}, "Active object is not a curve")
            return {'CANCELLED'}

        context.scene.vineivy_settings.target_curve = obj
        self.report({'INFO'}, f"Target curve set: {obj.name}")
        return {'FINISHED'}


class VINEIVY_OT_generate_ivy(Operator):
    bl_idname = "vineivy.generate_ivy"
    bl_label = "Generate Ivy"
    bl_description = "Generate ivy planes along selected curve"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ensure_object_mode(context)

        scene = context.scene
        settings = scene.vineivy_settings
        curve_obj = settings.target_curve

        if not curve_obj or curve_obj.type != 'CURVE':
            self.report({'WARNING'}, "Pick a valid target curve")
            return {'CANCELLED'}

        if settings.leaf_size_max < settings.leaf_size_min:
            self.report({'WARNING'}, "Leaf Size Max must be >= Leaf Size Min")
            return {'CANCELLED'}

        clear_generated_ivy_for_curve(curve_obj)

        depsgraph = context.evaluated_depsgraph_get()
        paths = get_curve_paths_world(curve_obj, depsgraph)

        if not paths:
            self.report({'WARNING'}, "Could not read any valid path from target curve")
            return {'CANCELLED'}

        verts, faces = generate_ivy_mesh_data(paths, settings)

        if not verts or not faces:
            self.report({'WARNING'}, "No ivy geometry generated. Try smaller spacing or a longer curve")
            return {'CANCELLED'}

        obj = create_ivy_mesh_object(context, curve_obj, verts, faces)

        if settings.recalc_normals:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            bm.to_mesh(obj.data)
            bm.free()

        if settings.shade_smooth:
            for poly in obj.data.polygons:
                poly.use_smooth = True

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        self.report({'INFO'}, f"Ivy generated: {obj.name}")
        return {'FINISHED'}


class VINEIVY_OT_clear_ivy(Operator):
    bl_idname = "vineivy.clear_ivy"
    bl_label = "Clear Ivy"
    bl_description = "Delete generated ivy for target curve"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curve_obj = context.scene.vineivy_settings.target_curve
        if not curve_obj or curve_obj.type != 'CURVE':
            self.report({'WARNING'}, "Pick a valid target curve")
            return {'CANCELLED'}

        clear_generated_ivy_for_curve(curve_obj)
        self.report({'INFO'}, f"Cleared ivy for {curve_obj.name}")
        return {'FINISHED'}


# ------------------------------------------------------------
# Panel
# ------------------------------------------------------------

class VINEIVY_PT_main(Panel):
    bl_label = "Vine / Ivy"
    bl_idname = "VINEIVY_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Vine/Ivy'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.vineivy_settings

        layout.prop(settings, "mode", expand=True)
        layout.separator()

        if settings.mode == 'VINE':
            self.draw_vine(layout, scene, settings)
        else:
            self.draw_ivy(layout, settings)

    def draw_vine(self, layout, scene, settings):
        col = layout.column(align=True)
        col.label(text="Point Objects")
        row = col.row()
        row.template_list(
            "VINEIVY_UL_points",
            "",
            scene,
            "vineivy_point_items",
            scene,
            "vineivy_point_index",
            rows=5,
        )

        buttons = row.column(align=True)
        buttons.operator("vineivy.capture_selected_points", text="", icon='RESTRICT_SELECT_OFF')
        buttons.operator("vineivy.add_active_object_point", text="", icon='ADD')
        buttons.operator("vineivy.remove_point", text="", icon='REMOVE')
        buttons.separator()
        op = buttons.operator("vineivy.move_point", text="", icon='TRIA_UP')
        op.direction = 'UP'
        op = buttons.operator("vineivy.move_point", text="", icon='TRIA_DOWN')
        op.direction = 'DOWN'

        col.operator("vineivy.clear_points", icon='TRASH')

        box = layout.box()
        box.label(text="Vine Shape")
        box.prop(settings, "sag_amount")
        box.prop(settings, "sag_randomness")
        box.prop(settings, "midpoint_side_jitter")
        box.prop(settings, "seed")

        box = layout.box()
        box.label(text="Curve")
        box.prop(settings, "curve_resolution")
        box.prop(settings, "bevel_depth")
        box.prop(settings, "bevel_resolution")
        box.prop(settings, "select_result_curve")

        layout.operator("vineivy.build_vine", icon='CURVE_DATA')

    def draw_ivy(self, layout, settings):
        col = layout.column(align=True)
        col.prop(settings, "target_curve")
        col.operator("vineivy.use_active_curve", icon='EYEDROPPER')

        box = layout.box()
        box.label(text="Leaf Distribution")
        box.prop(settings, "leaf_spacing")
        box.prop(settings, "leaf_size_min")
        box.prop(settings, "leaf_size_max")
        box.prop(settings, "leaf_width_ratio")
        box.prop(settings, "ivy_seed")

        box = layout.box()
        box.label(text="Randomization")
        box.prop(settings, "random_roll_deg")
        box.prop(settings, "offset_normal_min")
        box.prop(settings, "offset_normal_max")
        box.prop(settings, "offset_side")
        box.prop(settings, "offset_along")

        box = layout.box()
        box.label(text="Shading")
        box.prop(settings, "recalc_normals")
        box.prop(settings, "shade_smooth")

        row = layout.row(align=True)
        row.operator("vineivy.generate_ivy", icon='OUTLINER_OB_MESH')
        row.operator("vineivy.clear_ivy", icon='TRASH')


# ------------------------------------------------------------
# Registration
# ------------------------------------------------------------

classes = (
    VINEIVY_PointItem,
    VINEIVY_Settings,
    VINEIVY_UL_points,
    VINEIVY_OT_capture_selected_points,
    VINEIVY_OT_add_active_object_point,
    VINEIVY_OT_remove_point,
    VINEIVY_OT_move_point,
    VINEIVY_OT_clear_points,
    VINEIVY_OT_build_vine,
    VINEIVY_OT_use_active_curve,
    VINEIVY_OT_generate_ivy,
    VINEIVY_OT_clear_ivy,
    VINEIVY_PT_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.vineivy_settings = PointerProperty(type=VINEIVY_Settings)
    bpy.types.Scene.vineivy_point_items = CollectionProperty(type=VINEIVY_PointItem)
    bpy.types.Scene.vineivy_point_index = IntProperty(default=0)


def unregister():
    del bpy.types.Scene.vineivy_settings
    del bpy.types.Scene.vineivy_point_items
    del bpy.types.Scene.vineivy_point_index

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()