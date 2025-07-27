import bpy
import bpy.utils.previews
import os

def update_available_collections(self, context):
    """Actualizar las colecciones disponibles al cambiar el archivo .blend"""
    # Obtener las colecciones disponibles llamando a get_available_collections
    available_collections = get_available_collections(self, context)
    
    # Actualizar dinámicamente los elementos de la propiedad EnumProperty
    self["name_collection_items"] = available_collections
    self.name_collection = available_collections[0][0] if available_collections else ""
    
def get_available_collections(self, context):
    """Generar dinámicamente las colecciones disponibles en el archivo .blend"""
    if self.new_collection and os.path.isfile(bpy.path.abspath(self.new_collection)):
        try:
            with bpy.data.libraries.load(bpy.path.abspath(self.new_collection), link=False) as (data_from, data_to):
                items = [(col, col, "") for col in data_from.collections]
                items.reverse()
                return items
        except Exception as e:
            print(f"Error loading file: {e}")
    return []

def get_filtered_collections(self, context):
    filtered = []
    parent = bpy.data.collections.get("PERSONAJES")
    if parent:
        for child in parent.children:
            filtered.append((child.name, child.name, ""))
            print("Filtradas:", [col.name for col in parent.children])
    return filtered

class UC_Updated_Character(bpy.types.PropertyGroup):

    collection_enum: bpy.props.EnumProperty(
    name="collection",
    description="Debe estar dentro del collection 'PERSONAJES'",
    items=get_filtered_collections
    )
    
    new_collection: bpy.props.StringProperty(
        name="New Collection",
        description="Path to the new file",
        default="",
        subtype='FILE_PATH',
        update=update_available_collections,
    )
    
    name_collection: bpy.props.EnumProperty(
        name="Name Collection",
        description="Collections available in the selected .blend file",
        items=get_available_collections,
    )

class UC_Operator_Updated_Character(bpy.types.Operator):
    bl_idname = "mesh.append_and_replace"
    bl_label = "Update Character"
    bl_description = "Actualiza el personaje seleccionado con su nueva versión, recuerde usar el mismo nombre de colección"

    @classmethod
    def poll(cls, context):
        props = context.scene.uc_updated_character
        return bool(props.name_collection)


    def execute(self, context):
        props = context.scene.uc_updated_character
        collections = bpy.data.collections
        parent_file = props.new_collection
        
        name_cl = ""
        cl_cont : int = 0 
        for c in collections : 
            if c.name in props.collection_enum :
                cl_cont += 1
        if bpy.data.collections.get(props.name_collection) :
            name_cl = props.name_collection+f".{cl_cont:003}"
        else :
            name_cl = props.name_collection
        
        collection_name = props.name_collection
        directory_path = bpy.path.abspath(parent_file) + r'\Collection'

        try:
            result = bpy.ops.wm.append(
                directory=directory_path,
                filename=collection_name,
                link=False
            )
            print(f"Append Result: {result}")
        except Exception as e:
            print(f"Error appending collection: {e}")
        
        # Guardar la colección importada en una variable
        imported_collection = bpy.data.collections.get(name_cl)

        if imported_collection:
            
            old_collection = bpy.data.collections.get(props.collection_enum)
            parent_collection = old_collection

            if parent_collection:
                # Vincular la colección importada a la colección padre
                parent_collection.children.link(imported_collection)
            
            old_rig = None
            if old_collection:
                for obj in old_collection.objects:
                    if obj.type == 'ARMATURE':
                        if obj.parent == None:
                            old_rig = obj
                            break
            new_rig = None
            for obj in imported_collection.objects:
                if obj.type == 'ARMATURE':
                    if obj.parent == None:
                        new_rig = obj
                        break
            
            if old_rig and new_rig:
                

                # Transferir manualmente los datos de animación
                if hasattr(old_rig, "animation_data") and old_rig.animation_data:
                    # Crear datos de animación en new_rig si no existen
                    if not new_rig.animation_data:
                        new_rig.animation_data_create()

                    # Transferir la acción activa
                    new_rig.animation_data.action = old_rig.animation_data.action
                    new_rig.animation_data.action_slot = old_rig.animation_data.action.slots[0]
                    
                    
                # Copiar la matriz de transformación
                new_rig.matrix_world = old_rig.matrix_world
                
                if new_rig.animation_data and new_rig.animation_data.action:
                    action = new_rig.animation_data.action
                    # Iterar sobre las curvas de animación
                    for fcurve in list(action.fcurves):
                        # Verificar si la curva está asociada al objeto (no a los huesos)
                        if not fcurve.data_path.startswith("pose.bones"):
                            action.fcurves.remove(fcurve)  # Eliminar la curva de animación

            # Cambiar al modo POSE
            bpy.ops.object.mode_set(mode='POSE')

            # Iterar sobre los huesos de new_rig y old_rig
            for new_bone in new_rig.pose.bones:
                for old_bone in old_rig.pose.bones:
                    if new_bone.name == old_bone.name:
                        # Transferir el modo de rotación
                        new_bone.rotation_mode = old_bone.rotation_mode
                        

            # Cambiar de nuevo al modo OBJECT
            bpy.ops.object.mode_set(mode='OBJECT')
            
            if old_collection:
                # Seleccionar todos los objetos de la colección antigua
                for obj in old_collection.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)  # Eliminar los objetos de la colección

                # Eliminar la colección antigua
                bpy.data.collections.remove(old_collection)
            
            if new_rig:
                bpy.context.view_layer.objects.active = new_rig 
                new_rig.select_set(True)
                bpy.ops.object.transforms_to_deltas(mode='ALL')

            
            
            imported_collection.name = props.collection_enum
        else:
            self.report({'WARNING'}, f"Collection '{collection_name}' not found after import.")
        
        return {"FINISHED"}