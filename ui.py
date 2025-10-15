import bpy
import os
from . import bl_info
from . import addon_updater_ops
from .scene_utils import (
    is_any_object_visible_in_render,
    is_collection_exist,
    get_icon_by_vertices,
    file_exists_in_blend_directory,
    get_icon_by_leght,
    check_emitters_in_collection
)
from .drive.drive_importer import get_active_drive_preview
#region UTILS

def draw_foldable_section(layout, title, icon, fold_prop_name, draw_content_fn, context):
    scene = context.scene
    fold_state = getattr(scene.fold_settings, fold_prop_name)
    box = layout.box()
    header = box.row()
    header.prop(scene.fold_settings, fold_prop_name, icon='TRIA_DOWN' if fold_state else 'TRIA_RIGHT', icon_only=True, emboss=True)
    header.label(text=title, icon=icon)
    if fold_state:
        inner = box.box()
        icons = getattr(context.window_manager, "custom_icons", None)
        draw_content_fn(inner, context,icons)

def draw_informative_box(col,info,active):
    if active:
        box = col.box()
        lines = info.split("\n")
        for line in lines:
            box.label(text=line, icon='INFO_LARGE')
        col.separator()


def draw_youtube_info(row,_icon,url):
    row.operator("wm.url_open", icon_value=_icon).url = url
    
#endregion


#region PANEL DEFINITIONS

def draw_layout_status_content(layout, context,icons):
    scene = context.scene
    row = layout.row()
    row.operator("render.quick_setup", text="Setup layout", icon_value=icons["setup_layout"].icon_id)
    row.prop(scene.show_settings, "render_status", toggle=True, icon="HIDE_OFF" if scene.show_settings.render_status else "HIDE_ON")
    col = layout.column(align=True)

    ##recuerdo  COLOR_01 ES ROJO 
    if scene.show_settings.render_status:
        
        icon_bd_version = 'STRIP_COLOR_01' if not bpy.app.version == (4, 5, 3) else 'STRIP_COLOR_04'
        row = col.row()
        row.label(text="Blender version", icon=icon_bd_version)
        draw_youtube_info(row,icons["youtube"].icon_id,"https://youtu.be/JiDDLQkjKvU?list=PLJnbM9GLGL-p0A9zpAo08OjqCHfNlJ0Ef")
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
        col.label(text="Visible layout notes", icon=icon_render)
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
       
        row.prop(scene.show_settings, "leght_info", text="", icon=icon)
        if scene.show_settings.leght_info:
            layout.row().label(text=info)
            
        row.label(text= f"{seconds:.2f} seconds", icon="TIME")

def draw_props_settings_content(layout, context,icons):
    scene = context.scene
    title = layout.row(align=True)
    title.prop(scene.show_settings, "advance_prop_settings", toggle=True, icon="HIDE_OFF" if scene.show_settings.advance_prop_settings else "HIDE_ON")
    draw_youtube_info(title,icons["youtube"].icon_id,"https://youtu.be/kVD8lQowyzE")
    if scene.show_settings.advance_prop_settings:
        box = layout.box()
        col = box.column(align=True)
        col.prop(scene.props_advanced_settings, "remove_doubles", text="Remove double vertices")
        col.prop(scene.props_advanced_settings, "remove_empties", text="Remove emptys")
        col.prop(scene.props_advanced_settings, "add_in_collection", text="Create collection")
        col.prop(scene.props_advanced_settings, "mergeObjects", text="Merge meshes")
        col.prop(scene.props_advanced_settings, "only_selected_objects", text="Only selected objects")
        col.prop(scene.props_advanced_settings, "add_final_empty", text="Add final empty")
        layout.separator(factor=0.5)

    selected_objects = context.selected_objects

    if not selected_objects:
        layout.label(text="Ningún objeto seleccionado", icon='ERROR')
    else:
        total_vertices = 0
        total_faces = 0
        mesh_objects = [obj for obj in selected_objects if obj.type == 'MESH']

        if not mesh_objects:
            layout.label(text="Los objetos seleccionados no son mallas", icon='ERROR')
        else:
            for obj in mesh_objects:
                mesh = obj.data
                total_vertices += len(mesh.vertices)
                total_faces += len(mesh.polygons)

            row = layout.row()
            icon, info = get_icon_by_vertices(total_vertices)
            row.prop(scene.show_settings, "prop_helpInfo", text="", icon=icon)
            if scene.show_settings.prop_helpInfo:
                layout.row().label(text=info)
            row.label(text=f"Vertices: {total_vertices}", icon='DOT')
            row.label(text=f"Faces: {total_faces}", icon='MESH_CUBE')
   
    cleanpropbutton = layout.row()
    cleanpropbutton.scale_y = 1.3
    cleanpropbutton.operator("mesh.analyze_mesh", text="Clean Prop", icon='TRASH')
    layout.separator()
    row = layout.row()
    row.operator("mesh.fix_materials", text="Fix materials", icon='MATERIAL')
    row.operator("mesh.emission_view", icon="HIDE_OFF")
    layout.operator("object.add_decimate_modifier", text="Add decimate", icon="MOD_DECIM")
    layout.operator("object.add_smooth_by_angle", text="Add Smooth by angle", icon="OUTLINER_OB_META")
    
def draw_scale_settings_content(layout, context,icons):
    scene = context.scene
    
    box = layout.box()
    row = box.row()
    row.label(text="Character Scales", icon='OUTLINER_OB_ARMATURE')
    draw_youtube_info(row,icons["youtube"].icon_id,"https://youtu.be/HRrO4Oz1b3s")
    row = box.row()
    row.operator("cloud.get_character_list", icon="IMPORT")
    if hasattr(scene, "character_list_items"):
        row.prop(scene.show_settings, "character_list", toggle=True, icon="HIDE_OFF" if scene.show_settings.character_list else "HIDE_ON")

        if scene.show_settings.character_list:
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
        row.label(text="Map Scales", icon='WORLD')
        draw_youtube_info(row,icons["youtube"].icon_id,"https://youtu.be/mIw_6MAmsXY")
        row = box.row()
        row.operator("cloud.get_map_list", icon="IMPORT")

        if hasattr(scene, "map_list_items"):
            row.prop(scene.show_settings, "map_list", toggle=True, icon="HIDE_OFF" if scene.show_settings.map_list else "HIDE_ON")

            if scene.show_settings.map_list:
                box.template_list("MAPS_UL_List", "", scene, "map_list_items", scene, "map_list_index", rows=5)

                if scene.map_list_index >= 0 and len(scene.map_list_items) > scene.map_list_index:
                    selected = scene.map_list_items[scene.map_list_index]
                    box.label(text=f"Scale: {selected.scale:.4f}", icon='DOT')

                box.operator("map.apply_scale_to_selected", text="Apply Scale", icon='CON_SIZELIKE')

def draw_extras_content(layout, context,icons):
     scene = context.scene
     settings = scene.camera_frame_settings
     ln_settings = scene.layout_notes_settings
        
     box = layout.box()
     box.label(text="Layout notes", icon='FILE_TEXT')
     row = box.row(align=True)
     row.operator("extra.create_note", text="Create note", icon_value=icons["note"].icon_id)
     row.prop(ln_settings, "text_color", text="")
     
     rowgp = box.row(align=True)
     rowgp.operator("extra.create_note_gp", text="Create draw", icon_value=icons["draw"].icon_id)
     rowgp.prop(ln_settings, "grease_pencil_color", text="")
    
     box.operator("extra.hide_notes", text="Hide with keyframe", icon="HIDE_ON")
     
     box = layout.box()
     box.label(text="Camera", icon='CAMERA_DATA')
     row = box.row(align=True)
     row.label(text="Safe area")
     row.prop(settings, "enabled", toggle=True, icon="RESTRICT_VIEW_OFF" if settings.enabled else "RESTRICT_VIEW_ON")
     row.prop(settings, "color", text="")
     row.prop(settings, "width", text="")
     
     box = layout.box()
     box.label(text="Particles", icon='PARTICLES')
     box.operator("extra.bake_particles", text="Bake all particles", icon='FILE_VOLUME')

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
            draw_informative_box(box,"• Personajes deben estar dentro de PERSONAJES \n • No deben tener aplicado el scale a deltas!!",True)
        box.prop(props, "new_collection", text="New")
        if props.new_collection:
            box.prop(props, "name_collection", text="Select")
        box.operator("mesh.append_and_replace", icon="FILE_REFRESH")

#endregion

#------------------------------------------------- MAIN PANELS -------------------------------------------------#

class RENDER_PT_QuickSetupPanel(bpy.types.Panel):
    bl_label = "Layout Companion!"
    bl_idname = "RENDER_PT_quick_setup_npanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Layout Companion"

    def draw_header(self, context):
        icons = getattr(context.window_manager, "custom_icons", None)
        if icons:
            self.layout.label(text="", icon_value=icons["LC"].icon_id)

    def draw(self, context):
        layout = self.layout
        draw_foldable_section(layout, "LAYOUT STATUS", "BLENDER", "render_settings_fold", draw_layout_status_content, context)
        draw_foldable_section(layout, "PROPS SETTINGS", "MESH_DATA", "props_settings_fold", draw_props_settings_content, context)
        draw_foldable_section(layout, "SCALE SETTINGS", "CON_SIZELIKE", "scales_fold", draw_scale_settings_content, context)
        draw_foldable_section(layout, "EXTRAS", "POINTCLOUD_DATA", "extras_fold", draw_extras_content, context)


#region RESOURCES

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
        icons = getattr(context.window_manager, "custom_icons", None)
        tabs_row = layout.row(align=False)
        tabs_row.prop(scene, "resource_tabs", expand=True)
        draw_youtube_info(tabs_row,icons["youtube"].icon_id,"https://youtu.be/fDqLOPQNbY0")
        layout.separator()
        
        icons = getattr(context.window_manager, "custom_icons", None)
        if scene.resource_tabs == 'RESOURCES':
            draw_local_resources(layout, context,icons)
        elif scene.resource_tabs == 'DRIVE PROPS':
            draw_drive_resources(layout, context,icons)
        elif scene.resource_tabs == 'MANIQUIES':
            draw_local_maniquies(layout, context,icons)
        elif scene.resource_tabs == 'HORNS FILES':
            draw_horns_resources(layout, context,icons)

def draw_local_resources(layout, context,icons):
    scene = context.scene
    wm = context.window_manager

    resourceBox = layout.box()
    resourceBox.template_icon_view(wm, "res_effects_preview_enum")
    if wm.res_effects_preview_enum:
        box = resourceBox.box()
        box.label(text=wm.res_effects_preview_enum)
        row = box.row(align=True)
        row.scale_y = 1.3
        row.operator("resource.import_selected", icon="IMPORT")
        origin_import_type(scene, row)
    else:
        resourceBox.label(text="No hay previews disponibles")
        
        
def draw_local_maniquies(layout, context,icons):
    scene = context.scene
    wm = context.window_manager

    resourceBox = layout.box()
    resourceBox.template_icon_view(wm, "res_maniques_preview_enum")
    if wm.res_maniques_preview_enum:
        box = resourceBox.box()
        box.label(text=wm.res_maniques_preview_enum)
        row = box.row(align=True)
        row.scale_y = 1.3
        row.operator("resource.import_selected", icon="IMPORT")
        origin_import_type(scene, row)
    else:
        resourceBox.label(text="No hay previews disponibles")
        

def draw_drive_resources(layout, context,icons):
    scene = context.scene
    wm = context.window_manager
    
    box = layout.box()
    box.label(text="Bajo desarrollo: El tiempo de espera es elevado (tu blender se congelara varios segundos)", icon_value=icons["alert"].icon_id)
    box = layout.box()
    propBox = box.box()
    searchrow = propBox.row(align=True)
    searchrow.operator("prop.drive_refresh_previews", icon='FILE_REFRESH')
    searchrow.prop(wm, "drive_search", text="", icon='VIEWZOOM')
    searchrow.prop(scene, "drive_advance_settings", text="",icon="TOOL_SETTINGS")
    if scene.drive_advance_settings:
        deleterow = propBox.row()
        deleterow.label(text="Eliminar el prop seleccionado del drive")
        deleterow.operator("prop.drive_delete", text="", icon='TRASH')
    
        cache_size_mb = get_cache_size_mb()
        propBox.operator("props.cleanup_cache", text=f"Limpiar caché {cache_size_mb:.2f} MB", icon='TRASH')
    
    propBox.template_icon_view(wm, "drive_preview_enum")

    if hasattr(wm, "drive_preview_enum") and wm.drive_preview_enum:
        preview = get_active_drive_preview(context)
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
            row.scale_y = 1.3
            row.operator("prop.drive_import_blend", icon='IMPORT')
            origin_import_type(scene, row)
        else:
            col.label(text="Preview no encontrado")
    else:
        propBox.label(text="No hay previews disponibles")


def draw_horns_resources(layout, context,icons):
    scene = context.scene
    
    box = layout.box()
    devbox = box.box()
    devbox.label(text="Actualmente en desarrollo (Se puede usar)", icon_value=icons["alert"].icon_id)
    if hasattr(scene, "files_list_items"):
        if len(scene.files_list_items) > 0:
            row = box.row(align=True)
            
            if scene.drive_main_page:
                row.operator("drive.refresh_folders",text="Reload", icon='FILE_REFRESH')
            else:
                row.operator("drive.refresh_folders",text="Home", icon='HOME')
                  
            row.operator("drive.open_folder",text="Open trend",icon='FRAME_NEXT')
           
            row = box.row(align=True)
            row.prop(scene, "files_list_filter", text="", icon='VIEWZOOM')
            row.operator("drive.clear_filter", text="", icon='X')
                
            row.prop(scene, "horns_advance_settings", text="",icon="TOOL_SETTINGS")
            if scene.horns_advance_settings:
                settingsbox = box.row(align=True)
                settingsbox.prop(scene, "get_json_automatically", text="Get info automatically",icon="TRIA_DOWN_BAR")
                settingsbox.prop(scene, "show_horns_thumbnail", text="Show preview",icon="OUTLINER_OB_IMAGE")
                
            box.template_list("FILES_UL_List", "", scene, "files_list_items", scene, "files_list_index", rows=5)
           
            if not scene.drive_main_page:
                infobox = box.box()
                idx = scene.files_list_index

                if 0 <= idx < len(scene.files_list_items):
                    item = scene.files_list_items[idx]
                    if item.json_loaded:
                        col = infobox.column(align=True)
                        col.label(text=f"Type: {item.type}", icon='FILE_FOLDER')
                        col.label(text=f"Rigger: {item.rigger}", icon='USER')
                        col.label(text=f"Last update: {item.last_update}", icon='TIME')
                        if item.version:
                            col.label(text=f"Version: v{item.version}", icon='INFO')
                                                
                    if item.thumb_icon and scene.show_horns_thumbnail:
                        from .drive import horns_resources
                        pcoll = horns_resources.get_preview_collection()
                        
                        if item.thumb_icon in pcoll:
                            preview = pcoll[item.thumb_icon]
                            thumb_box = col.box()
                            thumb_col = thumb_box.column(align=True)
                            thumb_col.template_icon(icon_value=preview.icon_id, scale=12.0)
                        else:
                            col.box().label(text="No thumbnail available", icon='IMAGE_DATA')
                                
                    else:
                        if scene.get_json_automatically:
                            infobox.label(text="No existe info de este archivo", icon='INFO')
                        else:
                            infobox.label(text="La opcion de cargar info automaticamente esta desactivada", icon='INFO')

                    row = box.row()
                    row.scale_y = 1.3
                    row.operator("drive.import_file", icon='IMPORT')
                    origin_import_type(scene, row)
                else:
                    infobox.label(text="Seleccione un elemento válido", icon='INFO')
        else:
            box.operator("drive.list_main_folders", icon_value=icons["trends"].icon_id)

#endregion


#region COLLABS

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
        boxrow = box.row()
        
        boxrow.label(text="Export prop to collab",icon="NEWFOLDER")
        boxrow.prop(scene,"prop_guideline",text="",icon="QUESTION")
       
        if scene.prop_guideline:
            show_collab_guideline(box)
        
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
        row.operator("prop.drive_export", icon="EXPORT")
        
        
#endregion


#region ABOUT & UPDATER
 
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

def get_cache_size_mb():
        from .drive.drive_importer import get_temp_folder
        temp_folder = get_temp_folder()
        total_size = 0
        for root, dirs, files in os.walk(temp_folder):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)  # Convertir a MB

#endregion


#region REGISTERS

classes =(
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

#endregion
