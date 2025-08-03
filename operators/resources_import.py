import os
import bpy
import bpy.utils.previews
from bpy.types import Operator
from bpy.props import EnumProperty
from mathutils import Vector

# Diccionario global de previews
preview_collections = {}
addon_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def enum_previews_from_images(self, context):
    enum_items = []
    directory = os.path.join(addon_root, "previews")
    print(directory)
    
    

    if not os.path.exists(directory):
        print("Directorio no encontrado:", directory)
        return [("NONE", "Sin imágenes", "", 0, 0)]  # Fallback

    pcoll = preview_collections.get("main")
    if not pcoll:
        pcoll = bpy.utils.previews.new()
        setattr(pcoll, "my_previews_dir", "")
        setattr(pcoll, "my_previews", [])
        preview_collections["main"] = pcoll
    else:
        if not hasattr(pcoll, "my_previews_dir") or not hasattr(pcoll, "my_previews"):
            setattr(pcoll, "my_previews_dir", "")
            setattr(pcoll, "my_previews", [])


    if directory == pcoll.my_previews_dir:
        return pcoll.my_previews

    if directory and os.path.exists(directory):
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
    print(blend_path)
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

class RESOURCE_OT_ImportSelected(Operator):
    bl_idname = "resource.import_selected"
    bl_label = "Import"
    bl_description = "Importa el recurso seleccionado"

    def execute(self, context):
        selected_name = context.window_manager.collection_preview_enum
        print("-1")
        import_selected_collection(selected_name)
        return {'FINISHED'}


class RESOURCE_OT_place_origin(bpy.types.Operator):
    bl_idname = "resource.place_origin"
    bl_label = "Place Origin"
    bl_description = "Selecciona el tipo de origen en la que se posicionara el recurso Camera = Al frente de la camara, Cursor = En donde este colocado el 3D_Cursor"
    origin_type: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = bpy.context.scene
        
        if self.origin_type == "cursor":
            target_location = scene.cursor.location.copy()
            scene.resource_import_origin_cursor = True
            scene.resource_import_origin_camera = False
            
        elif self.origin_type == "camera":
            cam = context.scene.camera
            if not cam:
                self.report({'WARNING'}, "No hay cámara activa en la escena")
                return {'CANCELLED'}
            
            forward_vec = cam.matrix_world.to_quaternion() @ Vector((0, 0, -2))
            target_location = cam.location + forward_vec
            scene.resource_import_origin_cursor = False
            scene.resource_import_origin_camera = True
        else:
             target_location = scene.cursor.location.copy()

        # Actualiza el cursor 3D para importar en esa posición
        context.scene.cursor.location = target_location
        return {'FINISHED'}
