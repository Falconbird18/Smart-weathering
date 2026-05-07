bl_info = {
    "name": "Smart Weathering",
    "author": "Austin Tallent (Falconbird18)",
    "version": (0, 3),
    "blender": (4, 0, 0),
    "location": "View3D > N-Panel > Weathering",
    "description": "Smart weathering tool with automatic library syncing.",
    "category": "Material",
}

import os
import bpy

def get_library_path():
    addon_dir = os.path.dirname(__file__)
    return os.path.join(addon_dir, "assets.blend")

def sync_node_group(group_name):
    """Appends the latest node group and replaces the old one if it exists."""
    lib_path = get_library_path()
    if not os.path.exists(lib_path):
        return None

    with bpy.data.libraries.load(lib_path, link=False) as (data_from, data_to):
        if group_name in data_from.node_groups:
            data_to.node_groups = [group_name]
        else:
            return None

    new_group = data_to.node_groups[0]
    
    # If an old version exists, swap all users to the new one and delete the old one
    for old_group in bpy.data.node_groups:
        if old_group.name.startswith(group_name) and old_group != new_group:
            old_group.user_remap(new_group)
            bpy.data.node_groups.remove(old_group)
            
    new_group.name = group_name # Keep naming clean
    return new_group

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

        btn_text = "Disable Weathering" if weather_node and not weather_node.mute else "Enable Weathering"
        icon = "HIDE_OFF" if weather_node and not weather_node.mute else "HIDE_ON"

        layout.operator("object.toggle_weathering", text=btn_text, icon=icon)

        if weather_node:
            layout.separator()
            layout.template_node_view(mat.node_tree, weather_node, None)

class OBJECT_OT_ToggleWeathering(bpy.types.Operator):
    bl_idname = "object.toggle_weathering"
    bl_label = "Toggle Weathering"
    
    def execute(self, context):
        obj = context.active_object
        mat = obj.active_material
        group_name = "Smart Weathering"
        # DOUBLE CHECK THIS NAME MATCHES YOUR ASSET FILE EXACTLY
        gn_group_name = "Get Bounding Box" 

        # 1. ENSURE GEOMETRY NODES
        gn_group = sync_node_group(gn_group_name)
        if gn_group:
            mod = obj.modifiers.get("SmartWeathering_Bounds")
            if not mod:
                mod = obj.modifiers.new(name="SmartWeathering_Bounds", type='NODES')
            
            mod.node_group = gn_group
            
            # Explicitly move to top using index override
            try:
                bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
            except:
                pass 
        else:
            print(f"DEBUG: Could not find GN Group named '{gn_group_name}'")
            self.report({"WARNING"}, f"GN Group '{gn_group_name}' not found!")

        # 2. SHADER GROUP
        shader_group = sync_node_group(group_name)
        if not shader_group:
            self.report({"ERROR"}, f"Shader group '{group_name}' not found!")
            return {"CANCELLED"}

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        weather_node = nodes.get("WeatheringNodeInstance")

        if not weather_node:
            output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None)
            if not output_node:
                return {"CANCELLED"}

            weather_node = nodes.new(type="ShaderNodeGroup")
            weather_node.name = "WeatheringNodeInstance"
            weather_node.node_tree = shader_group
            weather_node.location = (output_node.location.x - 300, output_node.location.y)

            surface_input = output_node.inputs["Surface"]
            if surface_input.is_linked:
                old_link = surface_input.links[0]
                links.new(old_link.from_socket, weather_node.inputs[0])
            
            links.new(weather_node.outputs[0], surface_input)
        
        # Always ensure the latest tree is linked and unmuted when enabling
        weather_node.node_tree = shader_group
        weather_node.mute = False 

        return {"FINISHED"}

def register():
    bpy.utils.register_class(VIEW3D_PT_WeatheringPanel)
    bpy.utils.register_class(OBJECT_OT_ToggleWeathering)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_WeatheringPanel)
    bpy.utils.unregister_class(OBJECT_OT_ToggleWeathering)

if __name__ == "__main__":
    register()