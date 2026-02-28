bl_info = {
    "name": "Smart Weathering",
    "author": "Austin Tallent (Falconbird18)",
    "version": (0, 9),
    "blender": (5, 0, 0),
    "location": "View3D > N-Panel > Weathering",
    "description": "Smart weathering tool that is powerful and easy to use.",
    "category": "Material",
}

import os

import bpy


def get_library_path():
    # Gets the directory where this script is installed
    addon_dir = os.path.dirname(__file__)
    # Looks for 'assets.blend' inside that same folder
    return os.path.join(addon_dir, "assets.blend")


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

        # Icon logic
        if not weather_node:
            icon_style = "HIDE_ON"
            btn_text = "Enable Weathering"
        elif weather_node.mute:
            icon_style = "HIDE_ON"
            btn_text = "Enable Weathering"
        else:
            icon_style = "HIDE_OFF"
            btn_text = "Disable Weathering"

        layout.operator("object.toggle_weathering", text=btn_text, icon=icon_style)

        if weather_node:
            layout.separator()
            layout.template_node_view(mat.node_tree, weather_node, None)


class OBJECT_OT_ToggleWeathering(bpy.types.Operator):
    bl_idname = "object.toggle_weathering"
    bl_label = "Toggle Weathering"

    def execute(self, context):
        obj = context.active_object
        mat = obj.active_material
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        group_name = "Smart Weathering"

        # Cross-platform path resolution
        lib_path = get_library_path()

        if group_name not in bpy.data.node_groups:
            if not os.path.exists(lib_path):
                self.report({"ERROR"}, f"Asset file missing: {lib_path}")
                return {"CANCELLED"}

            with bpy.data.libraries.load(lib_path) as (data_from, data_to):
                if group_name in data_from.node_groups:
                    data_to.node_groups.append(group_name)
                else:
                    self.report({"ERROR"}, f"'{group_name}' not found in assets.blend")
                    return {"CANCELLED"}

        weather_node = nodes.get("WeatheringNodeInstance")

        if not weather_node:
            output_node = next(
                (
                    n
                    for n in nodes
                    if n.type == "OUTPUT_MATERIAL" and n.is_active_output
                ),
                None,
            )
            if not output_node:
                self.report({"ERROR"}, "No Material Output found!")
                return {"CANCELLED"}

            # Correctly handle the appended group
            weather_node = nodes.new(type="ShaderNodeGroup")
            weather_node.name = "WeatheringNodeInstance"
            weather_node.node_tree = bpy.data.node_groups[group_name]
            weather_node.width = 240
            weather_node.location = (
                output_node.location.x - 300,
                output_node.location.y,
            )

            surface_input = output_node.inputs["Surface"]
            if surface_input.is_linked:
                link = surface_input.links[0]
                old_source_node = link.from_node
                old_source_socket = link.from_socket
                if old_source_node != weather_node:
                    old_source_node.location.x -= 300
                    links.new(old_source_socket, weather_node.inputs[0])

            links.new(weather_node.outputs[0], surface_input)
            weather_node.mute = False
        else:
            weather_node.mute = not weather_node.mute

        return {"FINISHED"}


def register():
    bpy.utils.register_class(VIEW3D_PT_WeatheringPanel)
    bpy.utils.register_class(OBJECT_OT_ToggleWeathering)


def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_WeatheringPanel)
    bpy.utils.unregister_class(OBJECT_OT_ToggleWeathering)


if __name__ == "__main__":
    register()
