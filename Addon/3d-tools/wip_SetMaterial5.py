# Переключает все ноды на Linear (кроме базового цвета) и подключает их на входы материала (работает с постфиксами имён)
# Обрабатывает следующие постфиксы текстур:
#1. BaseColor (постфиксы _BaseColor, _color, _col, _albedo, а также неизвестные текстуры).
#2. Ambient Occlusion (постфиксы _AO, _amb, _occl)
#3. RMA - комбинированная карта, содержащая 3 канала: Roughness, Metallic, AO (постфиксы _RMA).
#4. Roughness (постфиксы _Roughness, _Rough, _R).
#5. Metallic (постфиксы _Metallic, _Metalness, _Metal, _M).
#6. Specular (постфиксы _Specular, _Spec, _S).
#7. Normal (постфиксы _Normal, _nom, _Norm, _N, _NM, _NRM).


bl_info = {
    "name": "[WIP] SetMaterial Texture Setup Tool",
    "author": "Wulfrein",
    "version": (2, 7),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > SetMaterial",
    "description": "Настройка материалов: обработка AO, BaseColor, Specular, Roughness, RMA и Normal текстур",
    "category": "Material",
}

import bpy

class MATERIAL_PT_test_panel(bpy.types.Panel):
    """Панель для настройки материалов"""
    bl_label = "SetMaterial"
    bl_idname = "MATERIAL_PT_test_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SetMaterial"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("material.setup_all_textures", text="Подключить ноды")

class MATERIAL_OT_setup_all_textures(bpy.types.Operator):
    """Оператор настройки всех текстур в материалах"""
    bl_idname = "material.setup_all_textures"
    bl_label = "Подключить ноды"
    bl_description = "Настраивает AO, BaseColor, Specular, Roughness, RMA и Normal текстуры"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Список известных постфиксов (в порядке убывания длины для корректного поиска)
    KNOWN_POSTFIXES = [
        '_basecolor', '_metalness', '_roughness', '_specular',
        '_albedo', '_metallic', '_normal',
        '_color', '_rough', '_metal', '_spec', '_norm', '_nrm',
        '_col', '_amb', '_occl', '_rma', '_nom',
        '_r', '_m', '_s', '_n', '_nm', '_ao'
    ]
    
    def execute(self, context):
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "Нет выбранных объектов")
            return {'CANCELLED'}
        
        processed_materials = set()
        texture_count = 0
        
        for obj in selected_objects:
            if not obj.data or not hasattr(obj.data, 'materials'):
                continue
                
            for material_slot in obj.data.materials:
                material = material_slot
                if not material or not material.node_tree:
                    continue
                
                if material in processed_materials:
                    continue
                processed_materials.add(material)
                
                result = self.process_material(material)
                texture_count += result
        
        if processed_materials:
            self.report({'INFO'}, f"Обработано {len(processed_materials)} материалов, настроено {texture_count} текстур")
        else:
            self.report({'WARNING'}, "Не найдено материалов для обработки")
        
        return {'FINISHED'}
    
    def get_texture_type(self, filename_lower):
        """Определяет тип текстуры по постфиксу"""
        sorted_postfixes = sorted(self.KNOWN_POSTFIXES, key=len, reverse=True)
        
        for postfix in sorted_postfixes:
            if self.is_texture_type(filename_lower, postfix):
                return postfix
        return None
    
    def is_texture_type(self, filename_lower, postfix):
        """Проверяет, является ли файл текстурой определенного типа.
        Постфикс должен быть в конце имени файла, непосредственно перед расширением."""
        dot_pos = filename_lower.rfind('.')
        if dot_pos == -1:
            return False
        
        name_without_ext = filename_lower[:dot_pos]
        return name_without_ext.endswith(postfix)
    
    def connect_roughness_metallic_to_bsdf(self, material, roughness_node, metallic_node):
        """Подключает Roughness и Metallic текстуры напрямую к BSDF"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        if not bsdf_node:
            return
        
        if roughness_node:
            for link in bsdf_node.inputs['Roughness'].links:
                node_tree.links.remove(link)
            node_tree.links.new(roughness_node.outputs[0], bsdf_node.inputs['Roughness'])
        
        if metallic_node:
            for link in bsdf_node.inputs['Metallic'].links:
                node_tree.links.remove(link)
            node_tree.links.new(metallic_node.outputs[0], bsdf_node.inputs['Metallic'])

    def connect_specular_to_bsdf(self, material, specular_node):
        """Подключает Specular текстуру напрямую к BSDF"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        if not bsdf_node:
            return
        
        for link in bsdf_node.inputs['Specular'].links:
            node_tree.links.remove(link)
        node_tree.links.new(specular_node.outputs[0], bsdf_node.inputs['Specular'])

    def connect_alpha_to_bsdf(self, material, basecolor_node):
        """Подключает альфа-канал BaseColor текстуры к BSDF, если он существует"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        if not bsdf_node:
            return
        
        if len(basecolor_node.outputs) > 1:
            for link in list(bsdf_node.inputs['Alpha'].links):
                node_tree.links.remove(link)
            node_tree.links.new(basecolor_node.outputs[1], bsdf_node.inputs['Alpha'])

    def process_material(self, material):
        """Обрабатывает один материал"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        existing_basecolor_node = None
        is_basecolor_in_mix = False
        
        if bsdf_node:
            for link in bsdf_node.inputs['Base Color'].links:
                from_node = link.from_node
                if from_node.type == 'TEX_IMAGE':
                    existing_basecolor_node = from_node
                elif from_node.type == 'MIX':
                    if len(from_node.inputs) > 6:
                        for mix_link in from_node.inputs[6].links:
                            if mix_link.from_node.type == 'TEX_IMAGE':
                                existing_basecolor_node = mix_link.from_node
                                is_basecolor_in_mix = True
                                break
        
        ao_nodes = []
        basecolor_nodes = []
        specular_nodes = []
        roughness_nodes = []
        metallic_nodes = []
        normal_nodes = []
        rma_nodes = []
        unknown_nodes = []
        
        for node in nodes:
            if node.type == 'TEX_IMAGE':
                image = node.image
                if image and image.name:
                    image_name_lower = image.name.lower()
                    texture_type = self.get_texture_type(image_name_lower)
                    
                    if texture_type in ['_ao', '_amb', '_occl']:
                        ao_nodes.append(node)
                    elif texture_type in ['_basecolor', '_color', '_col', '_albedo']:
                        basecolor_nodes.append(node)
                    elif texture_type in ['_specular', '_spec', '_s']:
                        specular_nodes.append(node)
                    elif texture_type in ['_roughness', '_rough', '_r']:
                        roughness_nodes.append(node)
                    elif texture_type in ['_metallic', '_metalness', '_metal', '_m']:
                        metallic_nodes.append(node)
                    elif texture_type in ['_normal', '_nom', '_norm', '_n', '_nm', '_nrm']:
                        normal_nodes.append(node)
                    elif texture_type == '_rma':
                        rma_nodes.append(node)
                    else:
                        unknown_nodes.append(node)
        
        rma_node = None
        ao_node = None
        roughness_node = None
        metallic_node = None
        final_basecolor_node = None
        specular_node = None
        normal_node = None
        
        extra_rma_nodes = []
        extra_roughness_nodes = []
        extra_metallic_nodes = []
        extra_ao_nodes = []
        extra_basecolor_nodes = []
        extra_specular_nodes = []
        extra_normal_nodes = []
        
        nodes_to_disconnect = []
        
        if existing_basecolor_node:
            final_basecolor_node = existing_basecolor_node
            extra_basecolor_nodes = [node for node in basecolor_nodes if node != final_basecolor_node]
            unknown_for_basecolor = [node for node in unknown_nodes if node != final_basecolor_node]
            extra_basecolor_nodes.extend(unknown_for_basecolor)
        else:
            priority_order = ['_basecolor', '_color', '_col', '_albedo']
            for postfix in priority_order:
                for node in basecolor_nodes:
                    image_name_lower = node.image.name.lower()
                    if self.is_texture_type(image_name_lower, postfix):
                        final_basecolor_node = node
                        break
                if final_basecolor_node:
                    break
            
            if not final_basecolor_node and unknown_nodes:
                final_basecolor_node = unknown_nodes[0]
                remaining_unknown = [node for node in unknown_nodes if node != final_basecolor_node]
                extra_basecolor_nodes.extend(remaining_unknown)
                extra_basecolor_nodes.extend(basecolor_nodes)
            elif not final_basecolor_node and basecolor_nodes:
                final_basecolor_node = basecolor_nodes[0]
                extra_basecolor_nodes = [node for node in basecolor_nodes if node != final_basecolor_node]
                extra_basecolor_nodes.extend(unknown_nodes)
            else:
                extra_basecolor_nodes = [node for node in basecolor_nodes if node != final_basecolor_node]
                extra_basecolor_nodes.extend(unknown_nodes)
        
        use_rma = len(rma_nodes) > 0
        
        if use_rma:
            rma_node = rma_nodes[0]
            extra_rma_nodes = rma_nodes[1:]
            extra_roughness_nodes = roughness_nodes.copy()
            extra_metallic_nodes = metallic_nodes.copy()
            extra_ao_nodes = ao_nodes.copy()
            
            nodes_to_disconnect.extend(extra_roughness_nodes)
            nodes_to_disconnect.extend(extra_metallic_nodes)
            nodes_to_disconnect.extend(extra_ao_nodes)
            
            roughness_node = None
            metallic_node = None
            ao_node = None
        else:
            if roughness_nodes:
                roughness_node = roughness_nodes[0]
                extra_roughness_nodes = roughness_nodes[1:]
                nodes_to_disconnect.extend(extra_roughness_nodes)
            
            if metallic_nodes:
                metallic_node = metallic_nodes[0]
                extra_metallic_nodes = metallic_nodes[1:]
                nodes_to_disconnect.extend(extra_metallic_nodes)
            
            if ao_nodes:
                ao_node = ao_nodes[0]
                extra_ao_nodes = ao_nodes[1:]
                nodes_to_disconnect.extend(extra_ao_nodes)
        
        if specular_nodes:
            specular_node = specular_nodes[0]
            extra_specular_nodes = specular_nodes[1:]
            nodes_to_disconnect.extend(extra_specular_nodes)
        
        if normal_nodes:
            normal_node = normal_nodes[0]
            extra_normal_nodes = normal_nodes[1:]
            nodes_to_disconnect.extend(extra_normal_nodes)
        
        nodes_to_disconnect.extend(extra_basecolor_nodes)
        
        for node in nodes_to_disconnect:
            self.disconnect_texture_node(node)
        
        if rma_node:
            self.setup_texture_node(rma_node, 'Linear', -460, 20)
        
        for i, node in enumerate(extra_rma_nodes):
            self.setup_texture_node(node, 'Linear', -800, 20 + (i * -40))
        
        if roughness_node:
            self.setup_texture_node(roughness_node, 'Linear', -460, -20)
        if metallic_node:
            self.setup_texture_node(metallic_node, 'Linear', -460, 60)
        if ao_node:
            self.setup_texture_node(ao_node, 'Linear', -460, 180)
        if specular_node:
            self.setup_texture_node(specular_node, 'Linear', -460, 20)
        if normal_node:
            self.setup_texture_node(normal_node, 'Linear', -460, -300)
        if final_basecolor_node:
            self.setup_texture_node(final_basecolor_node, 'sRGB', -460, 220)
        
        for i, node in enumerate(extra_roughness_nodes):
            self.setup_texture_node(node, 'Linear', -800, -20 + (i * -40))
        
        for i, node in enumerate(extra_metallic_nodes):
            self.setup_texture_node(node, 'Linear', -800, 60 + (i * -40))
        
        for i, node in enumerate(extra_ao_nodes):
            self.setup_texture_node(node, 'Linear', -800, 180 + (i * -40))
        
        for i, node in enumerate(extra_basecolor_nodes):
            self.setup_texture_node(node, 'sRGB', -800, 220 + (i * -40))
        
        for i, node in enumerate(extra_specular_nodes):
            self.setup_texture_node(node, 'Linear', -800, 20 + (i * -40))
        
        for i, node in enumerate(extra_normal_nodes):
            self.setup_texture_node(node, 'Linear', -800, -300 + (i * -40))
        
        texture_count = 0
        
        if rma_node:
            self.setup_rma_texture(material, rma_node, final_basecolor_node)
            texture_count += 1
        else:
            if final_basecolor_node and ao_node:
                self.create_mix_node(material, ao_node, final_basecolor_node, is_basecolor_in_mix)
                texture_count += 2
            elif final_basecolor_node:
                if not existing_basecolor_node or existing_basecolor_node != final_basecolor_node:
                    self.connect_basecolor_to_bsdf(material, final_basecolor_node)
                texture_count += 1
            
            if roughness_node or metallic_node:
                self.connect_roughness_metallic_to_bsdf(material, roughness_node, metallic_node)
                if roughness_node:
                    texture_count += 1
                if metallic_node:
                    texture_count += 1
        
        if normal_node:
            self.setup_normal_map(material, normal_node)
            texture_count += 1
        
        if specular_node:
            self.connect_specular_to_bsdf(material, specular_node)
            texture_count += 1
        
        return texture_count

    def disconnect_texture_node(self, node):
        """Полностью отключает текстурную ноду от всех связей"""
        node_tree = node.id_data
        links_to_remove = []
        
        for socket in node.inputs:
            for link in socket.links:
                links_to_remove.append(link)
        
        for socket in node.outputs:
            for link in socket.links:
                links_to_remove.append(link)
        
        for link in links_to_remove:
            node_tree.links.remove(link)
    
    def setup_texture_node(self, node, color_space, x, y):
        """Настраивает текстурную ноду: Color Space, позиция и сворачивание"""
        image = node.image
        if image:
            if image.colorspace_settings.name != color_space:
                image.colorspace_settings.name = color_space
            
            if not node.hide:
                node.hide = True
            
            node.location.x = x
            node.location.y = y
    
    def connect_basecolor_to_bsdf(self, material, basecolor_node):
        """Подключает BaseColor напрямую к BSDF, включая альфа-канал"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        if bsdf_node:
            for link in bsdf_node.inputs['Base Color'].links:
                node_tree.links.remove(link)
            
            node_tree.links.new(basecolor_node.outputs[0], bsdf_node.inputs['Base Color'])
            self.connect_alpha_to_bsdf(material, basecolor_node)
    
    def create_mix_node(self, material, ao_node, basecolor_node, is_basecolor_in_mix=False):
        """Создает или находит существующую Mix ноду и подключает BaseColor и AO"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        if not bsdf_node:
            return
        
        if not ao_node or not basecolor_node:
            return
        
        mix_node = None
        
        for node in nodes:
            if node.type == 'MIX' and node.name == "Mix BaseColor-AO":
                mix_node = node
                break
        
        if not mix_node:
            try:
                mix_node = nodes.new('ShaderNodeMix')
                mix_node.name = "Mix BaseColor-AO"
                mix_node.label = "Mix BaseColor-AO"
            except Exception:
                return
        
        mix_node.location.x = -200
        mix_node.location.y = 200
        mix_node.data_type = 'RGBA'
        mix_node.blend_type = 'MULTIPLY'
        
        if not mix_node.hide:
            mix_node.hide = True
        
        if len(mix_node.inputs) > 0:
            mix_node.inputs[0].default_value = 1.0
        
        if len(mix_node.inputs) > 6:
            for link in list(mix_node.inputs[6].links):
                node_tree.links.remove(link)
        
        if len(mix_node.inputs) > 7:
            for link in list(mix_node.inputs[7].links):
                node_tree.links.remove(link)
        
        if len(mix_node.inputs) > 6:
            node_tree.links.new(basecolor_node.outputs[0], mix_node.inputs[6])
        
        if len(mix_node.inputs) > 7:
            node_tree.links.new(ao_node.outputs[0], mix_node.inputs[7])
        
        for link in list(bsdf_node.inputs['Base Color'].links):
            node_tree.links.remove(link)
        
        if len(mix_node.outputs) > 2:
            node_tree.links.new(mix_node.outputs[2], bsdf_node.inputs['Base Color'])
        
        self.connect_alpha_to_bsdf(material, basecolor_node)
    
    def setup_normal_map(self, material, normal_texture_node):
        """Находит существующую Normal Map ноду или создает новую, подключает нормаль текстуру в цвет"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        normal_map_node = None
        for node in nodes:
            if node.type == 'NORMAL_MAP' and node.name == "Normal_Map":
                normal_map_node = node
                break
        
        if not normal_map_node:
            try:
                normal_map_node = nodes.new('ShaderNodeNormalMap')
                normal_map_node.name = "Normal_Map"
                normal_map_node.label = "Normal Map"
            except Exception:
                return
        
        normal_map_node.location.x = -180
        normal_map_node.location.y = -300
        
        if not normal_map_node.hide:
            normal_map_node.hide = True
        
        for link in normal_texture_node.outputs[0].links:
            if link.to_node == normal_map_node and link.to_socket == normal_map_node.inputs[1]:
                node_tree.links.remove(link)
                break
        
        node_tree.links.new(normal_texture_node.outputs[0], normal_map_node.inputs[1])
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        if bsdf_node:
            for link in bsdf_node.inputs['Normal'].links:
                node_tree.links.remove(link)
            node_tree.links.new(normal_map_node.outputs[0], bsdf_node.inputs['Normal'])

    def setup_rma_texture(self, material, rma_texture_node, basecolor_node=None):
        """Обрабатывает RMA текстуру: подключает к Separate Color, раскидывает каналы"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        separate_node = None
        for node in nodes:
            if node.name == "Separate RMA" and (node.type == 'SEPCOLOR' or node.type == 'SEPARATE_COLOR'):
                separate_node = node
                break
        
        if not separate_node:
            try:
                separate_node = nodes.new('ShaderNodeSeparateColor')
                separate_node.name = "Separate RMA"
                separate_node.label = "Separate RMA"
            except Exception:
                return
        
        separate_node.location.x = -180
        separate_node.location.y = 20
        
        if not separate_node.hide:
            separate_node.hide = True
        
        for link in rma_texture_node.outputs[0].links:
            if link.to_node == separate_node:
                node_tree.links.remove(link)
        
        node_tree.links.new(rma_texture_node.outputs[0], separate_node.inputs[0])
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        if not bsdf_node:
            return
        
        if len(separate_node.outputs) > 0:
            for link in bsdf_node.inputs['Roughness'].links:
                node_tree.links.remove(link)
            node_tree.links.new(separate_node.outputs[0], bsdf_node.inputs['Roughness'])
        
        if len(separate_node.outputs) > 1:
            for link in bsdf_node.inputs['Metallic'].links:
                node_tree.links.remove(link)
            node_tree.links.new(separate_node.outputs[1], bsdf_node.inputs['Metallic'])
        
        if len(separate_node.outputs) > 2:
            if not basecolor_node:
                for node in nodes:
                    if node.type == 'TEX_IMAGE':
                        image = node.image
                        if image and image.name:
                            image_name_lower = image.name.lower()
                            texture_type = self.get_texture_type(image_name_lower)
                            if texture_type in ['_basecolor', '_color', '_col', '_albedo']:
                                basecolor_node = node
                                break
            
            if basecolor_node:
                self.create_mix_node_for_rma(material, separate_node, basecolor_node, 2)
                # Подключаем альфа-канал BaseColor текстуры
                self.connect_alpha_to_bsdf(material, basecolor_node)

    def create_mix_node_for_rma(self, material, separate_node, basecolor_node, output_index):
        """Создает или находит Mix ноду для RMA Blue канала по имени"""
        node_tree = material.node_tree
        nodes = node_tree.nodes
        
        bsdf_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf_node = node
                break
        
        mix_node = None
        for node in nodes:
            if node.type == 'MIX' and node.name == "Mix BaseColor-AO":
                mix_node = node
                break
        
        if not mix_node:
            try:
                mix_node = nodes.new('ShaderNodeMix')
                mix_node.name = "Mix BaseColor-AO"
                mix_node.label = "Mix BaseColor-AO"
            except Exception:
                return
        
        mix_node.location.x = -200
        mix_node.location.y = 200
        mix_node.data_type = 'RGBA'
        mix_node.blend_type = 'MULTIPLY'
        
        if not mix_node.hide:
            mix_node.hide = True
        
        if len(mix_node.inputs) > 0:
            mix_node.inputs[0].default_value = 1.0
        
        if len(mix_node.inputs) > 6:
            for link in basecolor_node.outputs[0].links:
                if link.to_node == mix_node and link.to_socket == mix_node.inputs[6]:
                    node_tree.links.remove(link)
                    break
        
        if len(mix_node.inputs) > 7:
            for link in separate_node.outputs[output_index].links:
                if link.to_node == mix_node and link.to_socket == mix_node.inputs[7]:
                    node_tree.links.remove(link)
                    break
        
        if len(mix_node.inputs) > 6:
            node_tree.links.new(basecolor_node.outputs[0], mix_node.inputs[6])
        
        if len(mix_node.inputs) > 7:
            node_tree.links.new(separate_node.outputs[output_index], mix_node.inputs[7])
        
        if bsdf_node:
            for link in bsdf_node.inputs['Base Color'].links:
                node_tree.links.remove(link)
            
            if len(mix_node.outputs) > 2:
                node_tree.links.new(mix_node.outputs[2], bsdf_node.inputs['Base Color'])
        
        # Подключаем альфа-канал BaseColor текстуры
        self.connect_alpha_to_bsdf(material, basecolor_node)

# Регистрация классов
classes = [
    MATERIAL_PT_test_panel,
    MATERIAL_OT_setup_all_textures,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()