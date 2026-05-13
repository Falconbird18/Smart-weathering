bl_info = {
    "name": "Smart Weathering",
    "author": "Austin Tallent (Falconbird18)",
    "version": (0, 4),
    "blender": (5, 1, 0),
    "location": "View3D > N-Panel > Weathering",
    "description": "Smart weathering tool that is powerful and easy to use.",
    "category": "Material",
}

import os
import re

import bpy


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


# ====================== SYNC FUNCTION ======================
def sync_node_group(group_name):
    """Syncs node group from assets.blend. Handles nested groups safely."""
    lib_path = get_library_path()
    if not os.path.exists(lib_path):
        print(f"Warning: Assets file not found at {lib_path}")
        return None

    # Return existing group if available
    existing = bpy.data.node_groups.get(group_name)
    if existing:
        return existing

    # Clean old duplicates before loading
    for grp in list(bpy.data.node_groups):
        if re.match(rf"^{re.escape(group_name)}\.\d+$", grp.name):
            bpy.data.node_groups.remove(grp)

    # Load the group
    with bpy.data.libraries.load(lib_path, link=False) as (data_from, data_to):
        if group_name not in data_from.node_groups:
            print(f"Warning: Node group '{group_name}' not found in {lib_path}")
            return None
        data_to.node_groups = [group_name]

    # Find the correct group after loading
    new_grp = bpy.data.node_groups.get(group_name)

    if not new_grp:
        # Fallback search
        for grp in bpy.data.node_groups:
            if grp.name == group_name or grp.name.startswith(group_name + "."):
                new_grp = grp
                break

    if new_grp and new_grp.name != group_name:
        new_grp.name = group_name

    return new_grp


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
        # ... [Your existing toggle code - unchanged] ...
        obj = context.active_object
        mat = obj.active_material
        if not mat or not mat.use_nodes:
            self.report({"WARNING"}, "Active material requires 'Use Nodes'.")
            return {"CANCELLED"}

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        weather_node = nodes.get("WeatheringNodeInstance")

        group_name = "Smart Weathering"
        gn_group_name = "Get Bounding Box"

        if weather_node:
            # Remove logic (unchanged)
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
                    if weather_node.inputs[0].is_linked:
                        source_socket = weather_node.inputs[0].links[0].from_socket
                        links.new(source_socket, surface_input)
                    elif surface_input.is_linked:
                        links.remove(surface_input.links[0])
            nodes.remove(weather_node)
            self.report({"INFO"}, "Weathering removed.")
        else:
            # Add logic
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

            gn_group = sync_node_group(gn_group_name)
            if gn_group:
                mod = obj.modifiers.get("SmartWeathering_Bounds") or obj.modifiers.new(
                    name="SmartWeathering_Bounds", type="NODES"
                )
                mod.node_group = gn_group
                try:
                    bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
                except:
                    pass

            shader_group = sync_node_group(group_name)
            if not shader_group:
                self.report({"ERROR"}, "Failed to load 'Smart Weathering' node group.")
                return {"CANCELLED"}

            weather_node = nodes.new(type="ShaderNodeGroup")
            weather_node.name = "WeatheringNodeInstance"
            weather_node.node_tree = shader_group
            weather_node.location = (
                output_node.location.x - 300,
                output_node.location.y,
            )

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
        # ... [Your existing reload code - unchanged except for the cleanup part] ...
        obj = context.active_object
        mat = obj.active_material
        if not mat or not mat.use_nodes:
            self.report({"WARNING"}, "Active material requires 'Use Nodes'.")
            return {"CANCELLED"}

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        weather_node = nodes.get("WeatheringNodeInstance")

        if not weather_node:
            self.report({"INFO"}, "No weathering node found.")
            return {"FINISHED"}

        group_name = "Smart Weathering"
        gn_group_name = "Get Bounding Box"

        # Optional: Extra cleanup for misnamed groups
        for name in (group_name, gn_group_name):
            for grp in list(bpy.data.node_groups):
                if grp.name.startswith(name + ".") and grp.users == 0:
                    bpy.data.node_groups.remove(grp)

        gn_group = sync_node_group(gn_group_name)
        shader_group = sync_node_group(group_name)

        if not shader_group:
            self.report({"ERROR"}, "Failed to load Smart Weathering node group.")
            return {"CANCELLED"}

        # Update geometry nodes modifier
        if gn_group:
            mod = obj.modifiers.get("SmartWeathering_Bounds")
            if not mod:
                mod = obj.modifiers.new(name="SmartWeathering_Bounds", type="NODES")
                try:
                    bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
                except:
                    pass
            mod.node_group = gn_group

        # Update shader node
        if weather_node:
            weather_node.node_tree = shader_group

        self.report({"INFO"}, "Weathering nodes reloaded successfully.")
        return {"FINISHED"}


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
