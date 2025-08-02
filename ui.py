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
from .operators.resources_import import RESOURCE_OT_ImportSelected,enum_previews_from_images

def draw_foldable_section(layout, title, icon, fold_prop_name, draw_content_fn, context):
    scene = context.scene
    fold_state = getattr(scene, fold_prop_name)
    box = layout.box()
    header = box.row()
    header.prop(scene, fold_prop_name, icon='TRIA_DOWN' if fold_state else 'TRIA_RIGHT', icon_only=True, emboss=False)
    header.label(text=title, icon=icon)
    if fold_state:
        inner = box.box()
        draw_content_fn(inner, context)

def draw_layout_status_content(layout, context):
    scene = context.scene
    row = layout.row()
    row.operator("render.quick_setup", text="Setup layout", icon='SETTINGS')
    row.prop(scene, "show_render_status", toggle=True, icon="HIDE_OFF" if scene.show_render_status else "HIDE_ON")
    
    col = layout.column(align=True)

    ##recuedo  COLOR_01 ES ROJO 
    if scene.show_render_status:
        icon = 'STRIP_COLOR_01' if not bpy.app.version >= (4, 5, 0) else 'STRIP_COLOR_04'
        col.label(text="Blender version", icon=icon)

        scene_count = len(bpy.data.scenes)
        icon = 'STRIP_COLOR_01' if scene_count > 1 else 'STRIP_COLOR_04'
        col.label(text="One scene", icon=icon)

        cameraCollectionAvaible = is_collection_exist("CAMARA")
        dofText = "DOF in camera collection"
        if not cameraCollectionAvaible:
            col.label(text="'CAMARA' Collection in scene", icon="STRIP_COLOR_01")
        elif cameraCollectionAvaible.objects.get("DOF"):
            col.label(text=dofText, icon="STRIP_COLOR_04")
        else:
            col.label(text=dofText, icon="STRIP_COLOR_01")

        isVisibleOnRender = is_any_object_visible_in_render("NOTAS_LAYOUT")
        iconRender = 'STRIP_COLOR_04' if not isVisibleOnRender else 'STRIP_COLOR_01'
        col.label(text="Visible layout notes", icon=iconRender)
        
        chacheParticles = check_emitters_in_collection()
        iconParticle = 'STRIP_COLOR_04' if not chacheParticles else 'STRIP_COLOR_01'
        col.label(text="Cache particles", icon=iconParticle)

        hasRenderNotes = file_exists_in_blend_directory("NOTAS RENDER.txt")
        iconLayoutNote = 'STRIP_COLOR_09' if not hasRenderNotes else 'STRIP_COLOR_04'
        col.label(text="Render notes", icon=iconLayoutNote)
        
        fps = scene.render.fps
        total_frames = scene.frame_end - (scene.frame_start - 1)
        seconds = total_frames / fps
       
        row = layout.row()
        icon, info = get_icon_by_leght(total_frames)
       
        row.prop(scene, "show_leght_info", text="", icon=icon)
        if scene.show_leght_info:
            layout.row().label(text=info)
            
        row.label(text= f"{seconds:.2f} seconds", icon="TIME")

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
     box.operator("ot.blend_extras", text="Bake all particles", icon='FILE_VOLUME')
     
     box = layout.box()
     box.label(text="Camera", icon='CAMERA_DATA')
     row = box.row(align=True)
     row.label(text="Safe area")
     row.prop(settings, "enabled", toggle=True, icon="RESTRICT_VIEW_OFF" if settings.enabled else "RESTRICT_VIEW_ON")
     row.prop(settings, "color", text="")
     row.prop(settings, "width", text="")
     
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
        wm = context.window_manager

        layout.template_icon_view(wm, "collection_preview_enum")
        if wm.collection_preview_enum:
            box = layout.box()
            row = box.row(align=True)
            row.label(text=wm.collection_preview_enum)
            row.operator("resource.import_selected", icon="IMPORT")

            if scene.resource_import_origin_camera:
                row.operator("resource.place_origin", text="", icon="CURSOR").origin_type = "cursor"
                row.label(text="", icon="OUTLINER_OB_CAMERA")
            if scene.resource_import_origin_cursor:
                row.label(text="", icon="PIVOT_CURSOR")
                row.operator("resource.place_origin", text="", icon="CAMERA_DATA").origin_type = "camera"
        else:
            layout.label(text="No hay previews disponibles")


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