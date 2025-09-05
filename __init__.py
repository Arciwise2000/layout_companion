bl_info = {
    "name": "Layout Companion",
    "version": (1, 8, 70),
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
from bpy.app.handlers import persistent

addon_dir = os.path.dirname(__file__)
lib_dir = os.path.join(addon_dir, "dropbox", "lib")

if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

from .operators.mesh_analyze import MESH_OT_AnalyzeMesh
from .operators.quick_render_setup import RENDER_OT_QuickSetup
from .operators.character_apply_scale import CHARACTER_OT_ApplyScaleToSelected
from .operators.object_fix_materials import MESH_OT_FixMaterials, MESH_OT_EmissionView
from .operators.object_add_modifiers import OBJECT_OT_AddDecimateModifier, OBJECT_OT_AddSmoothByAngle
from .operators.ot_extras import register_extras,unregister_extras
from .operators.update_character import register_update_character, unregister_update_character
from .operators.cloud_character_list import register_character_list, unregister_character_list
from .operators.resources_import import register_resource_import, unregister_resource_import
from .dropbox.dropbox_collaborator import register_dropbox_collaboration, unregister_dropbox_collaboration
from .dropbox.dropbox_oauth import register_dropbox, unregister_dropbox, register_dropbox_previews,load_previews_from_cache
from .operators.camera_composition import register as register_camera, unregister as unregister_camera

@persistent
def on_blend_loaded(dummy):
    """Handler que carga los previews desde caché al abrir un .blend."""
    def delayed_load():
        try:
            cached_previews = load_previews_from_cache()
            if cached_previews:
                register_dropbox_previews(cached_previews)
        except Exception as e:
            print(f"[Dropbox] Error al cargar previews: {e}")
        return None

    bpy.app.timers.register(delayed_load, first_interval=1)

def register():
    addon_updater_ops.register(bl_info)
    scene_properties.register_props()
    register_character_list()

    for cls in (
        MESH_OT_AnalyzeMesh,
        RENDER_OT_QuickSetup,
        MESH_OT_FixMaterials,
        MESH_OT_EmissionView,
        CHARACTER_OT_ApplyScaleToSelected,
        OBJECT_OT_AddDecimateModifier,
        OBJECT_OT_AddSmoothByAngle,
    ):
        bpy.utils.register_class(cls) 

    register_extras()
    register_resource_import()
    register_dropbox()
    register_update_character()
    register_dropbox_collaboration()
    register_camera()
    ui.register_ui()
    
    if on_blend_loaded not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(on_blend_loaded)


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
        CHARACTER_OT_ApplyScaleToSelected,
        OBJECT_OT_AddDecimateModifier,
        OBJECT_OT_AddSmoothByAngle,
    )):
        bpy.utils.unregister_class(cls)
        
    unregister_extras()
    unregister_resource_import()
    unregister_dropbox()
    unregister_dropbox_collaboration()
    unregister_update_character()
    unregister_camera()
     
    if on_blend_loaded in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_blend_loaded)
