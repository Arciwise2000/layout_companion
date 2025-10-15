import os
import bpy
import bpy.utils.previews
from bpy.types import Operator
from mathutils import Vector
from bpy.props import EnumProperty, StringProperty

from .. import addon_dir


preview_collections = {}  # Diccionario global de previews


def enum_previews_from_directory(identifier, subfolder):

    def _enum_items(self, context):
        enum_items = []
        directory = os.path.join(addon_dir, "local_resources", subfolder)

        if not os.path.exists(directory):
            return [("NONE", "Sin imágenes", "", 0, 0)]  # fallback

        pcoll = preview_collections.get(identifier)
        if not pcoll:
            pcoll = bpy.utils.previews.new()
            setattr(pcoll, "my_previews_dir", "")
            setattr(pcoll, "my_previews", [])
            preview_collections[identifier] = pcoll

        if not pcoll.my_previews or pcoll.my_previews_dir != directory:
            enum_items.clear()
            i = 0
            for filename in os.listdir(directory):
                if filename.lower().endswith(".png"):
                    filepath = os.path.join(directory, filename)
                    thumb = pcoll.get(filename)
                    if not thumb:
                        thumb = pcoll.load(filename, filepath, 'IMAGE')
                    enum_items.append((filename, filename, "", thumb.icon_id, i))
                    i += 1

            pcoll.my_previews = enum_items
            pcoll.my_previews_dir = directory

        return pcoll.my_previews

    return _enum_items



def get_blend_and_collection(selected_name, category):
    """Obtiene ruta y nombre de colección basados en el enum elegido."""
    name_base = os.path.splitext(selected_name)[0]
    blend_path = os.path.join(addon_dir, "local_resources", category, name_base + ".blend")
    return blend_path, name_base


def get_next_available_name(base="Collection"):
    existing_names = {coll.name for coll in bpy.data.collections}
    index = 1
    while True:
        candidate = f"{base}.{str(index).zfill(3)}"
        if candidate not in existing_names:
            return candidate
        index += 1


def import_selected_collection(selected_name, category):
    blend_path, collection_name = get_blend_and_collection(selected_name, category)
    scene = bpy.context.scene

    if not os.path.exists(blend_path):
        print(f"No se encontró el archivo: {blend_path}")
        return

    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        source_scene_name = data_from.scenes[0] if data_from.scenes else None

        if collection_name in data_from.collections:
            data_to.collections = [collection_name]
        else:
            print(f"No se encontró la colección '{collection_name}' en el archivo externo.")
            return

    if scene.resource_import_origin_camera:
        bpy.ops.resource.place_origin(origin_type="camera")

    parent_collection = bpy.data.collections.get(source_scene_name)

    for coll in data_to.collections:
        if coll and coll.name == collection_name:
            new_name = get_next_available_name(collection_name)
            coll.name = new_name

            for obj in [o for o in coll.objects if o.parent is None]:
                obj.location = scene.cursor.location

            if parent_collection:
                parent_collection.children.link(coll)
            else:
                scene.collection.children.link(coll)

            bpy.context.view_layer.update()

            # ---- helpers ----
            def iter_collections_recursive(c):
                yield c
                for child in c.children:
                    yield from iter_collections_recursive(child)

            def disable_layer_collection_for_collection(layer_coll, target_coll):
                if layer_coll.collection is target_coll:
                    layer_coll.exclude = True
                    
                for child in layer_coll.children:
                    if disable_layer_collection_for_collection(child, target_coll):
                        return True
                return False
            # -----------------
            found_any = False
            for subcoll in iter_collections_recursive(coll):
                if subcoll.name.lower().startswith("proxy"):
                    found_any = True
                    ok = disable_layer_collection_for_collection(bpy.context.view_layer.layer_collection, subcoll)
                    if ok:
                        print(f"Colección 'Proxy' (data: {subcoll}) desactivada en el View Layer")
                    else:
                        print(f"No se encontró LayerCollection para la colección 'Proxy' (data: {subcoll})")

            if not found_any:
                pass

            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()

            print(f"Importado '{collection_name}'")
            break


class RESOURCE_OT_ImportSelected(Operator):
    bl_idname = "resource.import_selected"
    bl_label = "Import"
    bl_description = "Importa el recurso seleccionado"

    def execute(self, context):
        scene = context.scene
        category = "effects"
        if scene.resource_tabs == 'RESOURCES':
            selected_name = context.window_manager.res_effects_preview_enum
        elif scene.resource_tabs == 'MANIQUIES':
            selected_name = context.window_manager.res_maniques_preview_enum
            category = "maniquies"
        else:
            self.report({'ERROR'}, "No se reconoce la categoría")
            return {'CANCELLED'}

        import_selected_collection(selected_name, category)
        return {'FINISHED'}


class RESOURCE_OT_place_origin(Operator):
    bl_idname = "resource.place_origin"
    bl_label = "Place Origin"
    bl_description = "Selecciona dónde colocar el recurso (Camera o Cursor)."

    origin_type: StringProperty()

    def execute(self, context):
        scene = context.scene
        if self.origin_type == "camera":
            cam = scene.camera
            if not cam:
                self.report({'WARNING'}, "No hay cámara activa en la escena")
                return {'CANCELLED'}

            cam_world_pos = cam.matrix_world.translation
            forward_vec = cam.matrix_world.to_quaternion() @ Vector((0, 0, -2))
            target_location = cam_world_pos + forward_vec

            scene.resource_import_origin_cursor = False
            scene.resource_import_origin_camera = True
        else:
            target_location = scene.cursor.location.copy()
            scene.resource_import_origin_cursor = True
            scene.resource_import_origin_camera = False

        scene.cursor.location = target_location
        return {'FINISHED'}


classes = (
    RESOURCE_OT_ImportSelected,
    RESOURCE_OT_place_origin,
)


def register_resource_import():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.res_effects_preview_enum = EnumProperty(
        name="Efectos",
        items=enum_previews_from_directory("RESOURCES", "effects")
    )
    bpy.types.WindowManager.res_maniques_preview_enum = EnumProperty(
        name="Maniquíes",
        items=enum_previews_from_directory("MANIQUIES", "maniquies")
    )


def unregister_resource_import():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    del bpy.types.WindowManager.res_effects_preview_enum
    del bpy.types.WindowManager.res_maniques_preview_enum