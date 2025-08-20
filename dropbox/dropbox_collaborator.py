import os
import bpy
import json

import tempfile
from pathlib import Path
from ..addon_updater_ops import get_user_preferences
from .dropbox_oauth import get_temp_folder, get_dbx


TAGS_PROPS = [
    ('VEH', "vehicle", "Prop de transporte, como autos, bicicletas, barcos, etc."),
    ('RIG', "rigged", "Prop con rig o controladores para animación, incluyendo empties que simulan huesos."),
    ('ENV', "environment",
     "Elemento decorativo o estructural del entorno, como edificios, muebles o paisajes."),
    ('ANM', "animal", "Representación de un animal o criatura no humana."),
    ('ELE', "electronic", "Dispositivo o componente electrónico, como computadoras, teléfonos o electrodomésticos."),
    ('GUN', "weapon", "Prop armamentistico o que generen daño. (No deben ser reales)"),
    ('CLH', "cloth", "Prop hecho de tela o ropa, como prendas, banderas o cortinas."),
    ('FOD', "food", "Comida o bebida, como frutas, platos preparados o ingredientes."),
    ('NAT', "nature", "Elemento natural, como plantas, rocas, agua o árboles."),
    ('MAT', "material", "Material, grupo de nodos o texturas"),
    ('ANI', "animated", "Prop que contiene keys de animacion"),
    ('FXS', "Effect", "Tu prop es un particle system, sequencia de sprites, o algun otro que se considere efecto visual"),
    ('MIS', "misc", "Si tu prop no cumple con ningun tag agregado o es muy personalizado, textos, curves etc..."),
    ('GND', "geometry node", "Tu prop contiene nodos de geometry nodes"),
    ('GRA', "grabable", "Tu prop puede ser sostenido por un personaje, uso comun. Un lapiz, una pocion, etc..."),
    ('2D', "2d", "Tu prop es un objeto 2D, como un plano con una imagen, o un objeto de tipo 'IMAGE'"),
]

PROPS_FOLDER_PATH = ""


def collections_enum_items(self, context):
    items = []
    for col in bpy.data.collections:
        items.append((col.name, col.name, ""))
    return items


def gather_collection_data(collection):
    """Reúne todos los datablocks necesarios para exportar la colección limpia."""
    objects = list(collection.all_objects)  # Incluye objetos en subcolecciones
    meshes = [obj.data for obj in objects if obj.type == 'MESH' and obj.data]
    materials = []
    images = []

    # Materiales e imágenes usados por las mallas
    for mat in (m for mesh in meshes for m in mesh.materials if m):
        if mat not in materials:
            materials.append(mat)
        for node in getattr(mat.node_tree, "nodes", []):
            if node.type == 'TEX_IMAGE' and node.image and node.image not in images:
                images.append(node.image)

    datablocks = {
        "collections": [collection],
        "objects": objects,
        "meshes": meshes,
        "materials": materials,
        "images": images
    }

    return datablocks


def export_collection_clean(collection, filepath):
    data_to_save = gather_collection_data(collection)

    ids_to_save = {
        *data_to_save["collections"],
        *data_to_save["objects"],
        *data_to_save["meshes"],
        *data_to_save["materials"],
        *data_to_save["images"]
    }

    bpy.data.libraries.write(
        filepath,
        ids_to_save,
        fake_user=True,
        # Opcionales:
        # compress=True si quieres comprimir el .blend
        # path_remap="NONE" u otra opción si necesitas re-mapeo de rutas
    )


def upload_to_dropbox(local_path, dropbox_path):
    import dropbox
    from dropbox.files import WriteMode
    dbx = get_dbx()
    with open(local_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=WriteMode("overwrite"))


class PROPS_OT_DropBoxExportCollection(bpy.types.Operator):
    bl_idname = "prop.collab_export"
    bl_label = "Export"
    bl_description = "Exporta la colección seleccionada como un archivo limpio a Dropbox"

    def execute(self, context):
        scene = context.scene
        import dropbox

        collection = scene.all_collections
        if not collection:
            self.report({'ERROR'}, "No hay colección seleccionada!")
            return {'CANCELLED'}

        if not scene.prop_idname.strip():
            self.report(
                {'ERROR'}, "Falta asignar un ID al prop (prop_idname)!")
            return {'CANCELLED'}

        if not scene.prop_filename.strip():
            self.report({'ERROR'}, "Falta asignar el nombre al prop!")
            return {'CANCELLED'}

        if not scene.prop_preview_tex:
            self.report({'ERROR'}, "Falta preview!")
            return {'CANCELLED'}
        if not scene.prop_preview_tex:
            self.report({'ERROR'}, "Falta preview!")
            return {'CANCELLED'}
        if not bool(scene.tags_props_enum):
            self.report({'ERROR'}, "Falta tags!")
            return {'CANCELLED'}

        prop_id = scene.prop_idname.strip()
        dbx = get_dbx()
        wm = context.window_manager
        
        json_filename = f"{prop_id}.json"
        try:
            wm.progress_begin(0, 100)
            wm.progress_update(25)
            existing_files = dbx.files_list_folder(PROPS_FOLDER_PATH).entries
            for f in existing_files:
                if isinstance(f, dropbox.files.FileMetadata) and f.name.lower() == json_filename.lower():
                    self.report(
                        {'ERROR'}, f"Ya existe un prop con el ID '{prop_id}' en Dropbox")
                    return {'CANCELLED'}
        except dropbox.exceptions.ApiError as e:
            self.report({'ERROR'}, f"No se pudo verificar en Dropbox: {e}")
            return {'CANCELLED'}
        
        wm.progress_update(50)
        temp_dir = get_temp_folder()
        base_name = scene.prop_idname.strip()

        blend_path = temp_dir / f"{base_name}.blend"
        json_path = temp_dir / f"{base_name}.json"
        png_path = temp_dir / f"{base_name}.png"

        try:
            # 1. Exportar el blend limpio
            export_collection_clean(collection, str(blend_path))

            # 2. Guardar preview
            if scene.prop_preview_tex and scene.prop_preview_tex.image:
                scene.prop_preview_tex.image.save_render(
                    filepath=str(png_path))
            else:
                self.report({'WARNING'}, "No se encontró imagen de preview")
                return {'CANCELLED'}

            # 3. Crear JSON
            selected_ids = set(scene.tags_props_enum)
            selected_labels = [label for id_, label,
                               desc in TAGS_PROPS if id_ in selected_ids]

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
            
            # 4. Subir a Dropbox (usando PROPS_FOLDER_PATH)
            dropbox_base_path = f"{PROPS_FOLDER_PATH}/{base_name}"
            upload_to_dropbox(str(blend_path), f"{dropbox_base_path}.blend")
            if png_path.exists():
                upload_to_dropbox(str(png_path), f"{dropbox_base_path}.png")
            upload_to_dropbox(str(json_path), f"{dropbox_base_path}.json")
            wm.progress_update(100)
            wm.progress_end()
            self.report(
                {'INFO'}, f"Prop '{base_name}' exportado a Dropbox correctamente")
            clear_all()

        except Exception as e: 
            self.report({'ERROR'}, f"Error al exportar: {e}")
            return {'CANCELLED'}
        finally:
            # Limpieza temporal
            for p in (blend_path, json_path, png_path):
                if p.exists():
                    try:
                        p.unlink()
                    except:
                        pass

        return {'FINISHED'}


class PROPS_OT_SetLayouterName(bpy.types.Operator):
    bl_idname = "prop.collaborator_layouter_name"
    bl_label = ""
    bl_description = "Usa tu nombre de layouter"

    def execute(self, context):
        prefs = get_user_preferences(bpy.context)
        if prefs:
            bpy.context.scene.collaborator_name = prefs.layouter_name
        return {'FINISHED'}


class PROPS_OT_DeleteTexture(bpy.types.Operator):
    bl_idname = "prop.collaborator_delete_texture"
    bl_label = ""
    bl_description = "Elimina la textura actual"

    def execute(self, context):
        scene = context.scene
        tex = scene.prop_preview_tex

        # 1. Eliminar archivo temporal
        import tempfile
        import os
        temp_png = os.path.join(tempfile.gettempdir(), "prop_preview.png")
        if os.path.exists(temp_png):
            try:
                os.remove(temp_png)
                self.report({'INFO'}, "Archivo temporal eliminado")
            except Exception as e:
                self.report(
                    {'WARNING'}, f"No se pudo eliminar el PNG temporal: {e}")

        # 2. Eliminar textura y su imagen de Blender
        if tex:
            if tex.image:
                bpy.data.images.remove(tex.image)
            bpy.data.textures.remove(tex)
            scene.prop_preview_tex = None
            self.report({'INFO'}, "Textura de preview eliminada")

        return {'FINISHED'}


def clear_all():
    scenes = bpy.data.scenes
    if "EXPORT_PREVIEW" in scenes:
        scenes.remove(scenes["EXPORT_PREVIEW"])

    scene = bpy.context.scene
    scene.all_collections = None
    scene.prop_idname = ""
    scene.prop_filename = ""
    scene.prop_description = ""
    scene.tags_props_enum = set()

    if assign_render_to_preview in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(assign_render_to_preview)


class PROPS_OT_SelectPreviewImage(bpy.types.Operator):
    bl_idname = "props.select_preview_image"
    bl_label = ""
    bl_description = "Selecciona una imagen para usar como preview del prop"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(
        default="*.png;*.jpg;",
        options={'HIDDEN'}
    )

    def execute(self, context):
        scene = context.scene
        path = Path(self.filepath)

        if not path.exists():
            self.report({'ERROR'}, "Archivo no encontrado")
            return {'CANCELLED'}

        try:
            img = bpy.data.images.load(str(path))
            tex = bpy.data.textures.new("PreviewTex", type='IMAGE')
            tex.image = img  # img es la bpy.data.images.load(...)
            tex.extension = 'EXTEND'
            scene.prop_preview_tex = tex  # PointerProperty al tipo Texture

            self.report({'INFO'}, f"Imagen '{path.name}' cargada")
        except Exception as e:
            self.report({'ERROR'}, f"No se pudo cargar la imagen: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# MODO FOTO

class PROPS_OT_PreviewMaker(bpy.types.Operator):
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


def import_export_preview_scene():
    addon_dir = Path(__file__).parent.parent
    blend_path = addon_dir / "resources" / "LayoutCompanionExport.blend"

    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        if "EXPORT_PREVIEW" in data_from.scenes:
            data_to.scenes.append("EXPORT_PREVIEW")
        else:
            print("ERROR: No se encontró la escena EXPORT_PREVIEW en", blend_path)
            return None

    return bpy.data.scenes.get("EXPORT_PREVIEW")


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


class DropboxCollabProperties(bpy.types.PropertyGroup):
    bpy.types.Scene.all_collections = bpy.props.PointerProperty(
        name="Collection",
        description="Selecciona la colección a exportar",
        type=bpy.types.Collection
    )
    bpy.types.Scene.prop_preview_tex = bpy.props.PointerProperty(
        name="Preview Texture",
        type=bpy.types.Texture
    )
    bpy.types.Scene.prop_idname = bpy.props.StringProperty(
        name="ID",
        description="El ID Oculto del prop (aqui podrias poner prefijos o sufijos en caso que exista otro prop con el mismo nombre)",
        default=""
    )
    bpy.types.Scene.prop_filename = bpy.props.StringProperty(
        name="Name",
        description="Nombre que tendrá el archivo al subirlo",
        default=""
    )
    bpy.types.Scene.prop_description = bpy.props.StringProperty(
        name="Description",
        description="Notas/indicaciones/tips para el prop",
        default="Prop listo para su uso!"
    )
    bpy.types.Scene.collaborator_name = bpy.props.StringProperty(
        name="Collaborator:",
        description="Nombre del colaborador",
        default=""
    )
    bpy.types.Scene.tags_fold = bpy.props.BoolProperty(
        name="Tags",
        default=False
    )

    bpy.types.Scene.tags_props_enum = bpy.props.EnumProperty(
        name="Tags",
        description="Elige los tags que caracterizan al prop",
        items=TAGS_PROPS,
        options={'ENUM_FLAG'},
        default=set()
    )
    bpy.types.Scene.prop_guideline = bpy.props.BoolProperty(
        name="Guidelines",
        default=False
    )


classes = (
    PROPS_OT_DropBoxExportCollection,
    PROPS_OT_SelectPreviewImage,
    PROPS_OT_SetLayouterName,
    PROPS_OT_DeleteTexture,
    PROPS_OT_PreviewMaker,
    DropboxCollabProperties
)


def register_dropbox_collaboration():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.dropbox_props = bpy.props.PointerProperty(
        type=DropboxCollabProperties)


def unregister_dropbox_collaboration():
    del bpy.types.Scene.dropbox_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
