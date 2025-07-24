import bpy
from . import addon_updater_ops
from .LC_utils import is_any_object_visible_in_render
from .LC_utils import is_collection_exist
from .LC_utils import get_icon_by_vertices

class RENDER_PT_QuickSetupPanel(bpy.types.Panel):
    bl_label = "Layout Companion!"
    bl_idname = "RENDER_PT_quick_setup_npanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tools"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Import Settings
        # col = layout.column()
        # row = col.row()
        # row.prop(scene, "import_settings_fold", 
        #         icon='TRIA_DOWN' if scene.import_settings_fold else 'TRIA_RIGHT',
        #         icon_only=True, 
        #         emboss=False)
        # row.label(text="Imports", icon="GROUP")
        
        # if scene.import_settings_fold:
        #     box = col.box()
        #     row = box.row()
        #     row.operator("import.image_as_plane", text="Import Image as plane", icon='MESH_PLANE')
        
        # layout.separator(factor=1)
            
        
        # Render Settings
        col = layout.column()
        row = col.row()
        row.prop(scene, "render_settings_fold", 
                icon='TRIA_DOWN' if scene.render_settings_fold else 'TRIA_RIGHT',
                icon_only=True, 
                emboss=False)
        row.label(text="BLEND SETUP", icon="BLENDER")
        
        if scene.render_settings_fold:
            box = col.box()
            row = box.row()
            row.operator("render.quick_setup", text="Setup .Blend to Render", icon='SETTINGS')
            
            icon = 'STRIP_COLOR_01' if not bpy.app.version >= (4, 5, 0) else 'STRIP_COLOR_04'
            box.label(text="Blender Version", icon=icon)
            
            scene_count = len(bpy.data.scenes)
            icon = 'STRIP_COLOR_01' if scene_count > 1 else 'STRIP_COLOR_04'
            box.label(text="Only One Scene", icon=icon)
            
            cameraCollectionAvaible = is_collection_exist("CAMERA")
            dofText = "DOF in Camera Collection"
            if not cameraCollectionAvaible:
                box.label(text="'CAMERA' Collection in Scene", icon="STRIP_COLOR_01")
            elif cameraCollectionAvaible.objects.get("DOF"):
                box.label(text= dofText, icon="STRIP_COLOR_04")
            else:
                box.label(text= dofText, icon="STRIP_COLOR_01")
                
            collection_name = "NOTAS_LAYOUT"
            isVisibleOnRender = is_any_object_visible_in_render(collection_name)
            iconRender = 'STRIP_COLOR_04' if not isVisibleOnRender else 'STRIP_COLOR_01'
            box.label(text="Visible Layout Notes", icon=iconRender)
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
            box.prop(scene, "show_AdvancePropSettings", toggle=True)
            
            if scene.show_AdvancePropSettings:
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
            box.operator("cloud.get_name_list")
            
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
                
                
@addon_updater_ops.make_annotations
class RENDER_PT_UpdaterPreferences(bpy.types.AddonPreferences):
	bl_idname = __package__
 
	auto_check_update = bpy.props.BoolProperty(
		name="Auto-check for Update",
		description="If enabled, auto-check for updates using an interval",
		default=False)

	updater_interval_months = bpy.props.IntProperty(
		name='Months',
		description="Number of months between checking for updates",
		default=0,
		min=0)

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

	updater_interval_minutes = bpy.props.IntProperty(
		name='Minutes',
		description="Number of minutes between checking for updates",
		default=0,
		min=0,
		max=59)

	def draw(self, context):
		layout = self.layout

		# Works best if a column, or even just self.layout.
		mainrow = layout.row()
		col = mainrow.column()

		# Updater draw function, could also pass in col as third arg.
		addon_updater_ops.update_settings_ui(self, context)

		# Alternate draw function, which is more condensed and can be
		# placed within an existing draw function. Only contains:
		#   1) check for update/update now buttons
		#   2) toggle for auto-check (interval will be equal to what is set above)
		# addon_updater_ops.update_settings_ui_condensed(self, context, col)

		# Adding another column to help show the above condensed ui as one column
		# col = mainrow.column()
		# col.scale_y = 2
		# ops = col.operator("wm.url_open","Open webpage ")
		# ops.url=addon_updater_ops.updater.website