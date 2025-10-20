import os
import bpy

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
        return "STRIP_COLOR_01", "Geometria con demasiados poligonos, altamente recomendable NO usar (NO aplicarle keys de animacion)"
    elif vertices > 60000:
        return "STRIP_COLOR_02", "Considera agregar un decimate o usar otro prop (NO aplicarle keys de animacion)"
    elif vertices > 30000:
        return "STRIP_COLOR_03", "Geometria Aceptable"
    elif vertices > 10000:
        return "STRIP_COLOR_04","Geometria Perfecta!"
    else:
        return "STRIP_COLOR_05","Geometria Perfecta!"

def get_icon_by_leght(frames):
    if frames >= 960:
        return "STRIP_COLOR_01", "Larga duracion! Recomendable dividir"
    elif frames > 360:
        return "STRIP_COLOR_04", "Excelente duracion!"
    elif frames > 240:
        return "STRIP_COLOR_03","Corta duracion! Recomendable extender"
    else:
        return "STRIP_COLOR_01","Demasiado corto! Obligatorio extender"

def get_all_objects_recursive(collection):
        
    objects = list(collection.objects)
    for subcol in collection.children:
        objects.extend(get_all_objects_recursive(subcol))
    return objects

def check_emitters_in_collection():
    collection = is_collection_exist("EFECTOS")
    
    if not collection:
        return False
    
    all_objects = get_all_objects_recursive(collection)
    
    total = len(all_objects)
    if total == 0:
        return False
    
    for obj in all_objects:
        for mod in obj.modifiers:
            if mod.type == 'PARTICLE_SYSTEM':
                psys = mod.particle_system
                settings = psys.settings

                if settings.type != 'EMITTER':
                    continue

                cache = psys.point_cache
                if not cache.is_baked:
                    return True
                
    return False


def check_collections_disable(main_coll_name):    
    main_collection = bpy.data.collections.get(main_coll_name)
    
    if is_collection_exist(main_coll_name) is None:
        return False
    
    view_layer = bpy.context.view_layer
    
    def get_layer_collection(layer_coll, name):
        if layer_coll.name == name:
            return layer_coll
        for child in layer_coll.children:
            result = get_layer_collection(child, name)
            if result:
                return result
        return None
    
    main_layer_coll = get_layer_collection(view_layer.layer_collection, main_coll_name)
    
    if not main_layer_coll:
        return False
    
    for child_layer_coll in main_layer_coll.children:
        if child_layer_coll.exclude:
            return False

    return True