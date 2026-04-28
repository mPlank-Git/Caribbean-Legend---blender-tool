import bpy
from bpy.types import Panel, Operator
from bpy.props import IntProperty
import mathutils
from math import sqrt

class SE_OT_UVMap_CheckOverlaps(Operator):
    """Check UV2 overlaps with different rules for same/different objects"""
    bl_idname = "se.uvmap_check_overlaps"
    bl_label = "Check UV2 Overlaps"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects and context.mode == 'OBJECT'

    def execute(self, context):
        # First check all selected objects have UV2
        missing_uv2_objects = []
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
                
            if len(obj.data.uv_layers) < 2:
                missing_uv2_objects.append(obj.name)
        
        if missing_uv2_objects:
            obj_list = ", ".join(f"'{name}'" for name in missing_uv2_objects)
            self.report({'WARNING'}, f"UV2 not found in objects: {obj_list}. Operation cancelled.")
            return {'CANCELLED'}

        # Only activate UV2 if all objects have it
        bpy.ops.se.uvmap_set_active2()

        # Proceed with overlap check
        all_polygons = []
        checked_objects = 0
        tolerance = 1e-5

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            checked_objects += 1
            uv_layer = obj.data.uv_layers[1].data

            for poly in obj.data.polygons:
                uv_poly = [uv_layer[loop_idx].uv for loop_idx in poly.loop_indices]
                if len(uv_poly) >= 3:
                    all_polygons.append({
                        'points': uv_poly,
                        'object': obj.name,
                        'index': poly.index
                    })

        # Rest of the overlap checking code...
        total_overlaps = 0
        poly_count = len(all_polygons)

        for i in range(poly_count):
            poly1 = all_polygons[i]
            
            for j in range(i + 1, poly_count):
                poly2 = all_polygons[j]
                
                if poly1['object'] == poly2['object'] and poly1['index'] == poly2['index']:
                    continue

                # Quick bounding box check
                min1, max1 = self.get_poly_bounds(poly1['points'])
                min2, max2 = self.get_poly_bounds(poly2['points'])
                
                if (max1.x < min2.x - tolerance or min1.x > max2.x + tolerance or 
                    max1.y < min2.y - tolerance or min1.y > max2.y + tolerance):
                    continue

                # Different checks for same/different objects
                same_object = poly1['object'] == poly2['object']
                has_overlap = self.check_polygons_overlap(
                    poly1['points'], 
                    poly2['points'], 
                    tolerance,
                    same_object
                )

                if has_overlap:
                    total_overlaps += 1

        # Final report
        if total_overlaps == 0:
            self.report({'INFO'}, f"Checked {poly_count} polygons across {checked_objects} objects. No overlaps found.")
        else:
            self.report({'WARNING'}, f"Found {total_overlaps} overlaps in {poly_count} polygons (checked {checked_objects} objects)")

        return {'FINISHED'}

    def get_poly_bounds(self, poly):
        """Get bounding box of polygon"""
        min_co = mathutils.Vector((float('inf'), float('inf')))
        max_co = mathutils.Vector((float('-inf'), float('-inf')))
        
        for point in poly:
            min_co.x = min(min_co.x, point.x)
            min_co.y = min(min_co.y, point.y)
            max_co.x = max(max_co.x, point.x)
            max_co.y = max(max_co.y, point.y)
            
        return min_co, max_co

    def check_polygons_overlap(self, poly1, poly2, tolerance, same_object):
        """Check overlap with different rules for same/different objects"""
        # For same object: only check interior overlaps
        if same_object:
            return self.has_interior_overlap(poly1, poly2, tolerance)
        
        # For different objects: check both interior and boundary overlaps
        return (self.has_interior_overlap(poly1, poly2, tolerance) or 
                self.has_boundary_overlap(poly1, poly2, tolerance))

    def has_interior_overlap(self, poly1, poly2, tolerance):
        """Check if polygons have interior area overlap"""
        # Check if any point of poly1 is strictly inside poly2
        for point in poly1:
            if self.point_strictly_inside_polygon(point, poly2, tolerance):
                return True
                
        # Check if any point of poly2 is strictly inside poly1
        for point in poly2:
            if self.point_strictly_inside_polygon(point, poly1, tolerance):
                return True
                
        return False

    def has_boundary_overlap(self, poly1, poly2, tolerance):
        """Check if polygons share boundary points/edges"""
        # Check shared vertices
        for p1 in poly1:
            for p2 in poly2:
                if abs(p1.x - p2.x) < tolerance and abs(p1.y - p2.y) < tolerance:
                    return True
        
        # Check edge intersections
        for i in range(len(poly1)):
            edge1_p1 = poly1[i]
            edge1_p2 = poly1[(i + 1) % len(poly1)]
            
            for j in range(len(poly2)):
                edge2_p1 = poly2[j]
                edge2_p2 = poly2[(j + 1) % len(poly2)]
                
                if self.edges_intersect(edge1_p1, edge1_p2, edge2_p1, edge2_p2, tolerance):
                    return True
                    
        return False

    def point_strictly_inside_polygon(self, point, polygon, tolerance):
        """Check if point is strictly inside polygon (not on boundary)"""
        x, y = point.x, point.y
        inside = False
        n = len(polygon)
        
        # Check if point is on any vertex
        for p in polygon:
            if abs(x - p.x) < tolerance and abs(y - p.y) < tolerance:
                return False
                
        p1x, p1y = polygon[0].x, polygon[0].y
        for i in range(n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            
            # Check if point is on current edge
            if self.point_on_segment((x, y), (p1x, p1y), (p2x, p2y), tolerance):
                return False
                
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside

    def edges_intersect(self, a1, a2, b1, b2, tolerance):
        """Check if two edges intersect (not just touch)"""
        def ccw(A, B, C):
            return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)
            
        # Check if edges intersect properly (not just touch)
        return (ccw(a1, b1, b2) != ccw(a2, b1, b2) and 
                ccw(a1, a2, b1) != ccw(a1, a2, b2))

    def point_on_segment(self, point, seg_start, seg_end, tolerance):
        """Check if point lies on segment"""
        px, py = point
        x1, y1 = seg_start
        x2, y2 = seg_end
        
        # Check if point is within segment bounds
        if (px < min(x1, x2) - tolerance or px > max(x1, x2) + tolerance or
            py < min(y1, y2) - tolerance or py > max(y1, y2) + tolerance):
            return False
            
        # Check collinearity
        cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        if abs(cross) > tolerance:
            return False
            
        # Check distance from point to line
        if x1 == x2:
            return True
        else:
            A = (y2 - y1) / (x2 - x1)
            B = y1 - A * x1
            dist = abs(A * px - py + B) / sqrt(A**2 + 1)
            return dist <= tolerance

class SE_OT_UVMap_RenameAll(Operator):
    """Rename UV maps of selected objects: \n - for ID=1 sets name 'Float2' \n - for ID=2 sets name 'UVMap_normals'"""
    bl_idname = "se.uvmap_rename_all"
    bl_label = "Rename All UV Maps"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        renamed = 0
        materials_updated = 0
        original_active = context.active_object
        active_in_selection = original_active and original_active in context.selected_objects
        last_processed = None

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            last_processed = obj
            mesh = obj.data
            uv_layers = mesh.uv_layers
            old_names = [layer.name for layer in uv_layers]

            if len(uv_layers) >= 2:
                uv_layers[1].name = "UVMap_normals"

            if len(uv_layers) >= 1:
                uv_layers[0].name = "Float2"

            renamed += 1

            for slot in obj.material_slots:
                if not slot.material or not slot.material.use_nodes:
                    continue

                for node in slot.material.node_tree.nodes:
                    if node.type == 'UVMAP' and node.uv_map in old_names:
                        if node.uv_map == old_names[0] and len(uv_layers) >= 1:
                            node.uv_map = "Float2"
                            materials_updated += 1
                        elif len(old_names) > 1 and node.uv_map == old_names[1] and len(uv_layers) >= 2:
                            node.uv_map = "UVMap_normals"
                            materials_updated += 1

        if active_in_selection and original_active:
            context.view_layer.objects.active = original_active
        elif last_processed:
            context.view_layer.objects.active = last_processed

        self.report({'INFO'}, f"Renamed UV maps on {renamed} objects, updated {materials_updated} material nodes")
        return {'FINISHED'}

class SE_OT_UVMap_SetActive(Operator):
    """Set active UV map by index\n(Button is gray if all selected UV maps with this ID are already active)"""
    bl_idname = "se.uvmap_set_active"
    bl_label = "Set Active"
    bl_options = {'REGISTER', 'UNDO'}

    uv_index: IntProperty(
        default=-1,
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
            
        index = context.scene.se_uv_index - 1
        has_valid_uvs = False
        all_active = True
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                uv_layers = obj.data.uv_layers
                if 0 <= index < len(uv_layers):
                    has_valid_uvs = True
                    if uv_layers.active != uv_layers[index]:
                        all_active = False
        
        return has_valid_uvs and not all_active

    def execute(self, context):
        index = context.scene.se_uv_index - 1
        activated = 0
        total_meshes = 0
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
                
            total_meshes += 1
            uv_layers = obj.data.uv_layers
            if 0 <= index < len(uv_layers):
                uv_layers.active = uv_layers[index]
                activated += 1

        if total_meshes == 0:
            self.report({'INFO'}, "No mesh objects selected")
        elif activated == 0:
            self.report({'WARNING'}, f"UV Map ID={index+1} not found in any of {total_meshes} selected meshes")
        else:
            self.report({'INFO'}, f"UV Map ID={index+1}: activated [{activated}/{total_meshes}]")
        
        return {'FINISHED'}

class SE_OT_UVMap_SetActive1(Operator):
    """Set active UV map to index 1"""
    bl_idname = "se.uvmap_set_active1"
    bl_label = "Set Active UV1"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
            
        for obj in context.selected_objects:
            if obj.type == 'MESH' and len(obj.data.uv_layers) > 0:
                return True
        return False

    def execute(self, context):
        activated = 0
        total_meshes = 0
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
                
            total_meshes += 1
            uv_layers = obj.data.uv_layers
            if len(uv_layers) > 0:
                uv_layers.active = uv_layers[0]
                activated += 1

        if total_meshes == 0:
            self.report({'INFO'}, "No mesh objects selected")
        elif activated == 0:
            self.report({'WARNING'}, "UV1 not found in any of selected meshes")
        else:
            self.report({'INFO'}, f"UV Map ID=1: activated [{activated}/{total_meshes}]")
        
        return {'FINISHED'}

class SE_OT_UVMap_SetActive2(Operator):
    """Set active UV map to index 2"""
    bl_idname = "se.uvmap_set_active2"
    bl_label = "Set Active UV2"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
            
        for obj in context.selected_objects:
            if obj.type == 'MESH' and len(obj.data.uv_layers) > 1:
                return True
        return False

    def execute(self, context):
        activated = 0
        total_meshes = 0
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
                
            total_meshes += 1
            uv_layers = obj.data.uv_layers
            if len(uv_layers) > 1:
                uv_layers.active = uv_layers[1]
                activated += 1

        if total_meshes == 0:
            self.report({'INFO'}, "No mesh objects selected")
        elif activated == 0:
            self.report({'WARNING'}, "UV2 not found in any of selected meshes")
        else:
            self.report({'INFO'}, f"UV Map ID=2: activated [{activated}/{total_meshes}]")
        
        return {'FINISHED'}

class SE_OT_UVMap_SetName(Operator):
    """Set UV map name by ID"""
    bl_idname = "se.uvmap_set_name"
    bl_label = "Set Name"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.selected_objects or not context.scene.se_uv_name:
            return False
            
        uv_index = context.scene.se_uv_index - 1
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                uv_layers = obj.data.uv_layers
                if 0 <= uv_index < len(uv_layers):
                    return True
        return False

    def execute(self, context):
        set_count = 0
        total_meshes = 0
        uv_name = context.scene.se_uv_name
        uv_index = context.scene.se_uv_index - 1
        original_active = context.active_object
        active_in_selection = original_active and original_active in context.selected_objects
        last_processed = None

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            total_meshes += 1
            uv_layers = obj.data.uv_layers
            if 0 <= uv_index < len(uv_layers):
                last_processed = obj
                uv_layers[uv_index].name = uv_name
                set_count += 1

        if active_in_selection and original_active:
            context.view_layer.objects.active = original_active
        elif last_processed:
            context.view_layer.objects.active = last_processed

        if total_meshes == 0:
            self.report({'INFO'}, "No mesh objects selected")
        elif set_count == 0:
            self.report({'WARNING'}, f"UV Map ID={uv_index+1} not found in any of {total_meshes} selected meshes")
        else:
            self.report({'INFO'}, f"UV Map ID={uv_index+1}: renamed [{set_count}/{total_meshes}]")

        return {'FINISHED'}

class SE_OT_UVMap_CreateNew(Operator):
    """Create new UV map with specified ID if it doesn't exist\n(Note: Creates only one layer, doesn't create intermediate layers)"""
    bl_idname = "se.uvmap_create_new"
    bl_label = "Create New"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
            
        uv_index = context.scene.se_uv_index - 1
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
                
            if len(obj.data.uv_layers) <= uv_index:
                return True
                
        return False

    def execute(self, context):
        scene = context.scene
        prefs = context.preferences.addons[__name__.split(".")[0]].preferences
        uv_name = scene.se_uv_name if scene.se_uv_name != "UVMap_normals" else prefs.default_uv_name
        uv_index = scene.se_uv_index - 1
        created = 0

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            uv_layers = obj.data.uv_layers
            
            if len(uv_layers) > uv_index:
                continue
                
            new_uv = uv_layers.new(name=uv_name)
            created += 1
            uv_layers.active = new_uv

        self.report({'INFO'}, f"Created UV maps for {created} objects (ID: {uv_index + 1})")
        return {'FINISHED'}

class SE_OT_UVMap_DeleteByID(Operator):
    """Delete UV map with specified ID if it exists"""
    bl_idname = "se.uvmap_delete_active"
    bl_label = "Delete by ID"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
            
        uv_index = context.scene.se_uv_index - 1
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                uv_layers = obj.data.uv_layers
                if 0 <= uv_index < len(uv_layers):
                    return True
        return False

    def execute(self, context):
        deleted = 0
        total_meshes = 0
        uv_index = context.scene.se_uv_index - 1
        original_active = context.active_object
        active_in_selection = original_active and original_active in context.selected_objects
        last_processed = None

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            total_meshes += 1
            mesh = obj.data
            uv_layers = mesh.uv_layers
            
            if 0 <= uv_index < len(uv_layers):
                last_processed = obj
                uv_layers.remove(uv_layers[uv_index])
                deleted += 1

        if active_in_selection and original_active:
            context.view_layer.objects.active = original_active
        elif last_processed:
            context.view_layer.objects.active = last_processed

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        if total_meshes == 0:
            self.report({'INFO'}, "No mesh objects selected")
        elif deleted == 0:
            self.report({'WARNING'}, f"UV Map ID={uv_index+1} not found in any of {total_meshes} selected meshes")
        else:
            self.report({'INFO'}, f"UV Map ID={uv_index+1}: deleted [{deleted}/{total_meshes}]")

        return {'FINISHED'}

class SE_OT_UVMap_ResetName(Operator):
    """Reset UV map name to default from addon preferences"""
    bl_idname = "se.uvmap_reset_name"
    bl_label = "Reset UV Name"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.se_uv_name = context.preferences.addons["StormEngineTools"].preferences.default_uv_name
        return {'FINISHED'}

class SE_OT_UVAdvanced_Toggle(Operator):
    """Show/Hide More Options"""
    bl_idname = "se.uvadvanced_toggle"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.se_uv_settings_collapsed = not context.scene.se_uv_settings_collapsed
        return {'FINISHED'}

class SE_PT_UVMapPanel(Panel):
    bl_label = "UV Maps"
    bl_idname = "SE_PT_UVMapPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "StormEngineTools"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        # Панель отображается только если включена в настройках аддона
        addon_name = __name__.split(".")[0]  # Получаем имя аддона из модуля
        prefs = context.preferences.addons.get(addon_name)
        if prefs:
            return prefs.preferences.enable_uvmaps_panel
        return False

    max_uv_id = 10

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        
        main_row = col.row(align=True)
        
        left_col = main_row.column(align=True)
        left_col.scale_x = 1.0
        
        left_col.operator(
            SE_OT_UVMap_CreateNew.bl_idname,
            text="",
            icon='ADD'
        )
        
        uv_advanced_btn = left_col.operator(
            SE_OT_UVAdvanced_Toggle.bl_idname, 
            text="", 
            icon='DISCLOSURE_TRI_DOWN' if not context.scene.se_uv_settings_collapsed else 'DISCLOSURE_TRI_RIGHT',
            emboss=True
        )
        
        rename_col = main_row.column(align=True)
        rename_col.scale_x = 1.5
        rename_col.scale_y = 2.0
        
        rename_col.operator(
            SE_OT_UVMap_RenameAll.bl_idname, 
            text="Rename All UV Maps"
        )

        right_col = main_row.column(align=True)
        right_col.scale_x = 0.35
        
        right_col.operator(
            SE_OT_UVMap_SetActive1.bl_idname,
            text="1"
        )
        
        right_col.operator(
            SE_OT_UVMap_SetActive2.bl_idname,
            text="2"
        )
        
        if not context.scene.se_uv_settings_collapsed:
            box = col.box()
            uv_advanced_col = box.column(align=True)
            
            row = uv_advanced_col.row(align=True)
            label_col = row.row(align=True)
            label_col.scale_x = 0.5
            label_col.label(text="Name:")
            
            input_col = row.row(align=True)
            input_col.scale_x = 1.4
            input_col.prop(context.scene, "se_uv_name", text="")
            
            reset_col = row.row(align=True)
            reset_col.scale_x = 1.0
            reset_col.operator(SE_OT_UVMap_ResetName.bl_idname, text="", icon='LOOP_BACK')
            
            row = uv_advanced_col.row(align=True)
            
            row.prop(context.scene, "se_uv_index", text="ID")
                   
            add_col_btn = row.operator(SE_OT_UVMap_CreateNew.bl_idname, text="", icon='ADD')
            
            set_active_btn = row.operator(SE_OT_UVMap_SetActive.bl_idname, text="", icon='RESTRICT_SELECT_OFF')
            set_active_btn.uv_index = -1
                   
            rename_col_btn = row.operator(SE_OT_UVMap_SetName.bl_idname, text="", icon='GREASEPENCIL')
            
            row.operator(
                SE_OT_UVMap_DeleteByID.bl_idname, 
                text="", 
                icon='TRASH'
            )
            
            # Проверка пересечений на развертке - тормомзит на больших объектах
            #row.operator(
            #    SE_OT_UVMap_CheckOverlaps.bl_idname,
            #    text="",
            #    icon='MOD_UVPROJECT'
            #)

classes = (
    SE_OT_UVAdvanced_Toggle,
    SE_OT_UVMap_RenameAll,
    SE_OT_UVMap_SetActive,
    SE_OT_UVMap_SetActive1,
    SE_OT_UVMap_SetActive2,
    SE_OT_UVMap_SetName,
    SE_OT_UVMap_CreateNew,
    SE_OT_UVMap_DeleteByID,
    SE_OT_UVMap_ResetName,
    SE_OT_UVMap_CheckOverlaps,
    SE_PT_UVMapPanel,
)

def register():
    # Регистрируем классы
    for cls in classes:
        bpy.utils.register_class(cls)

    # Добавляем свойства сцены
    bpy.types.Scene.se_uv_index = bpy.props.IntProperty(
        name="UV Index",
        description="UV Map index (1-based)",
        default=2,  # Изменено с 1 на 2
        min=1,
        max=SE_PT_UVMapPanel.max_uv_id
    )
    
    bpy.types.Scene.se_uv_name = bpy.props.StringProperty(
        name="UV Name",
        description="UV Map name to set",
        default="UVMap_normals"
    )
    
    bpy.types.Scene.se_uv_settings_collapsed = bpy.props.BoolProperty(
        name="UV Settings Collapsed",
        description="Collapse advanced UV settings",
        default=True
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Safely delete scene properties
    scene_props = [
        'se_uv_index',
        'se_uv_name',
        'se_uv_settings_collapsed',
    ]
    
    for prop in scene_props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)