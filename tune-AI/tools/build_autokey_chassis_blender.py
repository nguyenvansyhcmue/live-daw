"""Render the clean THM Vocal Panel controller chassis in Blender.

Run with Blender, not CPython:
  Blender --background --python tools/build_autokey_chassis_blender.py

The render contains structure and materials only. Runtime text, meters,
waveforms, EQ nodes, buttons and knobs stay native Qt controls.
"""
from pathlib import Path
import math
import sys

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.autokey_visual_tokens import (CHASSIS_SCREWS, EQ_CONTROL_POCKET,
                                      EQ_GRAPH, EQ_SECTION, HEADER,
                                      KEY_DISPLAY, MACRO_CENTERS, MACRO_GROOVES,
                                      MAPPING, MODE_RAIL, OUTPUT_METER,
                                      OUTPUT_MODULE, TONE_SHIFT)

OUTPUT = ROOT / "assets" / "autokey_atomic" / "autokey_chassis_blender_clean@2x.png"
W, H = 2816, 2000
PW = 100.0  # reference pixels per Blender world unit


def material(name, base, metallic=0.0, roughness=0.45, noise=0.0,
             texture_scale=220.0, bump_strength=0.0, anisotropy=0.0):
    """Create a restrained PBR material suited to close product rendering.

    Colour variation alone reads as a flat bitmap.  The shared noise field also
    drives microscopic normal variation so powder coat and machined metal react
    to the same neutral softboxes as real hardware.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*base, 1.0)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    anisotropic = shader.inputs.get("Anisotropic IOR Level")
    if anisotropic is not None:
        anisotropic.default_value = anisotropy
    texture = None
    if noise or bump_strength:
        texture = nodes.new("ShaderNodeTexNoise")
        texture.inputs["Scale"].default_value = texture_scale
        texture.inputs["Detail"].default_value = 3.2
        texture.inputs["Roughness"].default_value = 0.72
    if noise and texture is not None:
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.30
        ramp.color_ramp.elements[0].color = (*tuple(max(0, c - noise) for c in base), 1)
        ramp.color_ramp.elements[1].position = 0.70
        ramp.color_ramp.elements[1].color = (*tuple(min(1, c + noise) for c in base), 1)
        links.new(texture.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    if bump_strength and texture is not None:
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = .035
        links.new(texture.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return mat


BLACK = material("Midnight teal anodised", (.012, .035, .041), .58, .36, .010,
                 310, .10, .28)
BLACK_SOFT = material("Deep ocean ceramic", (.028, .075, .082), .16, .42, .010,
                      420, .24, .04)
IVORY = material("Smoked bronze structural plate", (.16, .17, .16), .54, .34, .010,
                 360, .14, .10)
# The approved reference uses a light painted/enamel control surface, not bare
# metal. A metallic shader reflected the nearly black studio world and turned
# the intended ivory into gunmetal. Keep this deliberately dielectric so its
# warm neutral colour survives the product-lighting environment.
IVORY_LIGHT = material("Warm gunmetal instrument enamel", (.27, .28, .26), .34, .32, .006,
                       520, .035, .04)
GLASS = material("Deep teal optical glass", (.002, .027, .034), .16, .15, .003,
                 180, .018, .02)
BRASS = material("Champagne titanium trim", (.41, .35, .25), .88, .22, .005,
                 360, .035, .55)
STEEL = material("Machined smoke steel", (.34, .36, .35), .94, .18, .006,
                 460, .045, .72)
SATIN = material("Bead blasted bronze titanium", (.34, .33, .29), .78, .25, .006,
                 680, .055, .64)
RECESS = material("Deep teal routed shadow", (.003, .018, .022), .34, .38, .008,
                  520, .12, .05)


def xywh(rect):
    x, y, w, h = rect
    return ((x + w / 2) / PW - 7.04, 5.0 - (y + h / 2) / PW,
            w / PW, h / PW)


def rounded_box(name, rect, depth, z, mat, bevel_px=8):
    cx, cy, sx, sy = xywh(rect)
    bpy.ops.mesh.primitive_cube_add(location=(cx, cy, z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (sx / 2, sy / 2, depth / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Machined radius", "BEVEL")
    bevel.width = bevel_px / PW
    bevel.segments = 5
    bevel.limit_method = "ANGLE"
    obj.data.materials.append(mat)
    return obj


def chamfered_plate(name, rect, clip_px, depth, z, mat, bevel_px=3):
    """Create a restrained eight-corner faceplate in reference-pixel space."""
    x, y, w, h = rect
    points = ((x + clip_px, y), (x + w - clip_px, y), (x + w, y + clip_px),
              (x + w, y + h - clip_px), (x + w - clip_px, y + h),
              (x + clip_px, y + h), (x, y + h - clip_px), (x, y + clip_px))
    top = [(px / PW - 7.04, 5.0 - py / PW, z + depth / 2) for px, py in points]
    bottom = [(px / PW - 7.04, 5.0 - py / PW, z - depth / 2) for px, py in points]
    vertices = top + bottom
    faces = [tuple(range(8)), tuple(range(15, 7, -1))]
    for index in range(8):
        nxt = (index + 1) % 8
        faces.append((index, nxt, nxt + 8, index + 8))
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new("Machined edge", "BEVEL")
    bevel.width = bevel_px / PW
    bevel.segments = 3
    return obj


def screw(name, px, py, diameter=12):
    x, y, _, _ = xywh((px - diameter / 2, py - diameter / 2, diameter, diameter))
    # The fastener is countersunk into the main chassis whose top is z=.25.
    # Earlier revisions floated it near z=.50 and over-bevelled its shallow
    # head, which produced a soft black spot instead of precise hardware.
    bpy.ops.mesh.primitive_torus_add(
        major_radius=diameter / PW * .46, minor_radius=diameter / PW * .075,
        major_segments=64, minor_segments=12, location=(x, y, .256))
    washer = bpy.context.object
    washer.name = name + " washer"
    washer.data.materials.append(BLACK)

    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=diameter / PW / 2,
                                        depth=.018, location=(x, y, .265))
    head = bpy.context.object
    head.name = name
    head.data.materials.append(STEEL)
    bevel = head.modifiers.new("Countersunk rim", "BEVEL")
    bevel.width = .007
    bevel.segments = 4

    # Actual six-sided drive cavity with a lower socket floor.  The two nested
    # pieces provide a readable countersunk hex at 2x and normal UI scale.
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=6, radius=diameter / PW * .205, depth=.008,
        location=(x, y, .276),
        rotation=(0, 0, math.radians(18 if px < 704 else -18)))
    socket = bpy.context.object
    socket.name = name + " recessed hex drive"
    socket.data.materials.append(BLACK)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=6, radius=diameter / PW * .115, depth=.006,
        location=(x, y, .279),
        rotation=(0, 0, math.radians(18 if px < 704 else -18)))
    socket_floor = bpy.context.object
    socket_floor.name = name + " hex socket floor"
    socket_floor.data.materials.append(BLACK_SOFT)
    return head


def control_socket(name, px, py, diameter, accent=False):
    """Build a real three-part mounting socket for a live Qt control.

    The runtime control is intentionally not baked into the chassis.  A dark
    routed pocket, satin collar and tiny contact-shadow ring make it look like
    a component installed through the faceplate at any DPI.
    """
    x, y, _, _ = xywh((px - diameter / 2, py - diameter / 2,
                        diameter, diameter))
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=96, radius=diameter / PW * .53, depth=.020,
        location=(x, y, .365))
    pocket = bpy.context.object
    pocket.name = name + " routed pocket"
    pocket.data.materials.append(RECESS)
    pocket_bevel = pocket.modifiers.new("Routed pocket bevel", "BEVEL")
    pocket_bevel.width = .032
    pocket_bevel.segments = 5

    bpy.ops.mesh.primitive_torus_add(
        major_radius=diameter / PW * .47,
        minor_radius=diameter / PW * .026,
        major_segments=96, minor_segments=12,
        location=(x, y, .405))
    collar = bpy.context.object
    collar.name = name + " machined collar"
    collar.data.materials.append(SATIN if not accent else STEEL)

    bpy.ops.mesh.primitive_torus_add(
        major_radius=diameter / PW * .405,
        minor_radius=diameter / PW * .012,
        major_segments=96, minor_segments=8,
        location=(x, y, .414))
    contact = bpy.context.object
    contact.name = name + " contact shadow"
    contact.data.materials.append(BLACK)
    return pocket


def _apply_boolean_cut(target, cutter, modifier_name):
    """Apply one deterministic exact boolean and discard its cutter."""
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    cutter.select_set(False)
    modifier = target.modifiers.new(modifier_name, "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def _groove_cutter(name, rect, z=.365, depth=.060, rotation=0.0):
    cx, cy, sx, sy = xywh(rect)
    bpy.ops.mesh.primitive_cube_add(location=(cx, cy, z),
                                    rotation=(0, 0, rotation))
    cutter = bpy.context.object
    cutter.name = name
    cutter.scale = (sx / 2, sy / 2, depth / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = cutter.modifiers.new("Cutter radius", "BEVEL")
    bevel.width = 1.4 / PW
    bevel.segments = 3
    bpy.context.view_layer.objects.active = cutter
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return cutter


def cnc_separator(target, name, px):
    """Machine one restrained router seam into ``target`` itself.

    The earlier separator was dark geometry sitting above the faceplate.  This
    version subtracts a physical cutter volume from the macro deck.  The cut
    keeps the deck's own material on its walls and floor, so product lighting
    alone describes the recess instead of a black decal or inserted ornament.
    """
    seam = (px - 1.45, 792, 2.9, 160)
    cutter = _groove_cutter(f"{name} router cutter", seam,
                             z=.371, depth=.052)
    _apply_boolean_cut(target, cutter, f"{name} router boolean")


def build_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # New architecture: slim command rail, wide detector, compact stacked
    # utility controls, analyzer work area and a dedicated macro matrix.
    rounded_box("Outer enclosure", (5, 8, 1398, 984), .16, .08, BLACK, 18)
    rounded_box("Main chassis", (13, 16, 1382, 968), .18, .16, IVORY_LIGHT, 15)
    rounded_box("Command rail", HEADER.tuple(), .15, .34, BLACK_SOFT, 10)
    # A single quiet substrate establishes the middle assembly's ownership.
    # Its child modules are inset on every side; no duplicate chamfer, gasket
    # or centre spine is allowed to cross another module edge.
    rounded_box("Integrated mid deck substrate", (24, 112, 1360, 620),
                .12, .225, IVORY_LIGHT, 12)

    # New architecture: an analysis wing and a self-contained Vocal Core tower.
    # There is no full-width hero strip or shared horizontal mode rail.
    chamfered_plate("Vocal Core tower", (910, 125, 464, 590), 20,
                    .18, .28, IVORY, 8)
    chamfered_plate("Tone shift instrument", TONE_SHIFT.tuple(), 22,
                    .12, .36, SATIN, 12)
    # A shallow engraved title lane sits above the glass; the live title,
    # number and scale therefore never occupy the same physical layer.
    rounded_box("Tone shift title lane", (1007, 409, 272, 21), .025, .382, RECESS, 6)
    rounded_box("Tone shift readout", (1005, 434, 276, 74), .065, .42, GLASS, 10)

    # The detector is a serviceable glass instrument installed through two
    # nested frames, not a black rectangle printed on the panel.
    # Keep the bezel an even 6 px around the glass, then leave a deliberate
    # 10 px chassis reveal before the output meter.  This reads as two fitted
    # hardware modules instead of one frame colliding with the next.
    rounded_box("Detector routed aperture", (925, 125, 320, 275), .08, .345, RECESS, 16)
    rounded_box("Detector satin retaining frame", (929, 129, 312, 267), .12, .37, BRASS, 15)
    rounded_box("Detector glass", KEY_DISPLAY.tuple(), .08, .44, GLASS, 9)
    chamfered_plate("Output monitor instrument", OUTPUT_MODULE.tuple(), 22,
                    .12, .36, SATIN, 12)
    rounded_box("Output status header", (1262, 140, 96, 38), .035, .385, BLACK_SOFT, 7)
    rounded_box("Output meter retaining frame", (1267, 180, 86, 173), .055, .405, SATIN, 8)
    rounded_box("Output meter recess", OUTPUT_METER.tuple(), .07, .43, BLACK, 5)
    rounded_box("Output value footer", (1262, 350, 96, 31), .035, .385, BLACK_SOFT, 7)

    # Tone step switches get the same installed-component treatment as the
    # macro encoders; their live faces are still painted by Qt.
    control_socket("Tone down switch", 968, 471, 52, True)
    control_socket("Tone up switch", 1317, 471, 52, True)

    rounded_box("Mode routed aperture", (916, 531, 453, 188), .055, .315, RECESS, 14)
    rounded_box("Mode control tray", MODE_RAIL.tuple(), .12, .36, BLACK, 14)

    # The analyzer is now the entire left wing, vertically independent from
    # the Vocal Core tower rather than another full-width horizontal tier.
    chamfered_plate("Analyzer bridge", (34, 125, 852, 590), 20,
                    .16, .27, BLACK_SOFT, 8)
    rounded_box("Analyzer routed aperture", (65, 175, 790, 480), .07, .32, RECESS, 11)
    rounded_box("Analyzer outer bezel", (69, 179, 782, 472), .12, .36, BLACK, 10)
    rounded_box("Analyzer machined lip", (73, 183, 774, 464), .09, .40, BRASS, 8)
    rounded_box("Analyzer glass", EQ_GRAPH.tuple(), .08, .44, GLASS, 7)
    rounded_box("Analyzer toolbar", EQ_CONTROL_POCKET.tuple(), .07, .38, BLACK_SOFT, 7)

    rounded_box("Lower control backbone", (24, 750, 1360, 226),
                .12, .225, IVORY, 11)
    macro_deck = chamfered_plate("Macro control deck", (34, 770, 1340, 195), 16,
                                 .16, .28, IVORY_LIGHT, 8)
    # Freeze the deck's broad outer edge before cutting its fine internal
    # details; this keeps Boolean modifier order stable across Blender builds.
    bpy.context.view_layer.objects.active = macro_deck
    macro_deck.select_set(True)
    for modifier in tuple(macro_deck.modifiers):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    for index, (cx, cy) in enumerate(MACRO_CENTERS, 1):
        # No per-control card: the original approved knob is installed
        # directly through the continuous macro deck.
        control_socket(f"Macro {index}", cx, cy, 112, accent=index in (2, 5))

    for index, groove_x in enumerate(MACRO_GROOVES, 1):
        cnc_separator(macro_deck, f"Macro CNC separator {index}", groove_x)

    # One restrained radius catches light along every newly cut edge.  It is
    # deliberately sub-pixel at reference scale and never becomes a border.
    groove_bevel = macro_deck.modifiers.new("CNC cut edge radius", "BEVEL")
    groove_bevel.width = .006
    groove_bevel.segments = 2
    groove_bevel.limit_method = "ANGLE"

    rounded_box("Mapping routed aperture",
                (MAPPING.x - 7, MAPPING.y - 7, MAPPING.width + 14, MAPPING.height + 14),
                .055, .33, RECESS, 11)
    rounded_box("Mapping switch mount", MAPPING.tuple(), .08, .39, BLACK, 8)

    # Four genuinely small fasteners live in dedicated corner clearances on
    # the outer enclosure.  They never sit on a module seam or chamfer.
    for index, (x, y, _rotation) in enumerate(CHASSIS_SCREWS):
        screw(f"Rail fastener {index + 1}", x, y, 8)

    # Camera and product-lighting rig: neutral, broad and deliberately quiet.
    # Colour belongs to live UI state, never to the static chassis illumination.
    bpy.ops.object.camera_add(location=(0, 0, 18))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    # Blender's orthographic scale is the horizontal span for this landscape
    # camera.  14.08 world units maps exactly to the 1408 px design width;
    # the 2816:2000 render aspect then yields the required 10.00-unit height.
    camera.data.ortho_scale = 14.08
    camera.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = camera

    def area(name, location, energy, size, colour):
        bpy.ops.object.light_add(type="AREA", location=location)
        lamp = bpy.context.object
        lamp.name = name
        lamp.data.energy = energy
        lamp.data.shape = "RECTANGLE"
        lamp.data.size = size
        lamp.data.color = colour
        return lamp

    # Oversized white sources reveal bevels without hotspots, bloom or coloured
    # reflections.  Their low contrast matches real product photography.
    area("Upper softbox", (-4.8, 6.5, 13), 850, 13.0, (.97, .95, .90))
    area("Side fill", (7.5, 2.5, 14), 340, 14.0, (.82, .90, .90))
    area("Lower fill", (0, -7.0, 11), 160, 12.0, (.92, .82, .69))
    area("Front ambient", (0, 0, 20), 480, 17.0, (.96, .94, .89))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(OUTPUT)
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    # Bright neutral product lighting now establishes the tonal separation;
    # exposure stays conservative so the warm faceplate does not clip.
    scene.view_settings.exposure = -.05
    scene.world.color = (.003, .006, .006)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT.with_suffix(".blend")))
    bpy.ops.render.render(write_still=True)
    print(f"Rendered clean chassis: {OUTPUT}")


build_scene()
