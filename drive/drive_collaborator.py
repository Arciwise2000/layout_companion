import bpy
import json
import tempfile
from pathlib import Path
from ..addon_updater_ops import get_user_preferences
from .drive_importer import get_temp_folder
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from .. import addon_dir

TAGS_PROPS = [
    ('VEH', "vehicle", "Prop de transporte, como autos, bicicletas, barcos, etc."),
    ('RIG', "rigged", "Prop con rig o controladores para animación."),
    ('ENV', "environment", "Elemento decorativo o estructural del entorno."),
    ('ANM', "animal", "Representación de un animal o criatura no humana."),
    ('ELE', "electronic", "Dispositivo o componente electrónico."),
    ('GUN', "weapon", "Prop armamentístico ficticio."),
    ('CLH', "cloth", "Objeto hecho de tela o ropa."),
    ('FOD', "food", "Comida o bebida."),
    ('NAT', "nature", "Elemento natural."),
    ('MAT', "material", "Material o grupo de nodos."),
    ('ANI', "animated", "Prop animado."),
    ('FXS', "Effect", "Efecto visual o sistema de partículas."),
    ('MIS', "misc", "Prop misceláneo."),
    ('GND', "geometry node", "Prop con Geometry Nodes."),
    ('GRA', "grabable", "Prop que puede ser sostenido."),
    ('2D', "2d", "Prop bidimensional.")
]


def collections_enum_items(self, context):
    return [(col.name, col.name, "") for col in bpy.data.collections]


def gather_collection_data(collection):
    objects = list(collection.all_objects)
    meshes = [obj.data for obj in objects if obj.type == 'MESH' and obj.data]
    materials, images = [], []

    for mat in (m for mesh in meshes for m in mesh.materials if m):
        if mat not in materials:
            materials.append(mat)
        for node in getattr(mat.node_tree, "nodes", []):
            if node.type == 'TEX_IMAGE' and node.image and node.image not in images:
                images.append(node.image)

    return {
        "collections": [collection],
        "objects": objects,
        "meshes": meshes,
        "materials": materials,
        "images": images
    }


def export_collection_clean(collection, filepath):
    data_to_save = gather_collection_data(collection)
    ids_to_save = {
        *data_to_save["collections"],
        *data_to_save["objects"],
        *data_to_save["meshes"],
        *data_to_save["materials"],
        *data_to_save["images"]
    }
    bpy.data.libraries.write(filepath, ids_to_save, fake_user=True)


def upload_to_drive(local_path: str, filename: str):
    
    from . import drive_importer

    drive_importer.load_drive_config()
    service = drive_importer.get_drive_service()
    parent_id = drive_importer.SHARED_FOLDER_ID
    
    print(parent_id)
    file_metadata = {"name": filename, "parents": [parent_id]}
    media = MediaFileUpload(local_path, resumable=True)

    q = f"name = '{filename}' and '{parent_id}' in parents and trashed = false"
    existing = service.files().list(q=q, fields="files(id)").execute().get("files", [])
    if existing:
        service.files().update(fileId=existing[0]["id"], media_body=media).execute()
    else:
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()



class DRIVE_OT_ExportCollaboration(bpy.types.Operator):
    bl_idname = "prop.drive_export"
    bl_label = "Export"
    bl_description = "Exporta la colección seleccionada como archivo limpio a Google Drive"

    def execute(self, context):
        scene = context.scene
        collection = scene.all_collections

        if not collection:
            self.report({'ERROR'}, "No hay colección seleccionada.")
            return {'CANCELLED'}

        if not scene.prop_idname.strip():
            self.report({'ERROR'}, "Falta asignar un ID al prop (prop_idname).")
            return {'CANCELLED'}

        if not scene.prop_filename.strip():
            self.report({'ERROR'}, "Falta asignar el nombre al prop.")
            return {'CANCELLED'}

        if not scene.prop_preview_tex:
            self.report({'ERROR'}, "Falta preview.")
            return {'CANCELLED'}

        if not bool(scene.tags_props_enum):
            self.report({'ERROR'}, "Falta tags.")
            return {'CANCELLED'}

        prop_id = scene.prop_idname.strip()
        base_name = prop_id
        wm = context.window_manager
        temp_dir = get_temp_folder()
        blend_path = temp_dir / f"{base_name}.blend"
        json_path = temp_dir / f"{base_name}.json"
        png_path = temp_dir / f"{base_name}.png"

        try:
            wm.progress_begin(0, 100)
            wm.progress_update(10)

            # 1. EXPORT BLEND
            export_collection_clean(collection, str(blend_path))
            wm.progress_update(25)

            # 2. SAVE PREVIEW
            if scene.prop_preview_tex and scene.prop_preview_tex.image:
                scene.prop_preview_tex.image.save_render(filepath=str(png_path))
            else:
                self.report({'ERROR'}, "No se encontró imagen de preview.")
                return {'CANCELLED'}

            wm.progress_update(50)

            # 3.  JSON BORN
            selected_labels = [
                label for id_, label, _ in TAGS_PROPS if id_ in scene.tags_props_enum
            ]
            json_data = {
                "nombre_demostrativo": scene.prop_filename,
                "thumbnail": f"{base_name}.png",
                "colaborador": scene.collaborator_name,
                "tags": selected_labels,
                "descripcion": scene.prop_description
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)

            wm.progress_update(75)

            # 4. UPLOAD
            try:
                upload_to_drive(str(blend_path), f"{base_name}.blend")
                upload_to_drive(str(png_path), f"{base_name}.png")
                upload_to_drive(str(json_path), f"{base_name}.json")
            except HttpError as e:
                self.report({'ERROR'}, f"Error HTTP de Drive: {e}")
                return {'CANCELLED'}

            wm.progress_update(100)
            self.report({'INFO'}, f"Prop '{base_name}' exportado correctamente a Google Drive.")
            clear_all()
        except Exception as e:
            self.report({'ERROR'}, f"Error al exportar: {e}")
            return {'CANCELLED'}
        finally:
            wm.progress_end()
            # Limpieza temporal
            for p in (blend_path, json_path, png_path):
                if p.exists():
                    try:
                        p.unlink()
                    except:
                        pass

        return {'FINISHED'}



class DRIVE_OT_SetLayouterName(bpy.types.Operator):
    bl_idname = "prop.collaborator_layouter_name"
    bl_label = ""
    bl_description = "Usa tu nombre de layouter"

    def execute(self, context):
        prefs = get_user_preferences(bpy.context)
        if prefs:
            bpy.context.scene.collaborator_name = prefs.layouter_name
        return {'FINISHED'}


class DRIVE_OT_DeleteTexture(bpy.types.Operator):
    bl_idname = "prop.collaborator_delete_texture"
    bl_label = ""
    bl_description = "Elimina la textura actual"

    def execute(self, context):
        scene = context.scene
        tex = scene.prop_preview_tex
        temp_png = Path(tempfile.gettempdir()) / "prop_preview.png"
        if temp_png.exists():
            try:
                temp_png.unlink()
                self.report({'INFO'}, "Archivo temporal eliminado.")
            except Exception as e:
                self.report({'WARNING'}, f"No se pudo eliminar: {e}")

        if tex:
            if tex.image:
                bpy.data.images.remove(tex.image)
            bpy.data.textures.remove(tex)
            scene.prop_preview_tex = None
            self.report({'INFO'}, "Textura de preview eliminada.")
        return {'FINISHED'}


def clear_all():
    scenes = bpy.data.scenes
    if "EXPORT_PREVIEW" in scenes:
        scenes.remove(scenes["EXPORT_PREVIEW"])
    scene = bpy.context.scene
    scene.all_collections = None
    scene.prop_idname = ""
    scene.prop_filename = ""
    scene.prop_description = "Prop listo para su uso!"
    scene.tags_props_enum = set()


class DRIVE_OT_SelectPreviewImage(bpy.types.Operator):
    bl_idname = "props.select_preview_image"
    bl_label = ""
    bl_description = "Selecciona una imagen para usar como preview del prop"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.png;*.jpg;", options={'HIDDEN'})

    def execute(self, context):
        scene = context.scene
        path = Path(self.filepath)
        if not path.exists():
            self.report({'ERROR'}, "Archivo no encontrado.")
            return {'CANCELLED'}

        try:
            img = bpy.data.images.load(str(path))
            tex = bpy.data.textures.new("PreviewTex", type='IMAGE')
            tex.image = img
            tex.extension = 'EXTEND'
            scene.prop_preview_tex = tex
            self.report({'INFO'}, f"Imagen '{path.name}' cargada.")
        except Exception as e:
            self.report({'ERROR'}, f"No se pudo cargar la imagen: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# MODO FOTO

class COLLAB_OT_PreviewMaker(bpy.types.Operator):
    bl_idname = "props.preview_maker"
    bl_label = ""
    bl_description = "Crea una escena para sacar preview del objeto"

    def execute(self, context):

        if not bpy.context.scene.all_collections:
            self.report(
                {'ERROR'}, "No tienes la colección del prop seleccionada")
            return {'CANCELLED'}

        old_scene = bpy.context.scene
        saved_data = {
            "all_collections": old_scene.all_collections,
            "prop_filename": old_scene.prop_filename,
            "collaborator_name": old_scene.collaborator_name,
            "prop_description": old_scene.prop_description,
            "tags_props_enum": old_scene.tags_props_enum,
            "prop_preview_tex": old_scene.prop_preview_tex
        }

        if "EXPORT_PREVIEW" in bpy.data.scenes:
            target_scene = bpy.data.scenes["EXPORT_PREVIEW"]
        else:
            target_scene = import_export_preview_scene()
            if not target_scene:
                self.report(
                    {'ERROR'}, "No se pudo importar la escena EXPORT_PREVIEW")
                return {'CANCELLED'}

        if assign_render_to_preview not in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.append(assign_render_to_preview)

        bpy.context.window.scene = target_scene
        bpy.context.view_layer.update()
        set_camera_view()

        for key, value in saved_data.items():
            setattr(bpy.context.scene, key, value)

        prop_collection = saved_data["all_collections"]
        if prop_collection and prop_collection.name not in target_scene.collection.children:
            target_scene.collection.children.link(prop_collection)

        return {'FINISHED'}
    
def assign_render_to_preview(scene):
    try:
        temp_png = Path(tempfile.gettempdir()) / "prop_preview.png"
        bpy.data.images['Render Result'].save_render(filepath=str(temp_png))

        img = bpy.data.images.load(str(temp_png))
        tex = bpy.data.textures.new("PreviewTex", type='IMAGE')
        tex.image = img
        tex.extension = 'EXTEND'

        # Asignar a la propiedad de la escena
        scene.prop_preview_tex = tex

        print(f"[PreviewMaker] Preview guardada en {temp_png}")

    except Exception as e:
        print(f"[PreviewMaker] Error guardando preview: {e}")

def import_export_preview_scene():
    addon_path = Path(addon_dir)  # 👈 convierte string a Path
    blend_path = addon_path / "local_resources" / "LayoutCompanionExport.blend"

    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        if "EXPORT_PREVIEW" in data_from.scenes:
            data_to.scenes.append("EXPORT_PREVIEW")
        else:
            print("ERROR: No se encontró la escena EXPORT_PREVIEW en", blend_path)
            return None

    return bpy.data.scenes.get("EXPORT_PREVIEW")


def set_camera_view():
    cam = bpy.context.scene.camera
    if not cam:
        print("No hay cámara activa en la escena.")
        return

    # Itera sobre las áreas para encontrar una VIEW_3D
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'CAMERA'
                    space.lock_camera = False  # Opcional: desbloquea la vista si estaba bloqueada
                    break
            break



class DriveCollabProperties(bpy.types.PropertyGroup):
    bpy.types.Scene.all_collections = bpy.props.PointerProperty(
        name="Collection", type=bpy.types.Collection)
    bpy.types.Scene.prop_preview_tex = bpy.props.PointerProperty(
        name="Preview Texture", type=bpy.types.Texture)
    bpy.types.Scene.prop_idname = bpy.props.StringProperty(name="ID", default="")
    bpy.types.Scene.prop_filename = bpy.props.StringProperty(name="Name", default="")
    bpy.types.Scene.prop_description = bpy.props.StringProperty(
        name="Description", default="Prop listo para su uso!")
    bpy.types.Scene.collaborator_name = bpy.props.StringProperty(name="Collaborator:", default="")
    bpy.types.Scene.tags_props_enum = bpy.props.EnumProperty(
        name="Tags", items=TAGS_PROPS, options={'ENUM_FLAG'}, default=set())
    bpy.types.Scene.tags_fold = bpy.props.BoolProperty(name="Tags", default=False)
    bpy.types.Scene.prop_guideline = bpy.props.BoolProperty(name="Guidelines", default=False)



classes = (
    DRIVE_OT_ExportCollaboration,
    DRIVE_OT_SelectPreviewImage,
    DRIVE_OT_SetLayouterName,
    DRIVE_OT_DeleteTexture,
    DriveCollabProperties,
    COLLAB_OT_PreviewMaker
)


def register_drive_collaboration():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.drive_props = bpy.props.PointerProperty(type=DriveCollabProperties)


def unregister_drive_collaboration():
    del bpy.types.Scene.drive_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
