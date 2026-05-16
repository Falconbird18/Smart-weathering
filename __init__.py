bl_info = {
    "name": "Smart Weathering",
    "author": "Austin Tallent (Falconbird18)",
    "version": (0, 5),
    "blender": (5, 1, 0),
    "location": "View3D > N-Panel > Weathering",
    "description": "Smart weathering tool that is powerful and easy to use.",
    "category": "Material",
}

import importlib
import os
import sys

import bpy

# ====================== AUTO-RELOAD ======================
# Define modules to reload (add submodules here as needed)
modules_to_reload = [
    __name__,  # Reload the main addon module
]

# Reload existing modules
for module_name in modules_to_reload:
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])


# ====================== PREFERENCES ======================
class SmartWeatheringPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    custom_assets_path: bpy.props.StringProperty(
        name="Custom Assets Path",
        description="Path to a custom assets.blend file. Leave empty to use the default addon assets",
        subtype="FILE_PATH",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "custom_assets_path")
        layout.label(
            text="Restart Blender or reload the addon after changing the path",
            icon="INFO",
        )


# ====================== PATH HELPER ======================
def get_library_path():
    """Return custom path if set and valid, otherwise default addon assets.blend"""
    # Check user preference
    addon_prefs = bpy.context.preferences.addons.get(__name__)
    if addon_prefs and hasattr(addon_prefs, "preferences"):
        custom_path = addon_prefs.preferences.custom_assets_path
        if custom_path:
            abs_path = bpy.path.abspath(custom_path)
            if os.path.exists(abs_path) and abs_path.lower().endswith(".blend"):
                return abs_path

    # Fallback to default
    addon_dir = os.path.dirname(__file__)
    return os.path.join(addon_dir, "assets.blend")


# ====================== LINK FUNCTION ======================
def get_linked_node_group(group_name):
    """
    Get or link a node group from assets.blend.
    Returns the linked node group, or None if not found.
    """
    lib_path = get_library_path()
    if not os.path.exists(lib_path):
        print(f"Warning: Assets file not found at {lib_path}")
        return None

    # Ensure the library is loaded
    lib = None
    for library in bpy.data.libraries:
        if os.path.abspath(library.filepath) == os.path.abspath(lib_path):
            lib = library
            break

    # Link the node group
    with bpy.data.libraries.load(lib_path, link=True) as (data_from, data_to):
        if group_name not in data_from.node_groups:
            print(f"Warning: Node group '{group_name}' not found in {lib_path}")
            return None
        data_to.node_groups = [group_name]

    # Return the linked node group
    if data_to.node_groups:
        return data_to.node_groups[0]

    return None


# ====================== UI PANEL ======================
class VIEW3D_PT_WeatheringPanel(bpy.types.Panel):
    bl_label = "Weathering Controls"
    bl_idname = "VIEW3D_PT_weathering"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Weathering"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if not obj or obj.type != "MESH" or not obj.active_material:
            layout.label(text="Select mesh with material", icon="INFO")
            return

        mat = obj.active_material
        nodes = mat.node_tree.nodes if mat.use_nodes else None
        weather_node = nodes.get("WeatheringNodeInstance") if nodes else None

        btn_text = "Remove Weathering" if weather_node else "Add Weathering"
        icon = "TRASH" if weather_node else "ADD"

        layout.operator("object.toggle_weathering", text=btn_text, icon=icon)
        layout.operator(
            "object.reload_weathering", text="Reload Nodes", icon="FILE_REFRESH"
        )

        if weather_node:
            layout.separator()
            layout.template_node_view(mat.node_tree, weather_node, None)


# ====================== OPERATORS ======================
class OBJECT_OT_ToggleWeathering(bpy.types.Operator):
    bl_idname = "object.toggle_weathering"
    bl_label = "Toggle Weathering"

    def execute(self, context):
        obj = context.active_object
        mat = obj.active_material
        if not mat or not mat.use_nodes:
            self.report({"WARNING"}, "Active material requires 'Use Nodes'.")
            return {"CANCELLED"}

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        weather_node = nodes.get("WeatheringNodeInstance")

        if weather_node:
            # Remove logic - simply remove the node, no data cleanup needed
            mod = obj.modifiers.get("SmartWeathering_Bounds")
            if mod:
                obj.modifiers.remove(mod)

            output_node = next(
                (
                    n
                    for n in nodes
                    if n.type == "OUTPUT_MATERIAL" and n.is_active_output
                ),
                None,
            )
            if output_node:
                surface_input = output_node.inputs.get("Surface")
                if surface_input:
                    # If the weathering node has input, reconnect it
                    if weather_node.inputs[0].is_linked:
                        source_socket = weather_node.inputs[0].links[0].from_socket
                        links.new(source_socket, surface_input)
                    elif surface_input.is_linked:
                        links.remove(surface_input.links[0])

            # Simply remove the node from the tree
            nodes.remove(weather_node)
            self.report({"INFO"}, "Weathering removed.")
        else:
            # Add logic - link shader nodes from assets.blend
            output_node = next(
                (
                    n
                    for n in nodes
                    if n.type == "OUTPUT_MATERIAL" and n.is_active_output
                ),
                None,
            )
            if not output_node:
                return {"CANCELLED"}

            surface_input = output_node.inputs.get("Surface")

            # Add geometry nodes modifier with linked node group
            gn_group = get_linked_node_group("Get Bounding Box")
            if gn_group:
                mod = obj.modifiers.get("SmartWeathering_Bounds") or obj.modifiers.new(
                    name="SmartWeathering_Bounds", type="NODES"
                )
                mod.node_group = gn_group
                try:
                    bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
                except:
                    pass

            # Get linked shader group
            shader_group = get_linked_node_group("Smart Weathering")
            if not shader_group:
                self.report({"ERROR"}, "Failed to link 'Smart Weathering' node group.")
                return {"CANCELLED"}

            # Create shader node with linked group
            weather_node = nodes.new(type="ShaderNodeGroup")
            weather_node.name = "WeatheringNodeInstance"
            weather_node.node_tree = shader_group
            weather_node.location = (
                output_node.location.x - 300,
                output_node.location.y,
            )

            # Connect the shader node into the material
            if surface_input.is_linked:
                old_link = surface_input.links[0]
                links.new(old_link.from_socket, weather_node.inputs[0])
            links.new(weather_node.outputs[0], surface_input)

            self.report({"INFO"}, "Weathering added.")
        return {"FINISHED"}


class OBJECT_OT_ReloadWeatheringNodes(bpy.types.Operator):
    bl_idname = "object.reload_weathering"
    bl_label = "Reload Weathering Nodes"

    def execute(self, context):
        # Simply tell Blender to reload linked libraries
        # This is done by calling the appropriate operator
        try:
            for library in bpy.data.libraries:
                library.reload()
            self.report({"INFO"}, "Linked libraries reloaded.")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to reload libraries: {str(e)}")
            return {"CANCELLED"}


# ====================== REGISTER ======================
classes = (
    SmartWeatheringPreferences,
    VIEW3D_PT_WeatheringPanel,
    OBJECT_OT_ToggleWeathering,
    OBJECT_OT_ReloadWeatheringNodes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
