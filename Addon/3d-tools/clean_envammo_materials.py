bl_info = {
    "name": "Clean EnvAmmo Materials",
    "author": "ChatGPT",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > GM Tools",
    "description": "Removes EnvAmmo texture mixing setup and reconnects main texture directly to Principled BSDF for selected objects",
    "category": "Material",
}

import bpy


ENVAMMO_KEYWORDS = [
    "envammo",
    "env_ammo",
    "env ammo",
]


MIX_NODE_TYPES = {
    "ShaderNodeMix",
    "ShaderNodeMixRGB",
    "ShaderNodeMath",
    "ShaderNodeVectorMath",
}


def is_envammo_image_node(node):
    if node.type != "TEX_IMAGE":
        return False

    names = []

    if node.name:
        names.append(node.name.lower())

    if node.label:
        names.append(node.label.lower())

    if node.image:
        if node.image.name:
            names.append(node.image.name.lower())
        if node.image.filepath:
            names.append(node.image.filepath.lower())

    for name in names:
        for keyword in ENVAMMO_KEYWORDS:
            if keyword in name:
                return True

    return False


def get_node_socket(node, socket_name):
    if not node:
        return None

    for socket in node.inputs:
        if socket.name == socket_name:
            return socket

    for socket in node.outputs:
        if socket.name == socket_name:
            return socket

    return None


def find_principled_bsdf(nodes):
    for node in nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def find_material_output(nodes):
    for node in nodes:
        if node.type == "OUTPUT_MATERIAL":
            return node
    return None


def find_main_texture_node(nodes):
    image_nodes = [
        node for node in nodes
        if node.type == "TEX_IMAGE" and not is_envammo_image_node(node)
    ]

    if not image_nodes:
        return None

    preferred = []

    bad_keywords = [
        "normal",
        "nrm",
        "_nm",
        "-nm",
        "spec",
        "gloss",
        "rough",
        "metal",
        "height",
        "bump",
        "ao",
        "mask",
        "env",
        "ammo",
    ]

    for node in image_nodes:
        full_name = ""

        if node.name:
            full_name += node.name.lower() + " "

        if node.label:
            full_name += node.label.lower() + " "

        if node.image:
            if node.image.name:
                full_name += node.image.name.lower() + " "
            if node.image.filepath:
                full_name += node.image.filepath.lower() + " "

        if not any(keyword in full_name for keyword in bad_keywords):
            preferred.append(node)

    if preferred:
        return preferred[0]

    return image_nodes[0]


def remove_links_to_socket(node_tree, socket):
    links_to_remove = []

    for link in node_tree.links:
        if link.to_socket == socket or link.from_socket == socket:
            links_to_remove.append(link)

    for link in links_to_remove:
        node_tree.links.remove(link)


def remove_node_safe(node_tree, node):
    try:
        node_tree.nodes.remove(node)
        return True
    except Exception:
        return False


def is_cleanup_node(node):
    if node.type in {"MIX", "MIX_RGB"}:
        return True

    if node.type == "MATH":
        operation = getattr(node, "operation", "")
        if operation in {"MULTIPLY", "DIVIDE"}:
            return True

    if node.bl_idname in MIX_NODE_TYPES:
        return True

    return False


def clean_material(material):
    if not material or not material.use_nodes:
        return {
            "changed": False,
            "reason": "Material has no nodes",
            "removed": 0,
        }

    node_tree = material.node_tree
    nodes = node_tree.nodes
    links = node_tree.links

    principled = find_principled_bsdf(nodes)

    if not principled:
        return {
            "changed": False,
            "reason": "No Principled BSDF",
            "removed": 0,
        }

    main_texture = find_main_texture_node(nodes)

    if not main_texture:
        return {
            "changed": False,
            "reason": "No main texture found",
            "removed": 0,
        }

    removed_count = 0

    base_color_socket = principled.inputs.get("Base Color")
    alpha_socket = principled.inputs.get("Alpha")

    if base_color_socket:
        remove_links_to_socket(node_tree, base_color_socket)
        color_output = main_texture.outputs.get("Color")
        if color_output:
            links.new(color_output, base_color_socket)

    if alpha_socket:
        remove_links_to_socket(node_tree, alpha_socket)
        alpha_output = main_texture.outputs.get("Alpha")
        if alpha_output:
            links.new(alpha_output, alpha_socket)

    nodes_to_remove = []

    for node in list(nodes):
        if node == main_texture:
            continue

        if node == principled:
            continue

        if node.type == "OUTPUT_MATERIAL":
            continue

        if node.type == "UVMAP":
            continue

        if is_envammo_image_node(node):
            nodes_to_remove.append(node)
            continue

        if is_cleanup_node(node):
            nodes_to_remove.append(node)
            continue

    for node in nodes_to_remove:
        if remove_node_safe(node_tree, node):
            removed_count += 1

    material.blend_method = "BLEND"
    material.use_screen_refraction = False
    material.show_transparent_back = True

    return {
        "changed": True,
        "reason": "Cleaned",
        "removed": removed_count,
        "main_texture": main_texture.name,
    }


class GMTOOLS_OT_clean_envammo_materials(bpy.types.Operator):
    bl_idname = "gmtools.clean_envammo_materials"
    bl_label = "Clean EnvAmmo Materials"
    bl_description = "Clean EnvAmmo texture mixing setup on selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selected_objects = [
            obj for obj in context.selected_objects
            if obj.type == "MESH"
        ]

        if not selected_objects:
            self.report({"WARNING"}, "No selected mesh objects")
            return {"CANCELLED"}

        processed_materials = set()
        cleaned_count = 0
        skipped_count = 0
        removed_nodes_total = 0

        print("\n=== Clean EnvAmmo Materials ===")

        for obj in selected_objects:
            for slot in obj.material_slots:
                material = slot.material

                if not material:
                    continue

                if material.name in processed_materials:
                    continue

                processed_materials.add(material.name)

                result = clean_material(material)

                if result["changed"]:
                    cleaned_count += 1
                    removed_nodes_total += result.get("removed", 0)

                    print(
                        f"[CLEANED] {material.name} | "
                        f"Main texture: {result.get('main_texture', 'Unknown')} | "
                        f"Removed nodes: {result.get('removed', 0)}"
                    )
                else:
                    skipped_count += 1
                    print(
                        f"[SKIPPED] {material.name} | "
                        f"Reason: {result.get('reason', 'Unknown')}"
                    )

        print("=== Done ===")
        print(f"Cleaned materials: {cleaned_count}")
        print(f"Skipped materials: {skipped_count}")
        print(f"Removed nodes total: {removed_nodes_total}")
        print("===============================\n")

        self.report(
            {"INFO"},
            f"Cleaned: {cleaned_count}, skipped: {skipped_count}, removed nodes: {removed_nodes_total}"
        )

        return {"FINISHED"}


class GMTOOLS_PT_clean_envammo_panel(bpy.types.Panel):
    bl_label = "GM Material Tools"
    bl_idname = "GMTOOLS_PT_clean_envammo_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "GM Tools"

    def draw(self, context):
        layout = self.layout
        layout.operator(
            GMTOOLS_OT_clean_envammo_materials.bl_idname,
            icon="NODETREE"
        )


classes = (
    GMTOOLS_OT_clean_envammo_materials,
    GMTOOLS_PT_clean_envammo_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()