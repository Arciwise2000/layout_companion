import bpy
from . import addon_updater_ops
from .LC_utils import is_any_object_visible_in_render, is_collection_exist, get_icon_by_vertices, file_exists_in_blend_directory

class RENDER_PT_QuickSetupPanel(bpy.types.Panel):
    bl_label = "Layout Companion!"
    bl_idname = "RENDER_PT_quick_setup_npanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tools"
    
    def draw_header(self, context):
            layout = self.layout
            layout.label(text="",icon = "FUND")
            
    def draw(self, context):
        layout = self.layout
        scene = context.scene
     
        # Render Settings
        col = layout.column()
        row = col.row()
        row.prop(scene, "render_settings_fold", 
                icon='TRIA_DOWN' if scene.render_settings_fold else 'TRIA_RIGHT',
                icon_only=True, 
                emboss=False)
        row.label(text="LAYOUT STATUS", icon="BLENDER")
        
        if scene.render_settings_fold:
            box = col.box()
            row = box.row()
            row.operator("render.quick_setup", text="Setup layout", icon='SETTINGS')
            row.prop(scene, "show_render_status", toggle=True,icon= "HIDE_OFF" if scene.show_render_status else "HIDE_ON")
           
            if scene.show_render_status:
                
                icon = 'STRIP_COLOR_01' if not bpy.app.version >= (4, 5, 0) else 'STRIP_COLOR_04'
                box.label(text="Blender version", icon=icon)
                #------------------
                scene_count = len(bpy.data.scenes)
                icon = 'STRIP_COLOR_01' if scene_count > 1 else 'STRIP_COLOR_04'
                box.label(text="Only one scene", icon=icon)
                #------------------
                cameraCollectionAvaible = is_collection_exist("CAMERA")
                dofText = "DOF in camera collection"
                if not cameraCollectionAvaible:
                    box.label(text="'CAMERA' Collection in Scene", icon="STRIP_COLOR_01")
                elif cameraCollectionAvaible.objects.get("DOF"):
                    box.label(text= dofText, icon="STRIP_COLOR_04")
                else:
                    box.label(text= dofText, icon="STRIP_COLOR_01")
                #------------------
                collection_name = "NOTAS_LAYOUT"
                isVisibleOnRender = is_any_object_visible_in_render(collection_name)
                iconRender = 'STRIP_COLOR_04' if not isVisibleOnRender else 'STRIP_COLOR_01'
                box.label(text="Visible layout notes", icon=iconRender)
                
                hasRenderNotes = file_exists_in_blend_directory("NOTAS RENDER.txt")
                iconLayoutNote = 'STRIP_COLOR_09' if not hasRenderNotes else 'STRIP_COLOR_04'
                box.label(text="Render notes", icon=iconLayoutNote)
                layout.separator(factor=2)
        
        layout.separator(factor=1)
            
        # Props Settings
        col = layout.column()
        row = col.row()
        row.prop(scene, "props_settings_fold", 
                icon='TRIA_DOWN' if scene.props_settings_fold else 'TRIA_RIGHT',
                icon_only=True, 
                emboss=False)
        row.label(text="PROPS SETTINGS", icon='MESH_DATA')
       
        if scene.props_settings_fold:
            box = col.box()
            box.prop(scene, "show_advance_prop_settings", toggle=True,icon= "HIDE_OFF" if scene.show_advance_prop_settings else "HIDE_ON")
            
            if scene.show_advance_prop_settings:
                box.prop(scene, "remove_doubles", text="Remove Double Vertices")
                box.prop(scene, "remove_empties", text="Remove Emptys")
                box.prop(scene, "add_in_collection", text="Create Collection")
                box.prop(scene, "mergeObjects", text="Merge Meshes")
                box.separator(factor=0.5)

            if not context.active_object:
                box.label(text="Ningún objeto seleccionado", icon='ERROR')
            elif context.active_object.type != 'MESH':
                box.label(text="El objeto no es una malla", icon='ERROR')
            else:
                mesh = context.active_object.data
                row = box.row()
                currentIcon, currentInfo = get_icon_by_vertices(len(mesh.vertices))
                row.prop(scene,"show_prop_helpInfo", text="", icon=currentIcon)
                if scene.show_prop_helpInfo:
                    info_row = box.row()
                    info_row.alignment = 'CENTER'
                    info_row.label(text=currentInfo)
                    
                row.label(text=f"Vertices: {len(mesh.vertices)}", icon='DOT')
                row.label(text=f"Faces: {len(mesh.polygons)}", icon='MESH_CUBE')
            box.operator("mesh.analyze_mesh", text="Clean Prop", icon='TRASH')
            box.operator("mesh.fix_materials", text="Fix Materials", icon='MATERIAL')
            box.separator()
            box.operator("object.add_decimate_modifier", text="Add Decimate",icon="MOD_DECIM")

        layout.separator(factor=1)
            
        # Characters Settings
        col = layout.column()
        row = col.row()
        row.prop(scene, "characters_fold", 
                icon='TRIA_DOWN' if scene.characters_fold else 'TRIA_RIGHT',
                icon_only=True, 
                emboss=False)
        row.label(text="CHARACTER SETTINGS", icon='OUTLINER_OB_ARMATURE')
       
        if scene.characters_fold:
            box = col.box()
            box.label(text="Character Scales", icon='CON_SIZELIKE')
            
            row = box.row()
            row.operator("cloud.get_name_list",icon="IMPORT")
            
            if hasattr(scene, "character_list_items"):
                row.prop(scene, "show_character_list", toggle=True,icon= "HIDE_OFF" if scene.show_character_list else "HIDE_ON")
                
            if scene.show_character_list:
                if hasattr(scene, "character_list_items"):
                    # Lista de personajes
                    row = box.row()
                    row.template_list(
                        "CHARACTERS_UL_List", 
                        "", 
                        scene, 
                        "character_list_items", 
                        scene, 
                        "character_list_index", 
                        rows=5
                    )
                
                    if scene.character_list_index >= 0 and len(scene.character_list_items) > scene.character_list_index:
                        selected = scene.character_list_items[scene.character_list_index]
                        col = box.column()
                        col.label(text=f"Scale: {selected.scale:.4f}", icon='DOT')
                    box.operator("character.apply_scale_to_selected", text="Appply Scale", icon='CON_SIZELIKE')
            
            
            box.separator(factor=1)
            box = col.box()
            row = box.row()
            row.label(text="Character updater", icon='FILE_REFRESH')
            props = context.scene.uc_updated_character
          
            characterCollectionAvaible = is_collection_exist("PERSONAJES")
            if characterCollectionAvaible:
                box.prop(props, "collection_enum", text="Old")
            else:
                box.label(text="Personajes deben estar dentro de PERSONAJES")
                
            box.prop(props, "new_collection", text="New")
            if(props.new_collection):
                box.prop(props, "name_collection", text="Select")
            box.operator("mesh.append_and_replace",icon="FILE_REFRESH")
        
                
@addon_updater_ops.make_annotations
class RENDER_PT_UpdaterPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)

    updater_interval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31)

    updater_interval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)

    layouter_name = bpy.props.StringProperty(
        name="Nombre de Layouter",
        default="Layouter")

    def draw(self, context):
        layout = self.layout

        layout.label(text="Información del Layouter:")
        layout.prop(self, "layouter_name")
        layout.separator()
        addon_updater_ops.update_settings_ui(self, context)
