
bl_info = {
    "name": "Layout Companion",
    "version": (1, 7, 2),
    "author": "Arciwise",
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Layout Companion",
    "description": "Tools for Layouters",
    "category": "Animation",
}

import bpy
from bpy.props import EnumProperty
import bpy.utils.previews

from . import scene_properties
from . import addon_updater_ops

from .operators import update_character
from .operators.mesh_analyze import MESH_OT_AnalyzeMesh
from .operators.quick_render_setup import RENDER_OT_QuickSetup
from .operators.cloud_character_list import CLOUD_OT_GetNameList,CharacterListItem,CHARACTERS_UL_List
from .operators.object_fix_materials import MESH_OT_FixMaterials, MESH_OT_EmissionView
from .operators.character_apply_scale import CHARACTER_OT_ApplyScaleToSelected
from .operators.update_character import UC_Operator_Updated_Character, UC_Updated_Character
from .operators.object_add_modifiers import OBJECT_OT_AddDecimateModifier, OBJECT_OT_AddSmoothByAngle
from .operators.ot_extras import OT_EXTRAS

from .ui import RENDER_PT_QuickSetupPanel,RENDER_PT_About, RENDER_PT_Resources, RENDER_PT_UpdaterPreferences



from .operators.resources_import import preview_collections, enum_previews_from_images, RESOURCE_OT_ImportSelected,RESOURCE_OT_place_origin

def register():
    addon_updater_ops.register(bl_info)
    scene_properties.register_props()
    
    bpy.utils.register_class(CharacterListItem)
    bpy.utils.register_class(CHARACTERS_UL_List)
    bpy.utils.register_class(RENDER_PT_UpdaterPreferences)
    bpy.utils.register_class(MESH_OT_AnalyzeMesh)
    bpy.utils.register_class(RENDER_OT_QuickSetup)
    bpy.utils.register_class(CLOUD_OT_GetNameList)
    bpy.utils.register_class(MESH_OT_FixMaterials)
    bpy.utils.register_class(MESH_OT_EmissionView)
    bpy.utils.register_class(CHARACTER_OT_ApplyScaleToSelected)
    bpy.utils.register_class(OBJECT_OT_AddDecimateModifier)
    bpy.utils.register_class(OBJECT_OT_AddSmoothByAngle)
    bpy.utils.register_class(OT_EXTRAS)
    
    
    from .operators.camera_composition import register
    register()
    
    bpy.utils.register_class(UC_Updated_Character) 
    
    update_character.register_props()

    pcoll = bpy.utils.previews.new()
    setattr(pcoll, "my_previews_dir", "")
    setattr(pcoll, "my_previews", [])
    preview_collections["main"] = pcoll


    bpy.types.WindowManager.collection_preview_enum = EnumProperty(
        name="Recursos",
        items=enum_previews_from_images
    )
    bpy.utils.register_class(RESOURCE_OT_ImportSelected)
    bpy.utils.register_class(RESOURCE_OT_place_origin)
    
    
    bpy.utils.register_class(UC_Operator_Updated_Character)
    bpy.utils.register_class(RENDER_PT_QuickSetupPanel)
    bpy.utils.register_class(RENDER_PT_Resources)
    bpy.utils.register_class(RENDER_PT_About)
    bpy.types.Scene.character_list_items = bpy.props.CollectionProperty(type=CharacterListItem)
    bpy.types.Scene.character_list_index = bpy.props.IntProperty(default=0)
    bpy.types.Scene.character_list_filter = bpy.props.StringProperty(name="Filter", default="")

def unregister():
    addon_updater_ops.unregister()
    
    scene_properties.unregister_props()
    bpy.utils.unregister_class(CharacterListItem)
    bpy.utils.unregister_class(CHARACTERS_UL_List)
    bpy.utils.unregister_class(RENDER_PT_QuickSetupPanel)
    bpy.utils.unregister_class(RENDER_PT_Resources)
    bpy.utils.unregister_class(RENDER_PT_About)
    bpy.utils.unregister_class(RENDER_PT_UpdaterPreferences)
    bpy.utils.unregister_class(MESH_OT_AnalyzeMesh)
    bpy.utils.unregister_class(RENDER_OT_QuickSetup)
    bpy.utils.unregister_class(CLOUD_OT_GetNameList)
    bpy.utils.unregister_class(MESH_OT_FixMaterials)
    bpy.utils.unregister_class(MESH_OT_EmissionView)
    bpy.utils.unregister_class(CHARACTER_OT_ApplyScaleToSelected)
    bpy.utils.unregister_class(OBJECT_OT_AddDecimateModifier)
    bpy.utils.unregister_class(OBJECT_OT_AddSmoothByAngle)
    bpy.utils.unregister_class(OT_EXTRAS)
    
    
    from .operators.camera_composition import unregister
    unregister()

    bpy.utils.unregister_class(RESOURCE_OT_ImportSelected)
    bpy.utils.unregister_class(RESOURCE_OT_place_origin)
    
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    
    del bpy.types.WindowManager.collection_preview_enum

    
    update_character.unregister_props()
    
    bpy.utils.unregister_class(UC_Updated_Character)
    bpy.utils.unregister_class(UC_Operator_Updated_Character)
    
    del bpy.types.Scene.character_list_items
    del bpy.types.Scene.character_list_index
    del bpy.types.Scene.character_list_filter