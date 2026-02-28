# Smart Weathering

Smart Weathering is an addon for Blender that provides an easy-to-use node group for realistic weathering effects on materials.

## Features

- Toggle weathering on/off 
- Minimal UI in the 3D View N-panel under the "Weathering" tab for quick access.
- Edge wear, Ambient Occlusion, Scratches, Fingerprints, and dust (more to come).

## Requirements

- Blender 5.0 or newer.
- Target object must be a Mesh with an active material. The material must use nodes for the node group insertion to work correctly.


## Installation

1. Download the zip file
2. In Blender: Edit → Preferences → Add-ons → Install...
3. Select the .zip you created, enable the add-on, then use the "Weathering" panel in the 3D View N-panel.

## Usage

1. In the 3D View, open the right-hand N-panel and select the `Weathering` tab.
2. Select a Mesh object with an active material.
3. If the material does not use nodes, convert it to node-based by enabling "Use Nodes" on the material.
4. Click the button ("Enable Weathering") 
5. The add-on creates a group node and connects it to the active material output's Surface socket. If you enabled weathering previously and the node is present but muted, clicking the button will un-mute it.
6. To disable weathering, click the button again (it toggles the node group's mute state).

## Roadmap

Planned improvements and possible future features:

- Support batch-apply weathering to multiple selected objects.
- Provide presets (light, medium, heavy weathering) and the ability to save/load custom presets.
- Add thumbnail preview and inline documentation for node group inputs.
- Physical Damage, such as dents, and bumps using normals.
- Surface imperfections like sun fading and oil stains and leakage/streaks.

If you have feature requests or want to help implementing any of the items above, feel free to open an issue or submit a PR.
