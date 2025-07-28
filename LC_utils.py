import os
import bpy

def add_decimate_modifier():
    """Adds a Decimate modifier to the selected object."""
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        return False
    
    last_obj = None
    for obj in selected_objects:
        if obj.type == 'MESH':  # Only applicable to mesh objects
            if "Decimate" not in obj.modifiers:
                decimate_mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
                decimate_mod.ratio = 0.9
        
        last_obj = obj
    
    if last_obj:
        bpy.context.view_layer.objects.active = last_obj
        for area in bpy.context.window.screen.areas:
            if area.type == 'PROPERTIES':
                for space in area.spaces:
                    if space.type == 'PROPERTIES':
                        space.context = 'MODIFIER'
                        break
    return True


def is_any_object_visible_in_render(collection_name):
    collection = is_collection_exist(collection_name)
    if not collection:
        return False
    
    if collection.hide_render == False:
        return True
    
    for obj in collection.objects:
        if obj.hide_render == False:
            return True
    
    for sub_col in collection.children:
        if is_any_object_visible_in_render(sub_col):
            return True
    
    return False

def is_collection_exist(collection_name):
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        return None
    
    return collection

def file_exists_in_blend_directory(filename: str) -> bool:
    blend_path = bpy.data.filepath

    if not blend_path:
        return False

    blend_dir = os.path.dirname(blend_path)
    target_path = os.path.join(blend_dir, filename)
    return os.path.exists(target_path)

def get_icon_by_vertices(vertices):
    if vertices > 100000:
        return "STRIP_COLOR_01", "Geometria con demasiados poligonos, altamente recomendable NO usar"
    elif vertices > 60000:
        return "STRIP_COLOR_02", "Considera agregar un decimate o usar otro prop"
    elif vertices > 30000:
        return "STRIP_COLOR_03", "Geometria Aceptable"
    elif vertices > 10000:
        return "STRIP_COLOR_04","Geometria Perfecta!"
    else:
        return "STRIP_COLOR_05","Geometria Perfecta!"
    