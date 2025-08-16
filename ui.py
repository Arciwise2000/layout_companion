import bpy
import os
from . import bl_info
from . import addon_updater_ops
from .addon_updater_ops import get_user_preferences
from .dropbox.dropbox_oauth import get_temp_folder,cleanup_temp_files,is_dropbox_installed
from .scene_utils import (
    is_any_object_visible_in_render,
    is_collection_exist,
    get_icon_by_vertices,
    file_exists_in_blend_directory,
    get_icon_by_leght,
    check_emitters_in_collection
)
from .dropbox.dropbox_oauth import get_active_dropbox_preview

def draw_foldable_section(layout, title, icon, fold_prop_name, draw_content_fn, context):
    scene = context.scene
    fold_state = getattr(scene, fold_prop_name)
    box = layout.box()
    header = box.row()
    header.prop(scene, fold_prop_name, icon='TRIA_DOWN' if fold_state else 'TRIA_RIGHT', icon_only=True, emboss=True)
    header.label(text=title, icon=icon)
    if fold_state:
        inner = box.box()
        draw_content_fn(inner, context)

def draw_informative_box(col,info,active):
    if active:
        box = col.box()
        box.label(text=info, icon="INFO_LARGE")
        col.separator()

def draw_layout_status_content(layout, context):
    scene = context.scene
    row = layout.row()
    row.operator("render.quick_setup", text="Setup layout", icon='SETTINGS')
    row.prop(scene, "show_render_status", toggle=True, icon="HIDE_OFF" if scene.show_render_status else "HIDE_ON")
    
    col = layout.column(align=True)

    ##recuerdo  COLOR_01 ES ROJO 
    if scene.show_render_status:
        
        icon_bd_version = 'STRIP_COLOR_01' if not bpy.app.version >= (4, 5, 0) else 'STRIP_COLOR_04'
        col.label(text="Blender version", icon=icon_bd_version)
        
        ##-----------------------
        scene_count = len(bpy.data.scenes)
        exceedScenes = scene_count > 1
        icon_scene_count = 'STRIP_COLOR_04' if not exceedScenes else 'STRIP_COLOR_01'
            
        col.label(text="One scene", icon=icon_scene_count)
        draw_informative_box(col,"Hay una escena extra en el Blend. Eliminalo para evitar problemas de render!",exceedScenes)
        ##-----------------------
        cameraCollectionAvaible = is_collection_exist("CAMARA")
        dof_text = "DOF in camera collection"
        if not cameraCollectionAvaible:
            col.label(text="'CAMARA' Collection in scene", icon="STRIP_COLOR_01")
            draw_informative_box(col,"No existe la collection 'CAMARA'. Crea o renombra algun collection con ese nombre",True)
        elif cameraCollectionAvaible.objects.get("DOF"):
            col.label(text=dof_text, icon="STRIP_COLOR_04")
        else:
            col.label(text=dof_text, icon="STRIP_COLOR_01")
            draw_informative_box(col,"No existe el empty DOF dentro del collection 'CAMARA'", True)
        ##-----------------------
        isVisibleOnRender = is_any_object_visible_in_render("NOTAS_LAYOUT")
        icon_render = 'STRIP_COLOR_04' if not isVisibleOnRender else 'STRIP_COLOR_01'
        layoutnoterow = col.row()
        layoutnoterow.label(text="Visible layout notes", icon=icon_render)
        layoutnoterow.operator("extra.create_note", text="", icon="PLUS")
        draw_informative_box(col,"Hay objetos con visibilidad en render dentro de 'NOTAS LAYOUT'. Apagalas!",isVisibleOnRender)
        ##-----------------------
        chacheParticles = check_emitters_in_collection()
        icon_particle = 'STRIP_COLOR_04' if not chacheParticles else 'STRIP_COLOR_01'
        col.label(text="Cache particles", icon=icon_particle)
        draw_informative_box(col,"Existen particulas sin bakear! Usa 'bake all particles' o bakea las particulas faltantes",chacheParticles)
        ##-----------------------
        icon_rsc_pack = 'STRIP_COLOR_01' if not bpy.data.use_autopack else 'STRIP_COLOR_04'
        col.label(text="Automatically pack resource", icon=icon_rsc_pack)
        draw_informative_box(col,"Las imagenes no se guardaran con tu blend! Activa 'Automatically pack resource' o pulsa el boton 'Setup Layout'",not bpy.data.use_autopack)
        ##-----------------------
        hasRenderNotes = file_exists_in_blend_directory("NOTAS RENDER.txt")
        icon_layout_note = 'STRIP_COLOR_09' if not hasRenderNotes else 'STRIP_COLOR_04'
        col.label(text="Render notes", icon=icon_layout_note)

        fps = scene.render.fps
        total_frames = scene.frame_end - (scene.frame_start - 1)
        seconds = total_frames / fps
       
        row = layout.row()
        icon, info = get_icon_by_leght(total_frames)
       
        row.prop(scene, "show_leght_info", text="", icon=icon)
        if scene.show_leght_info:
            layout.row().label(text=info)
            
        row.label(text= f"{seconds:.2f} seconds", icon="TIME")
        
        ##elapsed = int(time.time() - scene.session_start_time)
        ##hours = elapsed // 3600
        ##minutes = (elapsed % 3600) // 60
        ##row = layout.row(alignment="CENTER")
        ##row.label(text="Blender time:")
        ##row.label(text=f"{hours:02d}:{minutes:02d} (hh:mm)")

def draw_props_settings_content(layout, context):
    scene = context.scene
    layout.prop(scene, "show_advance_prop_settings", toggle=True, icon="HIDE_OFF" if scene.show_advance_prop_settings else "HIDE_ON")

    if scene.show_advance_prop_settings:
        layout.prop(scene, "remove_doubles", text="Remove double vertices")
        layout.prop(scene, "remove_empties", text="Remove emptys")
        layout.prop(scene, "add_in_collection", text="Create collection")
        layout.prop(scene, "mergeObjects", text="Merge meshes")
        layout.prop(scene, "only_selected_objects", text="Only selected objects")
        layout.separator(factor=0.5)

    obj = context.active_object
    if not obj:
        layout.label(text="Ningún objeto seleccionado", icon='ERROR')
    elif obj.type != 'MESH':
        layout.label(text="El objeto no es una malla", icon='ERROR')
    else:
        mesh = obj.data
        row = layout.row()
        icon, info = get_icon_by_vertices(len(mesh.vertices))
        row.prop(scene, "show_prop_helpInfo", text="", icon=icon)
        if scene.show_prop_helpInfo:
            layout.row().label(text=info)
        row.label(text=f"Vertices: {len(mesh.vertices)}", icon='DOT')
        row.label(text=f"Faces: {len(mesh.polygons)}", icon='MESH_CUBE')

    layout.operator("mesh.analyze_mesh", text="Clean Prop", icon='TRASH')
    row = layout.row()
    row.operator("mesh.fix_materials", text="Fix materials", icon='MATERIAL')
    row.operator("mesh.emission_view", icon="HIDE_OFF")
    layout.separator()
    layout.operator("object.add_decimate_modifier", text="Add decimate", icon="MOD_DECIM")
    layout.operator("object.add_smooth_by_angle", text="Add Smooth by angle", icon="OUTLINER_OB_META")
    
def draw_character_settings_content(layout, context):
    scene = context.scene
    
    box = layout.box()
    box.label(text="Character Scales", icon='CON_SIZELIKE')
    row = box.row()
    row.operator("cloud.get_name_list", icon="IMPORT")

    if hasattr(scene, "character_list_items"):
        row.prop(scene, "show_character_list", toggle=True, icon="HIDE_OFF" if scene.show_character_list else "HIDE_ON")

        if scene.show_character_list:
            box.template_list("CHARACTERS_UL_List", "", scene, "character_list_items", scene, "character_list_index", rows=5)

            if scene.character_list_index >= 0 and len(scene.character_list_items) > scene.character_list_index:
                selected = scene.character_list_items[scene.character_list_index]
                box.label(text=f"Scale: {selected.scale:.4f}", icon='DOT')
 
            box.operator("character.apply_scale_to_selected", text="Apply Scale", icon='CON_SIZELIKE')
            row = box.row(align=True)
            row.prop(scene,"lock_character_loc",icon="LOCKED")
            row.prop(scene,"lock_character_rot",icon="LOCKED")
            row.prop(scene,"lock_character_scale",icon="LOCKED")

    box = layout.box()
    row = box.row()
    row.label(text="Character updater", icon='FILE_REFRESH')
    
    wm = context.window_manager

    row.prop(wm, "show_characterUpdater", toggle=True, icon="HIDE_OFF" if wm.show_characterUpdater else "HIDE_ON")
    if wm.show_characterUpdater:
        props = context.window_manager.uc_updated_character

        if is_collection_exist("PERSONAJES"):
            box.prop(props, "collection_enum", text="Old")
        else:
            box.label(text="Personajes deben estar dentro de PERSONAJES")

        box.prop(props, "new_collection", text="New")
        if props.new_collection:
            box.prop(props, "name_collection", text="Select")
        box.operator("mesh.append_and_replace", icon="FILE_REFRESH")

def draw_extras_content(layout, context):
     scene = context.scene
     settings = scene.camera_frame_settings
     
     box = layout.box()
     box.label(text="Particles", icon='PARTICLES')
     box.operator("extra.bake_particles", text="Bake all particles", icon='FILE_VOLUME')
     
     box = layout.box()
     box.label(text="Camera", icon='CAMERA_DATA')
     row = box.row(align=True)
     row.label(text="Safe area")
     row.prop(settings, "enabled", toggle=True, icon="RESTRICT_VIEW_OFF" if settings.enabled else "RESTRICT_VIEW_ON")
     row.prop(settings, "color", text="")
     row.prop(settings, "width", text="")
     
     
##---------------------PANELS----------------------------##

class RENDER_PT_QuickSetupPanel(bpy.types.Panel):
    bl_label = "Layout Companion!"
    bl_idname = "RENDER_PT_quick_setup_npanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Layout Companion"

    def draw_header(self, context):
        self.layout.label(text="", icon="FUND")

    def draw(self, context):
        layout = self.layout
        draw_foldable_section(layout, "LAYOUT STATUS", "BLENDER", "render_settings_fold", draw_layout_status_content, context)
        draw_foldable_section(layout, "PROPS SETTINGS", "MESH_DATA", "props_settings_fold", draw_props_settings_content, context)
        draw_foldable_section(layout, "CHARACTER SETTINGS", "OUTLINER_OB_ARMATURE", "characters_fold", draw_character_settings_content, context)
        draw_foldable_section(layout, "EXTRAS", "POINTCLOUD_DATA", "extras_fold", draw_extras_content, context)

def origin_import_type(scene, row):
    if scene.resource_import_origin_camera:
        row.operator("resource.place_origin", text="", icon="CURSOR").origin_type = "cursor"
        row.label(text="", icon="OUTLINER_OB_CAMERA")
    if scene.resource_import_origin_cursor:
        row.label(text="", icon="PIVOT_CURSOR")
        row.operator("resource.place_origin", text="", icon="CAMERA_DATA").origin_type = "camera"

class RENDER_PT_Resources(bpy.types.Panel):
    bl_label = "Resources"
    bl_idname = "RENDER_PT_Resources"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Layout Companion"
    
    def draw_header(self, context):
        self.layout.label(text="", icon="SNAP_VOLUME")
    def draw(self, context):
        scene = context.scene
        layout = self.layout
        
        tabs_row = layout.row(align=True)
        tabs_row.prop(scene, "resource_tabs", expand=True)
        
        layout.separator()
        
        if scene.resource_tabs == 'RESOURCES':
            draw_local_resources(layout, context)
        elif scene.resource_tabs == 'DROPBOX PROPS':
            draw_dropbox_resources(layout, context)

def draw_local_resources(layout, context):
    scene = context.scene
    wm = context.window_manager

    resourceBox = layout.box()
    resourceBox.template_icon_view(wm, "collection_preview_enum")
    if wm.collection_preview_enum:
        box = resourceBox.box()
        box.label(text=wm.collection_preview_enum)
        row = box.row(align=True)
        row.scale_y = 1.2
        row.operator("resource.import_selected", icon="IMPORT")
        origin_import_type(scene, row)
    else:
        resourceBox.label(text="No hay previews disponibles")

def draw_dropbox_resources(layout, context):
    scene = context.scene
    wm = context.window_manager
    prefs = get_user_preferences(context)

    box = layout.box()
    
    if not is_dropbox_installed():
        box.label(text="Dropbox is not installed, install from button bellow",icon="X")
        box.operator("prop.install_dependencies",icon="IMPORT")
        return
    
    if prefs.dropbox_access_token:
        row = box.row()
        row.label(text="Authenticated with Dropbox", icon='CHECKMARK')
        row.operator("prop.dropbox_logout", icon="DISCLOSURE_TRI_RIGHT")
    else:
        box.operator("prop.dropbox_auth", text="Connect with Dropbox", icon='URL')

    if not prefs.dropbox_access_token:
        return

    propBox = box.box()
    searchrow = propBox.row(align=True)
    searchrow.operator("prop.dropbox_refresh_previews", icon='FILE_REFRESH')
    searchrow.prop(wm, "dropbox_search", text="", icon='VIEWZOOM')
    propBox.template_icon_view(wm, "dropbox_preview_enum")

    if hasattr(wm, "dropbox_preview_enum") and wm.dropbox_preview_enum:
        preview = get_active_dropbox_preview(context)
        col = propBox.column(align=True)
        if preview:
            col.label(text=f"{preview.name}", icon="OBJECT_DATA")
            col.label(text=f"{preview.descripcion}", icon="TEXT")
            col.label(text=f"{preview.colaborador}", icon="USER")
            row = col.row()
            row.scale_y = 1
            row.label(text="", icon="TAG")
            if preview.tags:
                for tag in preview.tags:
                    tagbox = row.box()
                    tagbox.scale_y = 0.4
                    tagbox.label(text=tag.name)

            box = propBox.box()
            row = box.row(align=True)
            row.scale_y = 1.2
            row.operator("prop.dropbox_import_blend", icon='IMPORT')
            origin_import_type(scene, row)
        else:
            col.label(text="Preview no encontrado")
    else:
        propBox.label(text="No hay previews disponibles")

def show_collab_guideline(layout):
    box = layout.box()
    box.label(text="Prop export GUIDELINE:", icon='INFO')

    tips_box = box.box()
    tips_box.label(text="• El prop debe haber sido usado en algun layout.")
    tips_box.label(text="• El tamaño del prop no debe superar los 100MB.")
    tips_box.label(text="• Las texturas no deben ser mayor a 2048x2048.")
    tips_box.label(text="• El material debe ser para Cycles, sin emission.")
    tips_box.label(text="• Evita subir el mismo prop que otros colaboradores.")
    tips_box.label(text="• Nombre del prop en ingles. Descripcion: (ingles o español).")
    tips_box.label(text="• Se creativo :)")
    
def collab_prop_status(layout, ready):
    icon = 'STRIP_COLOR_01' if not ready else 'STRIP_COLOR_04'
    layout.label(text="",icon = icon)

class RENDER_PT_Collab(bpy.types.Panel):
    bl_label = "Collabs"
    bl_idname = "RENDER_PT_Collabs"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Layout Companion"
    
    def draw_header(self, context):
        self.layout.label(text="", icon="VIEW_PAN")
        
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        scene = context.scene
        prefs = get_user_preferences(context)
        boxrow = box.row()
        
        if not is_dropbox_installed():
            boxrow.label(text="Dropbox is not installed, install from: resources > dropbox props tab",icon="X")
            return
        
        boxrow.label(text="Export prop to collab",icon="NEWFOLDER")
        boxrow.prop(scene,"prop_guideline",text="",icon="QUESTION")
       
        if scene.prop_guideline:
            show_collab_guideline(box)
        
        if not prefs.dropbox_access_token:
            box.operator("prop.dropbox_auth", text="Connect with Dropbox", icon='URL')
            return
        
        databox = box.box()
        proprow = databox.row()
        proprow.prop(scene, "all_collections", text="Prop")
        collab_prop_status(proprow, scene.all_collections)
        
        previewbox = databox.box()
        previewrow = previewbox.row()
        previewrow.label(text="Preview")
        previewrow.operator("prop.collaborator_delete_texture",icon="X")
        previewrow.operator("props.select_preview_image", icon="FILE_FOLDER")
        previewrow.operator("props.preview_maker", icon="RESTRICT_RENDER_OFF")
        collab_prop_status(previewrow, scene.prop_preview_tex)
        row = previewbox.row()
        if scene.prop_preview_tex:
            row.template_preview(scene.prop_preview_tex, show_buttons=False)
        else:
            row.label(text="No preview image yet... select from pc, or make a render")
        
        idrow = databox.row()
        idrow.prop(scene, "prop_idname", text="ID")
        collab_prop_status(idrow, scene.prop_idname.strip())
        
        namerow = databox.row()
        namerow.prop(scene, "prop_filename", text="Name")
        collab_prop_status(namerow, scene.prop_filename.strip())
        
        databox.prop(scene, "prop_description", text="Description")
        
        collabnameRow = databox.row(align=True)
        collabnameRow.prop(scene, "collaborator_name", text="Collaborator")
        collabnameRow.operator("prop.collaborator_layouter_name",icon="USER")
        
        tagsrow = databox.row()
        tagsrow.prop(scene, "tags_fold", icon='TRIA_DOWN' if scene.tags_fold else 'TRIA_RIGHT', icon_only=True, emboss=True)
        tagsrow.label(text="Tags")
        
        has_tags_selected = bool(scene.tags_props_enum)
        collab_prop_status(tagsrow, has_tags_selected)
       
        if scene.tags_fold:
            grid = databox.grid_flow(columns=4, even_columns=True, even_rows=True, align=True)
            grid.use_property_split = False
            grid.use_property_decorate = False
        
            for item in scene.bl_rna.properties['tags_props_enum'].enum_items:
                grid.prop_enum(scene, "tags_props_enum", item.identifier, text=item.name)
        
        databox.separator()
        row = databox.row()
        row.scale_y = 2
        row.operator("prop.collab_export", icon="EXPORT")
        
class RENDER_PT_About(bpy.types.Panel):
    bl_label = "About"
    bl_idname = "RENDER_PT_About"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Layout Companion"
    
    def draw_header(self, context):
        self.layout.label(text="", icon="INFO")
        
    def draw(self, context):
        layout = self.layout
        version = bl_info.get("version", (0, 0, 0))
        version_str = ".".join(map(str, version))
        layout.label(text="Version: " + version_str)
        layout.operator("wm.url_open", text="Visit GitHub").url = "https://github.com/Arciwise2000/layout_companion"

   
@addon_updater_ops.make_annotations
class RENDER_PT_UpdaterPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    
    dropbox_access_token: bpy.props.StringProperty(
        name="Dropbox Access Token",
        subtype='PASSWORD',
        default="")
    
    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)

    updater_interval_days = bpy.props.IntProperty(
        name='Days', description="Days between update checks",
        default=7, min=0, max=31)

    updater_interval_hours = bpy.props.IntProperty(
        name='Hours', description="Hours between update checks",
        default=0, min=0, max=23)

    layouter_name = bpy.props.StringProperty(
        name="Nombre de Layouter",
        default="Layouter")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Información del Layouter:")
        layout.prop(self, "layouter_name")
        layout.separator()
        addon_updater_ops.update_settings_ui(self, context)
        layout.separator()
        box = layout.box()
        temp_folder = get_temp_folder()
        cache_size_mb = self.get_cache_size_mb(temp_folder)
        box.label(text=f"Tamaño de caché: {cache_size_mb:.2f} MB")
        box.operator("props.cleanup_cache", text="Limpiar caché", icon='TRASH')

    def get_cache_size_mb(self, folder_path):
            total_size = 0
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    fp = os.path.join(root, f)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
            return total_size / (1024 * 1024)  # Convertir a MB

class PROPS_OT_CleanupCache(bpy.types.Operator):
    bl_idname = "props.cleanup_cache"
    bl_label = "Limpiar Caché"
    bl_description = "Elimina todos los archivos temporales de la carpeta de caché"

    def execute(self, context):
        try:
            cleanup_temp_files()
            self.report({'INFO'}, "Caché limpiada con éxito.")
        except Exception as e:
            self.report({'ERROR'}, f"Error al limpiar caché: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}


classes =(
    PROPS_OT_CleanupCache,
    RENDER_PT_QuickSetupPanel,
    RENDER_PT_Resources,
    RENDER_PT_Collab,
    RENDER_PT_About,
    RENDER_PT_UpdaterPreferences
)

def register_ui():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_ui():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
        
