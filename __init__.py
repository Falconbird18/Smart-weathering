bl_info = {
    "name": "Smart Weathering",
    "author": "Austin Tallent (Falconbird18)",
    "version": (0, 3),
    "blender": (5, 1, 0),
    "location": "View3D > N-Panel > Weathering",
    "description": "Smart weathering tool that is powerful and easy to use.",
    "category": "Material",
}

import os
import re

import bpy


def get_library_path():
    addon_dir = os.path.dirname(__file__)
    return os.path.join(addon_dir, "assets.blend")


def sync_node_group(group_name):
    """Syncs node group from assets.blend. Handles nested groups safely."""
    lib_path = get_library_path()
    if not os.path.exists(lib_path):
        return None

    # Return existing group if available
    existing = bpy.data.node_groups.get(group_name)
    if existing:
        return existing

    # Clean old duplicates before loading
    for grp in list(bpy.data.node_groups):
        if re.match(rf"^{re.escape(group_name)}\.\d+$", grp.name):
            bpy.data.node_groups.remove(grp)

    # Load the group (Blender will auto-pull nested groups)
    with bpy.data.libraries.load(lib_path, link=False) as (data_from, data_to):
        if group_name not in data_from.node_groups:
            return None
        data_to.node_groups = [group_name]  # ← Must be a list!

    # Blender sometimes renames things on collision, so we search carefully
    new_grp = bpy.data.node_groups.get(group_name)

    if not new_grp:
        # Fallback: look for any group that was likely the one we requested
        for grp in bpy.data.node_groups:
            if (
                grp.name == group_name
                or grp.name.startswith(group_name + ".")
                or
                # Heuristic: the main group is usually the one containing "Smart Weathering"
                (group_name == "Smart Weathering" and "Smart Weathering" in grp.name)
            ):
                new_grp = grp
                break

    if new_grp and new_grp.name != group_name:
        new_grp.name = group_name

    return new_grp


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

        group_name = "Smart Weathering"
        gn_group_name = "Get Bounding Box"

        if weather_node:
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
                    else:
                        if surface_input.is_linked:
                            links.remove(surface_input.links[0])

            nodes.remove(weather_node)
            self.report({"INFO"}, "Weathering removed.")
        else:
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
        obj = context.active_object
        mat = obj.active_material

        if not mat or not mat.use_nodes:
            self.report({"WARNING"}, "Active material requires 'Use Nodes'.")
            return {"CANCELLED"}

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        weather_node = nodes.get("WeatheringNodeInstance")

        if not weather_node:
            self.report({"INFO"}, "No weathering node found to reload.")
            return {"FINISHED"}

        group_name = "Smart Weathering"
        gn_group_name = "Get Bounding Box"

        # Re-sync the node groups (will use existing ones if present)
        gn_group = sync_node_group(gn_group_name)
        shader_group = sync_node_group(group_name)

        if not shader_group:
            self.report({"ERROR"}, "Failed to load Smart Weathering node group.")
            return {"CANCELLED"}

        # Fix: Ensure geometry nodes modifier exists and is set up
        if gn_group:
            mod = obj.modifiers.get("SmartWeathering_Bounds")
            if not mod:
                # Create the modifier if it's missing
                mod = obj.modifiers.new(name="SmartWeathering_Bounds", type="NODES")
                try:
                    bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
                except:
                    pass
            mod.node_group = gn_group
        else:
            # If we couldn't load the geometry nodes group, remove modifier if it exists
            mod = obj.modifiers.get("SmartWeathering_Bounds")
            if mod:
                obj.modifiers.remove(mod)

        # Fix: Ensure shader node is properly connected
        output_node = next(
            (n for n in nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output),
            None,
        )

        if output_node:
            surface_input = output_node.inputs.get("Surface")
            if surface_input:
                # Check if weather node is already connected to output
                is_connected = any(
                    link.from_node == weather_node for link in surface_input.links
                )

                if not is_connected:
                    # Reconnect the weather node
                    if surface_input.is_linked:
                        # Save the original input before replacing
                        old_link = surface_input.links[0]
                        links.new(old_link.from_socket, weather_node.inputs[0])
                    links.new(weather_node.outputs[0], surface_input)

        # Update the weather node group reference
        weather_node.node_tree = shader_group

        self.report({"INFO"}, "Reloaded and fixed weathering nodes.")
        return {"FINISHED"}


classes = (
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
