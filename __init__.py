
bl_info = {
    "name": "Layout Companion",
    "version": (1, 5, 2),
    "author": "Arciwise",
    "blender": (4, 5, 0),
    "description": "Tools for Layouters",
    "category": "Animation",
}

import bpy
from .scene_properties import *
from . import addon_updater_ops
from .operators.mesh_analyze import MESH_OT_AnalyzeMesh
from .operators.quick_render_setup import RENDER_OT_QuickSetup
from .operators.cloud_get_name_list import CLOUD_OT_GetNameList
from .operators.object_fix_materials import MESH_OT_FixMaterials
from .operators.character_apply_scale import CHARACTER_OT_ApplyScaleToSelected
from .operators.object_add_decimate import OBJECT_OT_AddDecimateModifier
from .quick_setup_panel import RENDER_PT_QuickSetupPanel
from .quick_setup_panel import RENDER_PT_UpdaterPreferences
from .characters_ui_list import CHARACTERS_UL_List
from .character_list_item import CharacterListItem

def register():
    
    addon_updater_ops.register(bl_info)
    bpy.utils.register_class(CharacterListItem)
    bpy.utils.register_class(CHARACTERS_UL_List)
    bpy.utils.register_class(RENDER_PT_QuickSetupPanel)
    bpy.utils.register_class(RENDER_PT_UpdaterPreferences)
    bpy.utils.register_class(MESH_OT_AnalyzeMesh)
    bpy.utils.register_class(RENDER_OT_QuickSetup)
    bpy.utils.register_class(CLOUD_OT_GetNameList)
    bpy.utils.register_class(MESH_OT_FixMaterials)
    bpy.utils.register_class(CHARACTER_OT_ApplyScaleToSelected)
    bpy.utils.register_class(OBJECT_OT_AddDecimateModifier)
    

    bpy.types.Scene.character_list_items = bpy.props.CollectionProperty(type=CharacterListItem)
    bpy.types.Scene.character_list_index = bpy.props.IntProperty(default=0)
    bpy.types.Scene.character_list_filter = bpy.props.StringProperty(name="Filter", default="")

def unregister():
    bpy.utils.unregister_class(CharacterListItem)
    bpy.utils.unregister_class(CHARACTERS_UL_List)
    bpy.utils.unregister_class(RENDER_PT_QuickSetupPanel)
    bpy.utils.unregister_class(RENDER_PT_UpdaterPreferences)
    bpy.utils.unregister_class(MESH_OT_AnalyzeMesh)
    bpy.utils.unregister_class(RENDER_OT_QuickSetup)
    bpy.utils.unregister_class(CLOUD_OT_GetNameList)
    bpy.utils.unregister_class(MESH_OT_FixMaterials)
    bpy.utils.unregister_class(CHARACTER_OT_ApplyScaleToSelected)
    bpy.utils.unregister_class(OBJECT_OT_AddDecimateModifier)
    del bpy.types.Scene.character_list_items
    del bpy.types.Scene.character_list_index
    del bpy.types.Scene.character_list_filter

if __name__ == "__main__":
    register()