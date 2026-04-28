# Переименовывает имена текстур и пути до текстур с .tga.tx на .tga
# (но вообще можно вписать свои замены)
# Добавлены раздельные опции: Change name и Change path

bl_info = {
    "name": "Texture Renamer",
    "author": "Wulfrein",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > UI > StormEngineWIP",
    "description": "Find and replace texture names and paths in materials",
    "category": "Material",
}

import bpy
import os


class TEXTURE_OT_rename_textures(bpy.types.Operator):
    """Operator for renaming textures and paths"""
    bl_idname = "texture.rename_textures"
    bl_label = "Rename Textures"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        search_text = scene.texture_rename_search
        replace_text = scene.texture_rename_replace
        
        # Проверка настройки опций
        change_name = scene.texture_rename_change_name
        change_path = scene.texture_rename_change_path
        
        if not search_text:
            self.report({'WARNING'}, "Search text is not specified!")
            return {'CANCELLED'}
        
        if not change_name and not change_path:
            self.report({'WARNING'}, "Please enable at least one option: 'Change name' or 'Change path'")
            return {'CANCELLED'}
        
        renamed_count = 0
        
        # Process all materials
        for material in bpy.data.materials:
            if material.use_nodes and material.node_tree:
                # Process all nodes in material
                for node in material.node_tree.nodes:
                    # Check image nodes
                    if node.type == 'TEX_IMAGE' and node.image:
                        changed = False
                        
                        # Replace in name (if option enabled)
                        if change_name and search_text in node.image.name:
                            new_name = node.image.name.replace(search_text, replace_text)
                            node.image.name = new_name
                            changed = True
                        
                        # Replace in path (if option enabled)
                        if change_path and search_text in node.image.filepath:
                            new_path = node.image.filepath.replace(search_text, replace_text)
                            node.image.filepath = new_path
                            changed = True
                        
                        if changed:
                            renamed_count += 1
        
        self.report({'INFO'}, f"Renamed {renamed_count} textures (name and/or path)")
        return {'FINISHED'}


class TEXTURE_PT_rename_panel(bpy.types.Panel):
    """Panel for texture renaming tool"""
    bl_label = "Texture Renamer"
    bl_idname = "TEXTURE_PT_rename_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "StormEngineWIP"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Input fields - плотно друг к другу, без бокса (светлый фон)
        col = layout.column(align=True)
        
        # Используем split для контроля ширины лейблов
        split = col.split(factor=0.35)
        split.label(text="Find:")
        split.prop(scene, "texture_rename_search", text="")
        
        split = col.split(factor=0.35)
        split.label(text="Replace:")
        split.prop(scene, "texture_rename_replace", text="")
        
        # Box for checkboxes - на тёмном фоне
        box = layout.box()
        col = box.column(align=True)
        col.prop(scene, "texture_rename_change_name", text="Change name")
        col.prop(scene, "texture_rename_change_path", text="Change path")
        
        # Button
        layout.operator("texture.rename_textures", text="Replace", icon='FILE_REFRESH')


# Scene properties for storing input field values
def register_properties():
    bpy.types.Scene.texture_rename_search = bpy.props.StringProperty(
        name="Search Text",
        description="Text to search for in texture names and paths",
        default="tga.tx"
    )
    
    bpy.types.Scene.texture_rename_replace = bpy.props.StringProperty(
        name="Replace Text",
        description="Text to replace found matches with",
        default="tga"
    )
    
    bpy.types.Scene.texture_rename_change_name = bpy.props.BoolProperty(
        name="Change Name",
        description="Replace text in texture name",
        default=True
    )
    
    bpy.types.Scene.texture_rename_change_path = bpy.props.BoolProperty(
        name="Change Path",
        description="Replace text in texture file path",
        default=False
    )


def unregister_properties():
    del bpy.types.Scene.texture_rename_search
    del bpy.types.Scene.texture_rename_replace
    del bpy.types.Scene.texture_rename_change_name
    del bpy.types.Scene.texture_rename_change_path


def register():
    register_properties()
    bpy.utils.register_class(TEXTURE_OT_rename_textures)
    bpy.utils.register_class(TEXTURE_PT_rename_panel)


def unregister():
    bpy.utils.unregister_class(TEXTURE_PT_rename_panel)
    bpy.utils.unregister_class(TEXTURE_OT_rename_textures)
    unregister_properties()


if __name__ == "__main__":
    register()