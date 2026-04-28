bl_info = {
    "name": "Sailor Points Exporter and Importer",
    "author": "mPlank",
    "blender": (3, 6, 0),
    "category": "Object",
}

import bpy
import os
import bmesh

# Класс для хранения ссылок на другие точки
class SailorLink(bpy.types.PropertyGroup):
    target: bpy.props.StringProperty(name="Target")

# Оператор для добавления точки матроса
class AddSailorPoint(bpy.types.Operator):
    bl_idname = "object.add_sailor_point"
    bl_label = "Add Sailor Point"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Добавляем пустышку в форме сферы
        bpy.ops.object.empty_add(type='SPHERE')
        obj = context.object
        obj.name = f"SP_{len([o for o in bpy.data.objects if o.type == 'EMPTY' and o.name.startswith('SP_')])}_0"
        obj.scale = (0.5, 0.5, 0.5)  # Уменьшаем размер пустышки в 2 раза
        obj["original_index"] = len([o for o in bpy.data.objects if o.type == 'EMPTY' and o.name.startswith('SP_')])
        obj.sailor_links.clear()  # Очищаем существующие ссылки

        # Создаем или получаем коллекцию "SailorPoints"
        collection = bpy.data.collections.get("SailorPoints")
        if collection is None:
            collection = bpy.data.collections.new("SailorPoints")
            context.scene.collection.children.link(collection)
        
        # Перемещаем объект в коллекцию "SailorPoints"
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        collection.objects.link(obj)
        
        return {'FINISHED'}

# Оператор для связывания точек матросов
class LinkSailorPoints(bpy.types.Operator):
    bl_idname = "object.link_sailor_points"
    bl_label = "Link Sailor Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        if len(selected_objects) == 2:
            ob1, ob2 = selected_objects
            
            # Добавляем ссылки в настраиваемое свойство
            link1 = ob1.sailor_links.add()
            link1.target = ob2.name
            
            link2 = ob2.sailor_links.add()
            link2.target = ob1.name
            
            # Создаем линию связи
            link_index = self.get_next_link_index(context)
            link_name = f"line_{link_index}({ob1.name.split('_')[0]}_{ob1.name.split('_')[1]},{ob2.name.split('_')[0]}_{ob2.name.split('_')[1]})"
            self.create_link_line(ob1, ob2, link_name, context)
            
            self.report({'INFO'}, f"Linked {ob1.name} and {ob2.name}")
        else:
            self.report({'WARNING'}, "Select exactly 2 points to link")
        return {'FINISHED'}
    
    def get_next_link_index(self, context):
        max_index = -1
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.name.startswith("line_"):
                try:
                    index = int(obj.name.split('_')[1].split('(')[0])
                    max_index = max(max_index, index)
                except (IndexError, ValueError):
                    continue
        return max_index + 1

    def create_link_line(self, ob1, ob2, link_name, context):
        # Создаем новую линию между двумя пустышками
        mesh = bpy.data.meshes.new(link_name)
        obj = bpy.data.objects.new(link_name, mesh)
        collection = bpy.data.collections.get("SailorPoints")
        if collection is None:
            collection = bpy.data.collections.new("SailorPoints")
            context.scene.collection.children.link(collection)
        collection.objects.link(obj)
        bm = bmesh.new()
        v1 = bm.verts.new(ob1.location)
        v2 = bm.verts.new(ob2.location)
        bm.edges.new((v1, v2))
        bm.to_mesh(mesh)
        bm.free()

# Оператор для экспорта точек матросов
class ExportSailorPoints(bpy.types.Operator):
    bl_idname = "object.export_sailor_points"
    bl_label = "Export Sailor Points"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        points = []
        links = []
        links_set = set()
        
        for obj in bpy.data.objects:
            if obj.type == 'EMPTY' and obj.name.startswith("SP_"):
                points.append(obj)
                for link in obj.sailor_links:
                    if (obj.name, link.target) not in links_set and (link.target, obj.name) not in links_set:
                        links.append((obj.name, link.target))
                        links_set.add((obj.name, link.target))
        
        if not self.filepath:
            self.report({'ERROR'}, "No file path specified")
            return {'CANCELLED'}
        
        # Ensure the file has a .ini extension
        if not self.filepath.lower().endswith('.ini'):
            self.filepath += '.ini'

        try:
            points.sort(key=lambda obj: obj["original_index"])
        except KeyError:
            pass

        with open(bpy.path.abspath(self.filepath), 'w') as file:
            file.write("[SIZE]\n")
            file.write(f"points = {len(points)}\n")
            file.write(f"links = {len(links)}\n\n")
            
            file.write("[POINT_DATA]\n")
            for i, point in enumerate(points):
                # Преобразуем координаты для экспорта с ограничением на 6 знаков после запятой
                x, y, z = point.location
                animation_value = point.get("animation", 0)
                file.write(f"point {i} = {-y:.6f},{z:.6f},{x:.6f},{animation_value}\n")
            
            file.write("\n[LINK_DATA]\n")
            point_index_map = {point.name: i for i, point in enumerate(points)}
            for i, (point_name, target_name) in enumerate(links):
                idx1 = point_index_map[point_name]
                idx2 = point_index_map[target_name]
                file.write(f"link {i} = {idx1},{idx2}\n")
        
        self.report({'INFO'}, f"Exported {len(points)} points and {len(links)} links to {self.filepath}")
        return {'FINISHED'}

# Оператор для импорта точек матросов
class ImportSailorPoints(bpy.types.Operator):
    bl_idname = "object.import_sailor_points"
    bl_label = "Import Sailor Points"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        if not os.path.exists(bpy.path.abspath(self.filepath)):
            self.report({'ERROR'}, "File path does not exist")
            return {'CANCELLED'}

        with open(bpy.path.abspath(self.filepath), 'r') as file:
            data = file.readlines()
        
        points = []
        links = []
        point_data = False
        link_data = False
        
        # Создаем или получаем коллекцию "SailorPoints"
        collection = bpy.data.collections.get("SailorPoints")
        if collection is None:
            collection = bpy.data.collections.new("SailorPoints")
            context.scene.collection.children.link(collection)

        for line in data:
            if line.startswith("[POINT_DATA]"):
                point_data = True
                link_data = False
                continue
            if line.startswith("[LINK_DATA]"):
                point_data = False
                link_data = True
                continue
            if line.startswith("[SIZE]") or line.strip() == "":
                continue
            if point_data:
                parts = line.split("=")
                coords = parts[1].strip().split(",")
                x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                animation_value = int(coords[3]) if len(coords) > 3 else 0
                # Импортируем координаты с нужным преобразованием
                bpy.ops.object.empty_add(type='SPHERE', location=(z, -x, y))
                point = context.object
                point.name = f"SP_{len(points)}_{animation_value}"
                point.scale = (0.5, 0.5, 0.5)  # Уменьшаем размер пустышки в 2 раза
                point["animation"] = animation_value
                point["original_index"] = len(points)
                point.sailor_links.clear()
                points.append(point)
                collection.objects.link(point)
                for coll in point.users_collection:
                    if coll != collection:
                        coll.objects.unlink(point)
            if link_data:
                parts = line.split("=")
                indices = parts[1].strip().split(",")
                idx1, idx2 = int(indices[0]), int(indices[1])
                links.append((idx1, idx2))
        
        for idx1, idx2 in links:
            point1 = points[idx1]
            point2 = points[idx2]
            if point1.name.startswith("SP_") and point2.name.startswith("SP_"):
                link1 = point1.sailor_links.add()
                link1.target = point2.name
                link2 = point2.sailor_links.add()
                link2.target = point1.name
                link_index = self.get_next_link_index(context)
                link_name = f"line_{link_index}({point1.name.split('_')[0]}_{point1.name.split('_')[1]},{point2.name.split('_')[0]}_{point2.name.split('_')[1]})"
                self.create_link_line(point1, point2, link_name, context)
        
        self.report({'INFO'}, f"Imported {len(points)} points and {len(links)} links from {self.filepath}")
        return {'FINISHED'}
    
    def get_next_link_index(self, context):
        max_index = -1
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.name.startswith("line_"):
                try:
                    index = int(obj.name.split('_')[1].split('(')[0])
                    max_index = max(max_index, index)
                except (IndexError, ValueError):
                    continue
        return max_index + 1

    def create_link_line(self, ob1, ob2, link_name, context):
        # Создаем новую линию между двумя пустышками
        mesh = bpy.data.meshes.new(link_name)
        obj = bpy.data.objects.new(link_name, mesh)
        collection = bpy.data.collections.get("SailorPoints")
        if collection is None:
            collection = bpy.data.collections.new("SailorPoints")
            context.scene.collection.children.link(collection)
        collection.objects.link(obj)
        bm = bmesh.new()
        v1 = bm.verts.new(ob1.location)
        v2 = bm.verts.new(ob2.location)
        bm.edges.new((v1, v2))
        bm.to_mesh(mesh)
        bm.free()

# Операторы для установки анимационных значений
class SetAnimationValue(bpy.types.Operator):
    bl_idname = "object.set_animation_value"
    bl_label = "Set Animation Value"
    
    animation_value: bpy.props.IntProperty()
    
    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            # Если пустышки не выбраны, создаем новую пустышку с указанным значением анимации
            bpy.ops.object.empty_add(type='SPHERE')
            obj = context.object
            obj.name = f"SP_{len([o for o in bpy.data.objects if o.type == 'EMPTY' and o.name.startswith('SP_')])}_{self.animation_value}"
            obj.scale = (0.5, 0.5, 0.5)  # Уменьшаем размер пустышки в 2 раза
            obj["animation"] = self.animation_value
            collection = bpy.data.collections.get("SailorPoints")
            if collection is None:
                collection = bpy.data.collections.new("SailorPoints")
                context.scene.collection.children.link(collection)
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            collection.objects.link(obj)
        else:
            for obj in selected_objects:
                if obj.type == 'EMPTY' and obj.name.startswith("SP_"):
                    parts = obj.name.split('_')
                    new_name = f"{parts[0]}_{parts[1]}_{self.animation_value}"
                    obj.name = new_name
                    obj["animation"] = self.animation_value
        return {'FINISHED'}

# Панель инструментов для Sailor Points
class SailorPointsPanel(bpy.types.Panel):
    bl_label = "Sailor Points"
    bl_idname = "OBJECT_PT_sailor_points"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sailor Points'
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("object.add_sailor_point")
        row = layout.row()
        row.operator("object.link_sailor_points")
        row = layout.row()
        row.operator("object.export_sailor_points", text="Export Sailor Points").filepath = context.scene.export_filepath
        row = layout.row()
        row.operator("object.import_sailor_points", text="Import Sailor Points").filepath = context.scene.import_filepath
        row = layout.row()
        row.label(text="Set Animation Value:")
        row = layout.row()
        row.operator("object.set_animation_value", text="0 - Normal").animation_value = 0
        row.operator("object.set_animation_value", text="1 - CanL").animation_value = 1
        row = layout.row()
        row.operator("object.set_animation_value", text="2 - CanR").animation_value = 2
        row.operator("object.set_animation_value", text="3 - CanF").animation_value = 3
        row = layout.row()
        row.operator("object.set_animation_value", text="4 - CanB").animation_value = 4
        row.operator("object.set_animation_value", text="5 - Mast 1").animation_value = 5
        row = layout.row()
        row.operator("object.set_animation_value", text="6 - Mast 2").animation_value = 6
        row.operator("object.set_animation_value", text="7 - Mast 3").animation_value = 7
        row = layout.row()
        row.operator("object.set_animation_value", text="8 - Mast 4").animation_value = 8
        row.operator("object.set_animation_value", text="9 - Mast 5").animation_value = 9
        row = layout.row()
        row.operator("object.set_animation_value", text="10 - Non Target").animation_value = 10
        row = layout.row()
        row.prop(context.scene, "export_filepath", text="Export Filepath")
        row.prop(context.scene, "import_filepath", text="Import Filepath")

def menu_func_export(self, context):
    self.layout.operator(ExportSailorPoints.bl_idname, text="Export Sailor Points")

def menu_func_import(self, context):
    self.layout.operator(ImportSailorPoints.bl_idname, text="Import Sailor Points")

def register():
    bpy.utils.register_class(SailorLink)
    bpy.utils.register_class(AddSailorPoint)
    bpy.utils.register_class(LinkSailorPoints)
    bpy.utils.register_class(ExportSailorPoints)
    bpy.utils.register_class(ImportSailorPoints)
    bpy.utils.register_class(SailorPointsPanel)
    bpy.utils.register_class(SetAnimationValue)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.Object.sailor_links = bpy.props.CollectionProperty(type=SailorLink)
    bpy.types.Scene.export_filepath = bpy.props.StringProperty(
        name="Export Filepath",
        description="Filepath for exporting sailor points data",
        default="//sailor_points.ini",
        subtype='FILE_PATH'
    )
    bpy.types.Scene.import_filepath = bpy.props.StringProperty(
        name="Import Filepath",
        description="Filepath for importing sailor points data",
        default="//sailor_points.ini",
        subtype='FILE_PATH'
    )

def unregister():
    bpy.utils.unregister_class(SailorLink)
    bpy.utils.unregister_class(AddSailorPoint)
    bpy.utils.unregister_class(LinkSailorPoints)
    bpy.utils.unregister_class(ExportSailorPoints)
    bpy.utils.unregister_class(ImportSailorPoints)
    bpy.utils.unregister_class(SailorPointsPanel)
    bpy.utils.unregister_class(SetAnimationValue)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    del bpy.types.Object.sailor_links
    del bpy.types.Scene.export_filepath
    del bpy.types.Scene.import_filepath

if __name__ == "__main__":
    register()
