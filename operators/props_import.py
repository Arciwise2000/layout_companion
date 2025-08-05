import os
import bpy
import bpy.utils.previews
from bpy.types import Operator
from bpy.props import EnumProperty
from mathutils import Vector
import dropbox

# Diccionario global de previews
preview_props = {}
addon_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def enum_previews_from_images(self, context):
    enum_items = []
    directory = os.path.join(addon_root, "previews")

    if not os.path.exists(directory):
        return [("NONE", "Sin imágenes", "", 0, 0)]  # Fallback

    pcoll = preview_collections.get("main")
    if not pcoll:
        pcoll = bpy.utils.previews.new()
        setattr(pcoll, "my_previews_dir", "")
        setattr(pcoll, "my_previews", [])
        preview_props["main"] = pcoll
        
    if not pcoll.my_previews or pcoll.my_previews_dir != directory:
        enum_items.clear()
        for i, filename in enumerate(os.listdir(directory)):
            if filename.lower().endswith(".png"):
                filepath = os.path.join(directory, filename)
                thumb = pcoll.get(filename)
                if not thumb:
                    thumb = pcoll.load(filename, filepath, 'IMAGE')
                enum_items.append((filename, filename, "", thumb.icon_id, i))
        pcoll.my_previews = enum_items
        pcoll.my_previews_dir = directory

    return pcoll.my_previews


def get_blend_and_collection(selected_name):
    name_base = os.path.splitext(selected_name)[0]
    blend_path = os.path.join(addon_root, "resources", name_base + ".blend")
    collection_name = name_base
    return blend_path, collection_name


def get_next_available_name(base="Collection"):
    existing_names = {coll.name for coll in bpy.data.collections}
    index = 1
    while True:
        candidate = f"{base}.{str(index).zfill(3)}"
        if candidate not in existing_names:
            return candidate
        index += 1


def import_selected_collection(selected_name):
    blend_path, collection_name = get_blend_and_collection(selected_name)
    scene = bpy.context.scene
    
    if not os.path.exists(blend_path):
        print(f"No se encontró el archivo: {blend_path}")
        return

    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        if collection_name in data_from.collections:
            data_to.collections = [collection_name]
                        
    if scene.resource_import_origin_camera:
        bpy.ops.resource.place_origin(origin_type="camera")
    else:
        bpy.ops.resource.place_origin(origin_type="cursor")
        
    for coll in data_to.collections:
        if coll and coll.name == collection_name:
            new_name = get_next_available_name(collection_name)
            coll.name = new_name
            print("2")
            
        print("3")
            
        bpy.context.view_layer.update()
        
        for obj in [o for o in coll.objects if o.parent is None]:
            obj.location = scene.cursor.location
            print("4")

        scene.collection.children.link(coll)
        print(f"Importado: {collection_name}")
        break

class PROP_OT_ImportSelected(Operator):
    bl_idname = "prop.import_selected"
    bl_label = "Import"
    bl_description = "Importa el prop seleccionado"

    def execute(self, context):
        #selected_name = context.window_manager.collection_preview_enum
        #import_selected_collection(selected_name)
        return {'FINISHED'}