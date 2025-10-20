bl_info = {
    "name": "Layout Companion",
    "version": (1, 9, 2),
    "author": "Arciwise",
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Layout Companion",
    "description": "Tools for Layouters",
    "category": "Animation",
}

import bpy
import os
import sys
from . import scene_properties
from . import addon_updater_ops
from . import ui

addon_dir = os.path.dirname(__file__)
libs_dir = os.path.join(addon_dir, "libs")

if libs_dir not in sys.path:
    sys.path.append(libs_dir)

from .operators.mesh_analyze import MESH_OT_AnalyzeMesh
from .operators.quick_render_setup import RENDER_OT_QuickSetup
from .operators.object_fix_materials import MESH_OT_FixMaterials, MESH_OT_EmissionView
from .operators.object_add_modifiers import OBJECT_OT_AddDecimateModifier, OBJECT_OT_AddSmoothByAngle
from .operators.ot_extras import register_extras,unregister_extras
from .operators.character_updater import register_update_character, unregister_update_character
from .operators.github_scales import register_character_list, unregister_character_list
from .operators.resources_import import register_resource_import, unregister_resource_import
from .drive.drive_collaborator import register_drive_collaboration, unregister_drive_collaboration
from .drive.drive_importer import register_drive, unregister_drive
from .drive.horns_resources import register_horns_resources, unregister_horns_resources
from .operators.camera_composition import register as register_camera, unregister as unregister_camera


custom_icons = None

def register_icons():
    import bpy.utils.previews
    global custom_icons
    custom_icons = bpy.utils.previews.new()

    icons_dir = os.path.join(addon_dir, "visuals")
    custom_icons.load("LC", os.path.join(icons_dir, "LC.png"), 'IMAGE')
    custom_icons.load("note", os.path.join(icons_dir, "note_icon.png"), 'IMAGE')
    custom_icons.load("draw", os.path.join(icons_dir, "draw_icon.png"), 'IMAGE')
    custom_icons.load("setup_layout", os.path.join(icons_dir, "setupLayout_icon.png"), 'IMAGE')
    custom_icons.load("alert", os.path.join(icons_dir, "alert_icon.png"), 'IMAGE')
    custom_icons.load("trends", os.path.join(icons_dir, "get_trends_icon.png"), 'IMAGE')
    custom_icons.load("youtube", os.path.join(icons_dir, "youtube_tutorial.png"), 'IMAGE')
    custom_icons.load("search", os.path.join(icons_dir, "search_icon.png"), 'IMAGE')
    custom_icons.load("compressed", os.path.join(icons_dir, "compressed.png"), 'IMAGE')
    bpy.types.WindowManager.custom_icons = custom_icons


def unregister_icons():
    global custom_icons
    if custom_icons:
        bpy.utils.previews.remove(custom_icons)
        del bpy.types.WindowManager.custom_icons
        custom_icons = None


def register():
    addon_updater_ops.register(bl_info)
    scene_properties.register_props()
    register_character_list()

    for cls in (
        MESH_OT_AnalyzeMesh,
        RENDER_OT_QuickSetup,
        MESH_OT_FixMaterials,
        MESH_OT_EmissionView,
        OBJECT_OT_AddDecimateModifier,
        OBJECT_OT_AddSmoothByAngle,
    ):
        bpy.utils.register_class(cls) 

    register_extras()
    register_resource_import()
    register_drive()
    register_update_character()
    register_drive_collaboration()
    register_horns_resources()
    register_camera()
    register_icons()
    ui.register_ui()

def unregister():
    addon_updater_ops.unregister()
    scene_properties.unregister_props()
    unregister_character_list()
    ui.unregister_ui()

    for cls in reversed((
        MESH_OT_AnalyzeMesh,
        RENDER_OT_QuickSetup,
        MESH_OT_FixMaterials,
        MESH_OT_EmissionView,
        OBJECT_OT_AddDecimateModifier,
        OBJECT_OT_AddSmoothByAngle,
    )):
        bpy.utils.unregister_class(cls)
        
    unregister_extras()
    unregister_resource_import()
    unregister_drive()
    unregister_drive_collaboration()
    unregister_update_character()
    unregister_horns_resources()
    unregister_camera()
    unregister_icons()
    
