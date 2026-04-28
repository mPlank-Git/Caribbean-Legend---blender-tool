import bpy
import re
from bpy.types import Panel, Operator

# Добавляем новый оператор для обработки префиксов
class SE_OT_AddBakingPrefix(Operator):
    bl_idname = "se.add_baking_prefix"
    bl_label = "Add Baking Prefixes"
    bl_description = """Process objects and add prefixes based on material names
    
    Scans all visible objects and checks their first material slot.
    Adds prefixes to object names based on material suffixes:
    - Objects with materials with '_sN' or '_aoN' postfix get 'N_' prefix
    - Objects that already have correct prefix are skipped
    - Objects with wrong prefix are corrected with warning
    
    Example:
    Material 'wall_s1' → Object renamed to '1_wall'
    Material 'roof_ao2' → Object renamed to '2_roof'"""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefixed_objects = []
        corrected_objects = []

        # Регулярные выражения для проверки
        prefix_pattern = re.compile(r'^(\d+)_')  # существующий префикс
        suffix_pattern = re.compile(r'_(s|ao)(\d+)(?:_|$)')  # постфиксы в материале

        for obj in bpy.context.scene.objects:
            # Пропускаем объекты, которые исключены из View Layer или невидимы
            if not obj.visible_get() or obj.hide_get():
                continue

            # Получаем материал из первого слота
            if obj.material_slots and obj.material_slots[0].material:
                mat_name = obj.material_slots[0].material.name
                new_prefix = None

                # Ищем номер в постфиксах материала
                match = suffix_pattern.search(mat_name)
                if match:
                    number = match.group(2)
                    new_prefix = f"{number}_"

                if new_prefix:
                    # Проверяем текущее имя объекта
                    current_name = obj.name
                    prefix_match = prefix_pattern.match(current_name)

                    if prefix_match:
                        current_prefix = prefix_match.group(1) + "_"
                        if current_prefix != new_prefix:
                            # Удаляем старый префикс и добавляем новый
                            obj.name = new_prefix + current_name[len(current_prefix):]
                            corrected_objects.append(obj.name)
                            prefixed_objects.append(obj)
                    else:
                        # Добавляем новый префикс
                        obj.name = new_prefix + current_name
                        prefixed_objects.append(obj)

        # Выделяем все объекты, которым добавились префиксы
        if prefixed_objects or corrected_objects:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in prefixed_objects:
                obj.select_set(True)
            if prefixed_objects:
                bpy.context.view_layer.objects.active = prefixed_objects[-1]

            # Выводим предупреждение для исправленных объектов
            if corrected_objects:
                self.report({'WARNING'}, f"Corrected prefixes for objects: {', '.join(corrected_objects)}")
            
            self.report({'INFO'}, f"Processed {len(prefixed_objects)} objects")
        else:
            self.report({'INFO'}, "No objects needed prefixing")

        return {'FINISHED'}

class SE_OT_SelectByPrefix(Operator):
    """Select objects by prefix"""
    bl_idname = "se.select_by_prefix"
    bl_label = "Select By Prefix"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}  # Добавлен 'INTERNAL' чтобы скрыть панель
    
    def execute(self, context):
        # Этот метод теперь будет переопределяться в дочерних классах
        return {'FINISHED'}

class SE_OT_SelectPrefix1(SE_OT_SelectByPrefix):
    """Select objects with prefix 1_"""
    bl_idname = "se.select_prefix1"
    bl_label = "1_Select"
    
    def execute(self, context):
        # Сбрасываем выделение
        bpy.ops.object.select_all(action='DESELECT')
        
        # Ищем все объекты с префиксом 1_
        selected_objects = []
        view_layer = context.view_layer
        baking_collection = bpy.data.collections.get("BAKING")
        
        for obj in bpy.data.objects:
            if obj.name.startswith("1_"):
                # Пропускаем объекты из коллекции BAKING
                if baking_collection and obj.name in baking_collection.objects:
                    continue
                
                # Проверяем, есть ли объект хотя бы в одной коллекции (кроме BAKING)
                if not any(coll for coll in obj.users_collection if coll.name != "BAKING"):
                    continue
                
                try:
                    # Делаем объект видимым
                    obj.hide_viewport = False
                    obj.hide_set(False)
                    obj.hide_select = False
                    
                    # Проверяем доступность в текущем view layer
                    if obj.name in view_layer.objects:
                        obj.select_set(True)
                        selected_objects.append(obj)
                except:
                    continue
        
        if selected_objects:
            context.view_layer.objects.active = selected_objects[-1]
            self.report({'INFO'}, f"Selected {len(selected_objects)} objects with prefix '1_'")
        else:
            self.report({'WARNING'}, "No objects with prefix '1_' found")
        
        return {'FINISHED'}

class SE_OT_SelectPrefix2(SE_OT_SelectByPrefix):
    """Select objects with prefix 2_"""
    bl_idname = "se.select_prefix2"
    bl_label = "2_Select"
    
    def execute(self, context):
        # Аналогичная реализация для префикса 2_
        bpy.ops.object.select_all(action='DESELECT')
        selected_objects = []
        view_layer = context.view_layer
        baking_collection = bpy.data.collections.get("BAKING")
        
        for obj in bpy.data.objects:
            if obj.name.startswith("2_"):
                # Пропускаем объекты из коллекции BAKING
                if baking_collection and obj.name in baking_collection.objects:
                    continue
                
                if not any(coll for coll in obj.users_collection if coll.name != "BAKING"):
                    continue
                
                try:
                    obj.hide_viewport = False
                    obj.hide_set(False)
                    obj.hide_select = False
                    
                    if obj.name in view_layer.objects:
                        obj.select_set(True)
                        selected_objects.append(obj)
                except:
                    continue
        
        if selected_objects:
            context.view_layer.objects.active = selected_objects[-1]
            self.report({'INFO'}, f"Selected {len(selected_objects)} objects with prefix '2_'")
        else:
            self.report({'WARNING'}, "No objects with prefix '2_' found")
        
        return {'FINISHED'}

class SE_OT_SelectPrefix3(SE_OT_SelectByPrefix):
    """Select objects with prefix 3_"""
    bl_idname = "se.select_prefix3"
    bl_label = "3_Select"
    
    def execute(self, context):
        # Аналогичная реализация для префикса 3_
        bpy.ops.object.select_all(action='DESELECT')
        selected_objects = []
        view_layer = context.view_layer
        baking_collection = bpy.data.collections.get("BAKING")
        
        for obj in bpy.data.objects:
            if obj.name.startswith("3_"):
                # Пропускаем объекты из коллекции BAKING
                if baking_collection and obj.name in baking_collection.objects:
                    continue
                
                if not any(coll for coll in obj.users_collection if coll.name != "BAKING"):
                    continue
                
                try:
                    obj.hide_viewport = False
                    obj.hide_set(False)
                    obj.hide_select = False
                    
                    if obj.name in view_layer.objects:
                        obj.select_set(True)
                        selected_objects.append(obj)
                except:
                    continue
        
        if selected_objects:
            context.view_layer.objects.active = selected_objects[-1]
            self.report({'INFO'}, f"Selected {len(selected_objects)} objects with prefix '3_'")
        else:
            self.report({'WARNING'}, "No objects with prefix '3_' found")
        
        return {'FINISHED'}



class SE_OT_BakingButtonBase(Operator):
    """Base baking operator - not used directly"""
    bl_options = {'REGISTER', 'UNDO'}
    
    # Параметры, которые будут переопределены в дочерних классах
    material_name = ""
    object_prefix = ""
    baked_object_name = ""
    
    @classmethod
    def get_description(cls):
        """Генерирует описание оператора динамически"""
        return f"""Prepare objects for baking (shadow{cls.object_prefix[0]})

    Performs the following operations:
    1. Deselects all objects
    2. Deletes old baking objects with prefix '{cls.object_prefix}' from BAKING collection
    3. Makes all objects with prefix '{cls.object_prefix}' visible
    4. Selects all objects with prefix '{cls.object_prefix}'
    5. Checks that all objects have UV2 layer
    6. Renames UV maps according to standard (Float2 for UV1, UVMap_normals for UV2)
    7. Makes original objects invisible for render
    8. Duplicates selected objects
    9. Applies material '{cls.material_name}' to duplicates
    10. Applies all modifiers on duplicated objects
    11. Joins all duplicates into single object
    12. Clears parent relationship (keep transform)
    13. Moves baked object to BAKING collection
    14. Makes baked object visible for render
    15. Deletes UV1 layer (if not named "Float2" shows warning)
    16. Renames object to '{cls.baked_object_name}'

    Note: Works only in Object Mode"""

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        # Проверка наличия материала перед началом выполнения
        baking_material = bpy.data.materials.get(self.material_name)
        if not baking_material:
            self.report({'ERROR'}, f"Material '{self.material_name}' not found! Operation cancelled.")
            return {'CANCELLED'}
            
        # 0. Выход из Local View
        if context.space_data.local_view:
            bpy.ops.view3d.localview()
            
        baking_collection = "BAKING"
        
        # 1. Сбрасываем выделение
        bpy.ops.object.select_all(action='DESELECT')
        
        # 2. Удаляем старые объекты для выпечки
        baking_collection_obj = bpy.data.collections.get(baking_collection)
        if baking_collection_obj:
            for obj in baking_collection_obj.objects:
                if obj.name.startswith(self.object_prefix):
                    bpy.data.objects.remove(obj, do_unlink=True)

        # 3. Ищем все объекты с префиксом
        all_objects = [obj for obj in bpy.data.objects if obj.name.startswith(self.object_prefix)]
        if not all_objects:
            self.report({'WARNING'}, f"No objects with prefix '{self.object_prefix}' found")
            return {'CANCELLED'}

        # 4. Обрабатываем только те объекты, которые можно выделить
        processed_objects = []
        failed_objects = []
        
        for obj in all_objects:
            try:
                if not any(obj.name in coll.objects for coll in bpy.data.collections if coll.name != baking_collection):
                    context.scene.collection.objects.link(obj)
                
                obj.hide_viewport = False
                obj.hide_set(False)
                obj.hide_select = False
                obj.select_set(True)
                processed_objects.append(obj)
            except Exception as e:
                failed_objects.append(obj.name)
                print(f"Failed to process {obj.name}: {str(e)}")

        if not processed_objects:
            self.report({'ERROR'}, f"Could not process any objects with prefix '{self.object_prefix}'")
            return {'CANCELLED'}

        # 5. Проверка наличия UV2
        for obj in processed_objects:
            if obj.type == 'MESH' and len(obj.data.uv_layers) < 2:
                self.report({'ERROR'}, f"Object '{obj.name}' doesn't have UV2")
                return {'CANCELLED'}

        # 6. Переименовываем UV-карты
        bpy.ops.se.uvmap_rename_all()

        # 7. Настраиваем видимость оригиналов для рендера
        for obj in processed_objects:
            obj.hide_render = True

        # 8. Дублируем объекты
        bpy.ops.object.duplicate()
        duplicated_objects = context.selected_objects

        # 9. Применяем материал (материал уже проверен в начале функции)
        for obj in duplicated_objects:
            if obj.type == 'MESH':
                if obj.data.materials:
                    obj.data.materials[0] = baking_material
                else:
                    obj.data.materials.append(baking_material)

        # 10. Применяем модификаторы
        for obj in duplicated_objects:
            if obj.type == 'MESH':
                # Apply all modifiers in reverse order
                for modifier in reversed(obj.modifiers):
                    try:
                        bpy.context.view_layer.objects.active = obj
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                    except Exception as e:
                        print(f"Failed to apply modifier {modifier.name} on {obj.name}: {str(e)}")
                        continue

        # 11. Группируем объекты
        if len(duplicated_objects) > 1:
            context.view_layer.objects.active = duplicated_objects[0]
            bpy.ops.object.join()
            baked_object = context.active_object
        else:
            baked_object = duplicated_objects[0]

        # 12. Открепляем от родителя
        if baked_object.parent:
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

        # 13. Создаем/настраиваем коллекцию BAKING
        if not baking_collection_obj:
            baking_collection_obj = bpy.data.collections.new(baking_collection)
            context.scene.collection.children.link(baking_collection_obj)
            baking_collection_obj['storm_engine_created'] = True
            baking_collection_obj.color_tag = context.preferences.addons['StormEngineTools'].preferences.baking_collection_color

        # Настраиваем видимость коллекции BAKING
        baking_collection_obj.hide_viewport = False      # Глаз - ВКЛ (видима в 3D viewport)
        baking_collection_obj.hide_render = False        # Фотоаппарат - ВКЛ (видима при рендере)
        
        # Функция для поиска layer_collection
        def find_layer_collection(layer_coll, coll_name):
            if layer_coll.name == coll_name:
                return layer_coll
            for child in layer_coll.children:
                found = find_layer_collection(child, coll_name)
                if found:
                    return found
            return None
        
        # Устанавливаем для всех ViewLayers
        for view_layer in context.scene.view_layers:
            layer_collection = find_layer_collection(view_layer.layer_collection, "BAKING")
            if layer_collection:
                layer_collection.exclude = False  # Галка - ВКЛ (не исключать из ViewLayer)
                layer_collection.hide_viewport = False  # Видимость в viewport

        # Перемещаем коллекцию BAKING на первую позицию
        collections = context.scene.collection.children
        current_index = collections.find(baking_collection_obj.name)
        if current_index > 0:
            other_collections = [col for col in collections if col != baking_collection_obj]
            while len(collections) > 0:
                collections.unlink(collections[0])
            collections.link(baking_collection_obj)
            for col in other_collections:
                collections.link(col)

        # Перемещаем объект в коллекцию BAKING
        for coll in baked_object.users_collection:
            coll.objects.unlink(baked_object)
        baking_collection_obj.objects.link(baked_object)

        # 14. Делаем объект видимым для рендера
        baked_object.hide_render = False

        # 15. Удаляем UV1
        if baked_object.type == 'MESH' and len(baked_object.data.uv_layers) > 0:
            uv_layer = baked_object.data.uv_layers[0]
            uv_name = uv_layer.name
            if uv_name != "Float2":
                self.report({'WARNING'}, f"Deleted UV map '{uv_name}'")
            baked_object.data.uv_layers.remove(uv_layer)

        # 16. Переименовываем объект
        baked_object.name = self.baked_object_name

        # Формируем сообщение
        msg = f"Prefix [{self.object_prefix}], material [{self.material_name}]: combined {len(processed_objects)} objects"
        if failed_objects:
            msg += f" (skipped {len(failed_objects)}: excluded from ViewLayer)"
            
        self.report({'INFO'}, msg)
        
        # Если включено автосглаживание - применяем его
        if context.scene.se_auto_smooth:
            bpy.ops.se.bake_smooth()
            
        return {'FINISHED'}

class SE_OT_BakingButton1(SE_OT_BakingButtonBase):
    """Baking Setup 1"""  # Короткое описание для UI
    bl_idname = "se.baking_button1"
    bl_label = "Baking Setup 1"
    
    material_name = "!baking1"
    object_prefix = "1_"
    baked_object_name = "1_Bake"
    
    @classmethod
    def description(cls, context, properties):
        return cls.get_description()

class SE_OT_BakingButton2(SE_OT_BakingButtonBase):
    """Baking Setup 2"""
    bl_idname = "se.baking_button2"
    bl_label = "Baking Setup 2"
    
    material_name = "!baking2"
    object_prefix = "2_"
    baked_object_name = "2_Bake"
    
    @classmethod
    def description(cls, context, properties):
        return cls.get_description()

class SE_OT_BakingButton3(SE_OT_BakingButtonBase):
    """Baking Setup 3"""
    bl_idname = "se.baking_button3"
    bl_label = "Baking Setup 3"
    
    material_name = "!baking3"
    object_prefix = "3_"
    baked_object_name = "3_Bake"
    
    @classmethod
    def description(cls, context, properties):
        return cls.get_description()

class SE_OT_BakeSmooth(Operator):
    """Add Edge Split and merge vertices by distance"""
    bl_idname = "se.bake_smooth"
    bl_label = "Bake Smooth"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Проверяем, что есть выделенные объекты
        if not context.selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        processed_objects = 0

        # Обрабатываем каждый выделенный объект
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            # Проверяем наличие существующего модификатора Edge Split
            for mod in obj.modifiers:
                if mod.type == 'EDGE_SPLIT':
                    # Удаляем существующий модификатор
                    obj.modifiers.remove(mod)
                    break

            # Добавляем новый модификатор Edge Split
            edge_split = obj.modifiers.new(name="EdgeSplit", type='EDGE_SPLIT')
            edge_split.split_angle = 1.13446  # 65 градусов в радианах
            edge_split.use_edge_angle = True
            edge_split.use_edge_sharp = True

            # Сохраняем текущий активный объект и режим
            prev_active = context.view_layer.objects.active
            prev_mode = prev_active.mode if prev_active else 'OBJECT'
            
            # Переходим в режим редактирования
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')

            # Выделяем все вершины
            bpy.ops.mesh.select_all(action='SELECT')

            # Объединяем вершины по расстоянию
            bpy.ops.mesh.remove_doubles(threshold=0.0001)

            # Возвращаемся в режим объектов
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Применяем Shade Auto Smooth
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 1.13446  # 65 градусов в радианах

            # Применяем objects_clear_geom_data
            bpy.ops.se.objects_clear_geom_data()
            
            # Восстанавливаем предыдущий активный объект и режим
            if prev_active:
                context.view_layer.objects.active = prev_active
                if prev_mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode=prev_mode)

            processed_objects += 1

        self.report({'INFO'}, f"Processed {processed_objects} objects")
        return {'FINISHED'}

class SE_OT_ToggleAutoSmooth(Operator):
    """Toggle Auto Smooth mode"""
    bl_idname = "se.toggle_auto_smooth"
    bl_label = "Toggle Auto Smooth"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.se_auto_smooth = not context.scene.se_auto_smooth
        return {'FINISHED'}

    @classmethod
    def description(cls, context, properties):
        return "When enabled, smooth operations will be applied automatically after N_Bake-buttons"

class SE_OT_TimeSelection_First(Operator):
    """Go to first time preset"""
    bl_idname = "se.timeselection_first"
    bl_label = "Go to First"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.se_time_preset = "Day1"
        return {'FINISHED'}

class SE_OT_TimeSelection_Prev(Operator):
    """Go to previous time preset"""
    bl_idname = "se.timeselection_prev"
    bl_label = "Previous"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        time_presets = ["Day1", "Day2", "Day3", "Day4", "Evening", "Morning", "Storm"]
        current_index = time_presets.index(context.scene.se_time_preset)
        new_index = (current_index - 1) % len(time_presets)
        context.scene.se_time_preset = time_presets[new_index]
        return {'FINISHED'}

class SE_OT_TimeSelection_Next(Operator):
    """Go to next time preset"""
    bl_idname = "se.timeselection_next"
    bl_label = "Next"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        time_presets = ["Day1", "Day2", "Day3", "Day4", "Evening", "Morning", "Storm"]
        current_index = time_presets.index(context.scene.se_time_preset)
        new_index = (current_index + 1) % len(time_presets)
        context.scene.se_time_preset = time_presets[new_index]
        return {'FINISHED'}

class SE_OT_TimeSelection_Last(Operator):
    """Go to last time preset"""
    bl_idname = "se.timeselection_last"
    bl_label = "Go to Last"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.se_time_preset = "Storm"
        return {'FINISHED'}

class SE_OT_UpdateWorldLighting(Operator):
    """Update World Lighting based on time preset"""
    bl_idname = "se.update_world_lighting"
    bl_label = "Update World Lighting"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Get the world node tree
        world = context.scene.world
        if not world or not world.node_tree:
            self.report({'ERROR'}, "World node tree not found")
            return {'CANCELLED'}

        # Get the OutsideLighting node group
        outside_lighting = None
        for node in world.node_tree.nodes:
            if node.type == 'GROUP' and node.name == "OutsideLighting":
                outside_lighting = node
                break

        if not outside_lighting:
            self.report({'ERROR'}, "OutsideLighting node group not found")
            return {'CANCELLED'}

        # Get the group node tree
        group_tree = outside_lighting.node_tree
        if not group_tree:
            self.report({'ERROR'}, "OutsideLighting group node tree not found")
            return {'CANCELLED'}

        # Get required nodes
        background = None
        group_output = None
        for node in group_tree.nodes:
            if node.name == "Background":
                background = node
            elif node.name == "GroupOutput":
                group_output = node

        if not background or not group_output:
            self.report({'ERROR'}, "Required nodes not found in group")
            return {'CANCELLED'}

        # Clear existing connections
        for link in group_tree.links:
            group_tree.links.remove(link)

        # Get the sky node based on time preset
        time_preset = context.scene.se_time_preset
        sky_node = None
        
        if time_preset == "Day1":
            sky_node = group_tree.nodes.get("Sky_D1")
        elif time_preset == "Day2":
            sky_node = group_tree.nodes.get("Sky_D2")
        elif time_preset == "Day3":
            sky_node = group_tree.nodes.get("Sky_D3")
        elif time_preset == "Day4":
            sky_node = group_tree.nodes.get("Sky_D4")
        elif time_preset == "Evening":
            sky_node = group_tree.nodes.get("Sky_E1")
        elif time_preset == "Morning":
            sky_node = group_tree.nodes.get("Sky_M1")
        elif time_preset == "Storm":
            sky_node = group_tree.nodes.get("Sky_S1")

        if not sky_node:
            self.report({'ERROR'}, f"Sky node for {time_preset} not found")
            return {'CANCELLED'}

        # Connect nodes
        if time_preset == "Storm":
            # For Storm, connect Sky_S1 directly to GroupOutput
            group_tree.links.new(sky_node.outputs[0], group_output.inputs[0])
        else:
            # For other presets, connect through Background
            group_tree.links.new(sky_node.outputs[0], background.inputs[0])
            group_tree.links.new(background.outputs[0], group_output.inputs[0])

        # Handle shadow textures if enabled
        if context.scene.se_apply_to_shadow_textures:
            # Get active object from BAKING collection
            baking_collection = bpy.data.collections.get("BAKING")
            if baking_collection:
                # Get active object
                active_obj = context.active_object
                if active_obj and active_obj.name.startswith(("1_", "2_", "3_")):
                    # Process based on prefix
                    if active_obj.name.startswith("1_"):
                        material = bpy.data.materials.get("!baking1")
                        if material and material.node_tree:
                            # Get node based on time preset
                            node_name = None
                            if time_preset == "Day1":
                                node_name = "shadow_d1"
                            elif time_preset == "Day2":
                                node_name = "shadow_d2"
                            elif time_preset == "Day3":
                                node_name = "shadow_d3"
                            elif time_preset == "Day4":
                                node_name = "shadow_d4"
                            elif time_preset == "Evening":
                                node_name = "shadow_e1"
                            elif time_preset == "Morning":
                                node_name = "shadow_m1"
                            elif time_preset == "Storm":
                                node_name = "shadow_s1"

                            if node_name:
                                node = material.node_tree.nodes.get(node_name)
                                if node:
                                    # Select the node
                                    for n in material.node_tree.nodes:
                                        n.select = False
                                    node.select = True
                                    material.node_tree.nodes.active = node
                                    
                                    # Update UV Editor if enabled
                                    if context.scene.se_apply_to_uv_editor:
                                        # Find the image texture node with the same name
                                        image_node = material.node_tree.nodes.get(node_name)
                                        if image_node and image_node.type == 'TEX_IMAGE':
                                            # Set active texture in UV Editor
                                            for area in context.screen.areas:
                                                if area.type == 'IMAGE_EDITOR':
                                                    area.spaces.active.image = image_node.image
                                                    area.spaces.active.use_image_pin = False
                                                    break

                    elif active_obj.name.startswith("2_"):
                        material = bpy.data.materials.get("!baking2")
                        if material and material.node_tree:
                            # Get node based on time preset
                            node_name = None
                            if time_preset == "Day1":
                                node_name = "shadow2_d1"
                            elif time_preset == "Day2":
                                node_name = "shadow2_d2"
                            elif time_preset == "Day3":
                                node_name = "shadow2_d3"
                            elif time_preset == "Day4":
                                node_name = "shadow2_d4"
                            elif time_preset == "Evening":
                                node_name = "shadow2_e1"
                            elif time_preset == "Morning":
                                node_name = "shadow2_m1"
                            elif time_preset == "Storm":
                                node_name = "shadow2_s1"

                            if node_name:
                                node = material.node_tree.nodes.get(node_name)
                                if node:
                                    # Select the node
                                    for n in material.node_tree.nodes:
                                        n.select = False
                                    node.select = True
                                    material.node_tree.nodes.active = node
                                    
                                    # Update UV Editor if enabled
                                    if context.scene.se_apply_to_uv_editor:
                                        # Find the image texture node with the same name
                                        image_node = material.node_tree.nodes.get(node_name)
                                        if image_node and image_node.type == 'TEX_IMAGE':
                                            # Set active texture in UV Editor
                                            for area in context.screen.areas:
                                                if area.type == 'IMAGE_EDITOR':
                                                    area.spaces.active.image = image_node.image
                                                    area.spaces.active.use_image_pin = False
                                                    break

                    elif active_obj.name.startswith("3_"):
                        material = bpy.data.materials.get("!baking3")
                        if material and material.node_tree:
                            # Get node based on time preset
                            node_name = None
                            if time_preset == "Day1":
                                node_name = "shadow3_d1"
                            elif time_preset == "Day2":
                                node_name = "shadow3_d2"
                            elif time_preset == "Day3":
                                node_name = "shadow3_d3"
                            elif time_preset == "Day4":
                                node_name = "shadow3_d4"
                            elif time_preset == "Evening":
                                node_name = "shadow3_e1"
                            elif time_preset == "Morning":
                                node_name = "shadow3_m1"
                            elif time_preset == "Storm":
                                node_name = "shadow3_s1"

                            if node_name:
                                node = material.node_tree.nodes.get(node_name)
                                if node:
                                    # Select the node
                                    for n in material.node_tree.nodes:
                                        n.select = False
                                    node.select = True
                                    material.node_tree.nodes.active = node
                                    
                                    # Update UV Editor if enabled
                                    if context.scene.se_apply_to_uv_editor:
                                        # Find the image texture node with the same name
                                        image_node = material.node_tree.nodes.get(node_name)
                                        if image_node and image_node.type == 'TEX_IMAGE':
                                            # Set active texture in UV Editor
                                            for area in context.screen.areas:
                                                if area.type == 'IMAGE_EDITOR':
                                                    area.spaces.active.image = image_node.image
                                                    area.spaces.active.use_image_pin = False
                                                    break

        return {'FINISHED'}

class SE_OT_ToggleBakeClear(Operator):
    """Clear Image\nToggle clearing of the image before baking"""
    bl_idname = "se.toggle_bake_clear"
    bl_label = "Toggle Bake Clear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Получаем настройки bake из render
        bake_settings = context.scene.render.bake
        # Инвертируем текущее состояние
        bake_settings.use_clear = not bake_settings.use_clear
        return {'FINISHED'}

#### ПАНЕЛЬ ########################################################################################################

class SE_PT_BakingPanel(Panel):
    bl_label = "Baking"
    bl_idname = "SE_PT_BakingPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "StormEngineTools"
    bl_order = 3

    @classmethod
    def poll(cls, context):
        # Панель отображается только если включена в настройках аддона
        addon_name = __name__.split(".")[0]  # Получаем имя аддона из модуля
        prefs = context.preferences.addons.get(addon_name)
        if prefs:
            return prefs.preferences.enable_baking_panel
        return False

    def draw(self, context):
        layout = self.layout
        
        # Новая строка с кнопкой Add Baking Prefix
        prefix_row = layout.row()
        prefix_row.operator(
            SE_OT_AddBakingPrefix.bl_idname,
            text="Add Baking Prefix",
            icon='SORTALPHA'
        )
        
        # Основной контейнер для кнопок выпечки с выравниванием
        baking_col = layout.column(align=True)
        
        # Строка с кнопками выбора по префиксу
        select_row = baking_col.row(align=True)
        select_row.operator(SE_OT_SelectPrefix1.bl_idname, text="1_Select")
        select_row.operator(SE_OT_SelectPrefix2.bl_idname, text="2_Select")
        select_row.operator(SE_OT_SelectPrefix3.bl_idname, text="3_Select")
        
        # Строка с кнопками 1_Bake, 2_Bake, 3_Bake
        baking_row = baking_col.row(align=True)
        baking_row.operator(SE_OT_BakingButton1.bl_idname, text="1_Bake")
        baking_row.operator(SE_OT_BakingButton2.bl_idname, text="2_Bake")
        baking_row.operator(SE_OT_BakingButton3.bl_idname, text="3_Bake")
    
        # Вторая строка с кнопкой Bake_smooth и переключателем Auto
        smooth_row = baking_col.row(align=True)
        smooth_row.operator(SE_OT_BakeSmooth.bl_idname, text="Bake_smooth", icon='MOD_SMOOTH')
        
        # Добавляем переключатель Auto справа
        auto_smooth_prop = smooth_row.operator(
            SE_OT_ToggleAutoSmooth.bl_idname,
            text="",
            icon='CHECKBOX_HLT' if context.scene.se_auto_smooth else 'CHECKBOX_DEHLT',
            depress=context.scene.se_auto_smooth
        )
        
        # Остальной код панели остается без изменений
        time_col = layout.column(align=True)
        
        # Time selection row
        time_row = time_col.row(align=True)
        
        # Previous button
        time_row.operator(
            SE_OT_TimeSelection_Prev.bl_idname,
            text="",
            icon='TRIA_LEFT'
        )
        
        # Time selection menu
        time_row.prop(
            context.scene,
            "se_time_preset",
            text=""
        )
        
        # Next button
        time_row.operator(
            SE_OT_TimeSelection_Next.bl_idname,
            text="",
            icon='TRIA_RIGHT'
        )
        
        # Apply to shadow textures checkbox
        time_row.prop(
            context.scene,
            "se_apply_to_shadow_textures",
            text="",
            icon='TEXTURE'
        )
        
        # Apply to UV Editor checkbox
        row = time_row.row(align=True)
        row.enabled = context.scene.se_apply_to_shadow_textures
        row.prop(
            context.scene,
            "se_apply_to_uv_editor",
            text="",
            icon='UV'
        )
        
        # Bake row with Clear Image toggle
        bake_row = time_col.row(align=True)
        
        # Clear Image toggle (icon only)
        bake_settings = context.scene.render.bake
        props = bake_row.operator(
            SE_OT_ToggleBakeClear.bl_idname,
            text="",
            icon='CHECKBOX_HLT' if bake_settings.use_clear else 'CHECKBOX_DEHLT',
            depress=bake_settings.use_clear
        )
        
        # Bake button
        bake_op = bake_row.operator(
            "object.bake", 
            text="Bake", 
            icon='RENDER_STILL'
        )
        bake_op.use_clear = bake_settings.use_clear

# Обновляем список классов для регистрации
classes = (
    SE_OT_AddBakingPrefix,
    SE_OT_SelectByPrefix,
    SE_OT_SelectPrefix1,
    SE_OT_SelectPrefix2,
    SE_OT_SelectPrefix3,
    SE_OT_BakingButton1,
    SE_OT_BakingButton2,
    SE_OT_BakingButton3,
    SE_OT_BakeSmooth,
    SE_OT_ToggleAutoSmooth,
    SE_OT_TimeSelection_First,
    SE_OT_TimeSelection_Prev,
    SE_OT_TimeSelection_Next,
    SE_OT_TimeSelection_Last,
    SE_OT_UpdateWorldLighting,
    SE_OT_ToggleBakeClear,
    SE_PT_BakingPanel,
)

def register():
    # Регистрируем свойства сцены
    bpy.types.Scene.se_time_preset = bpy.props.EnumProperty(
        name="Time Preset",
        description="Current time preset",
        items=[
            ("Day1", "Day1", "Day 1"),
            ("Day2", "Day2", "Day 2"),
            ("Day3", "Day3", "Day 3"),
            ("Day4", "Day4", "Day 4"),
            ("Evening", "Evening", "Evening"),
            ("Morning", "Morning", "Morning"),
            ("Storm", "Storm", "Storm")
        ],
        default="Day1",
        update=lambda self, context: bpy.ops.se.update_world_lighting()
    )
    
    bpy.types.Scene.se_apply_to_shadow_textures = bpy.props.BoolProperty(
        name="Apply to Shadow Textures",
        description="Apply time preset to shadow textures",
        default=True
    )
    
    bpy.types.Scene.se_apply_to_uv_editor = bpy.props.BoolProperty(
        name="Apply to UV Editor",
        description="Apply time preset to UV Editor",
        default=True
    )
    
    bpy.types.Scene.se_bake_clear_image = bpy.props.BoolProperty(
        name="Clear Image",
        description="Clear image before baking",
        default=True
    )
    
    bpy.types.Scene.se_auto_smooth = bpy.props.BoolProperty(
        name="Auto Smooth",
        description="Automatically apply smoothing after baking operations",
        default=False
    )
    
    # Регистрируем все классы
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    # Удаляем регистрацию классов в обратном порядке
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Безопасно удаляем свойства сцены
    scene_props = [
        'se_time_preset',
        'se_apply_to_shadow_textures',
        'se_apply_to_uv_editor',
        'se_auto_smooth',
        'se_bake_clear_image'
    ]
    
    for prop in scene_props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)