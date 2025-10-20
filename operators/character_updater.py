import bpy
import os


def get_filtered_collections(self, context):
    filtered = [("NONE", "Empty", "Sin colección seleccionada")] 

    parent = bpy.data.collections.get("PERSONAJES")
    if parent:
        for child in parent.children:
            filtered.append((child.name, child.name, ""))

    return filtered

class UC_Props(bpy.types.PropertyGroup):
    old_collection: bpy.props.EnumProperty(
        name="Old rig:",
        description="Selecciona el rig actual en la escena",
        items=get_filtered_collections
    )

    def update_new_blend(self, context):
        if not self.new_blend_path or not os.path.exists(bpy.path.abspath(self.new_blend_path)):
            self.new_collection = ""
            return

        blend_path = bpy.path.abspath(self.new_blend_path)
        old_name = self.old_collection.name if self.old_collection else None
        collections = []

        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            collections = list(data_from.collections)

        # Actualizar Enum
        enum_items = [(col, col, "") for col in collections]
        if old_name and old_name in collections:
            self.new_collection = old_name
        elif collections:
            self.new_collection = collections[0]
        else:
            try:
                self.property_unset("new_collection")
            except Exception:
                pass

    new_blend_path: bpy.props.StringProperty(
        name="New rig:",
        subtype='FILE_PATH',
        description="Ruta al archivo .blend que contiene el rig nuevo",
        update=update_new_blend  # 👈 importante
    )

    new_collection: bpy.props.EnumProperty(
        name="Collection:",
        description="Selecciona la colección del rig nuevo",
        items=lambda self, context: self.get_collections_from_blend(context)
    )

    def get_collections_from_blend(self, context):
        """Escanea el archivo .blend y devuelve sus colecciones"""
        items = []
        if not self.new_blend_path or not os.path.exists(bpy.path.abspath(self.new_blend_path)):
            return items

        blend_path = bpy.path.abspath(self.new_blend_path)
        from bpy import path as bpath
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            for col in data_from.collections:
                items.append((col, col, ""))
        return items



class UC_Operator_Updated_Character(bpy.types.Operator):
    """Actualiza un personaje reemplazando su colección por una nueva versión."""
    bl_idname = "mesh.append_and_replace"
    bl_label = "Actualizar Personaje"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.window_manager.uc_updated_character
        old_col = bpy.data.collections.get(props.old_collection)
        blend_path = bpy.path.abspath(props.new_blend_path)
        new_col_name = props.new_collection

        if not old_col or not blend_path or not new_col_name:
            self.report({'ERROR'}, "Faltan datos (rig viejo, archivo o colección nueva)")
            return {'CANCELLED'}

        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            if new_col_name in data_from.collections:
                data_to.collections = [new_col_name]
        new_collection = data_to.collections[0]
        
        context.scene.collection.children.link(new_collection)
        
        old_rig = find_armature_in_collection(old_col)
        new_rig = find_armature_in_collection(new_collection)
        
        if old_rig and new_rig:
            new_rig.matrix_world = old_rig.matrix_world.copy()
            
            new_rig.lock_location = old_rig.lock_location
            new_rig.lock_rotation = old_rig.lock_rotation
            new_rig.lock_scale = old_rig.lock_scale
            
            old_action = None
            old_slot = None
            if old_rig.animation_data:
                old_action = old_rig.animation_data.action
                old_slot = getattr(old_rig.animation_data, "action_slot", None)
                
            # === RENOMBRAR Y OCULTAR EL RIG VIEJO ===
            old_col.name = old_col.name + "_old"
            layer_col = get_layer_collection_for_collection(context.view_layer.layer_collection, old_col)
            if layer_col:
                layer_col.exclude = True
            else:
                self.report({'WARNING'}, f"No se encontró LayerCollection para {old_col.name}")
                
                
            new_rig.animation_data_create()
            if old_action:
                new_rig.animation_data.action = old_action
            if old_slot:
                new_rig.animation_data.action_slot = old_slot

        personajes_col = bpy.data.collections.get("PERSONAJES")
        if personajes_col:
            personajes_col.children.link(new_collection)
            context.scene.collection.children.unlink(new_collection)
            
            
        clear_uc_props(context)
        self.report({'INFO'}, f"Rig actualizado: {new_col_name}")
        return {'FINISHED'}
    


def find_armature_in_collection(collection):
    """Busca recursivamente un objeto tipo ARMATURE dentro de la colección y sus hijos."""
    for obj in collection.objects:
        if obj.type == 'ARMATURE':
            return obj
    for child_col in collection.children:
        armature = find_armature_in_collection(child_col)
        if armature:
            return armature
    return None


def get_layer_collection_for_collection(layer_collection, collection):
    if layer_collection.collection == collection:
        return layer_collection
    for child in layer_collection.children:
        found = get_layer_collection_for_collection(child, collection)
        if found:
            return found
    return None

def clear_uc_props(context):
    """Limpia todos los valores de UC_Props a su estado inicial, de forma segura."""
    props = context.window_manager.uc_updated_character
    props.old_collection = "NONE"
    props.new_blend_path = ""

    enum_items = props.get_collections_from_blend(context)
    if enum_items and enum_items[0][0]:
        props.new_collection = enum_items[0][0]
    else:
        try:
            props.property_unset("new_collection")
        except Exception:
            pass

classes = (  
    UC_Props,
    UC_Operator_Updated_Character)

def register_update_character():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.uc_updated_character = bpy.props.PointerProperty(type=UC_Props)


def unregister_update_character():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.WindowManager.uc_updated_character
