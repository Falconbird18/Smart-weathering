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
- **Leakage/Streaks:** Vertical procedural streaks that appear under overhangs or sharp edges.
* **Moss/Algae:** A directional mask (usually using the Normal "Z" axis) to add organic growth only on the top or shaded sides of the model.
* **Snow/Frost:** Similar to moss, but with a focus on "piling up" in the crevices and top-facing surfaces.

### 2. Physical Damage

You have scratches, but "wear and tear" often goes deeper:

* **Pitting/Dents:** Small procedural bumps that affect the **Normal** output to give the surface a hammered or aged feel.
* **Chipped Paint:** A mask that creates a "stepped" transition between the base color and a "substrate" color (like seeing the metal underneath the paint).

### 3. Surface Polish

Sometimes weathering isn't about adding "dirt," but how the surface has changed over time:

* **Sun Fading:** A checkbox to subtly desaturate and lighten the base color based on upward-facing normals.
* **Oil/Grease Stains:** Darker, lower-roughness patches that accumulate near "mechanical" areas.

### 4. Technical "Quality of Life" Features

To keep that UI clean while adding power:

* **Global Intensity Slider:** A single 0–1 slider at the top to dial back the entire weathering effect at once.
* **Seed Value:** A random seed input so the user can "shuffle" the procedural noise if the scratches or dust don't look quite right on a specific model.

---




If you have feature requests or want to help implementing any of the items above, feel free to open an issue or submit a PR.
