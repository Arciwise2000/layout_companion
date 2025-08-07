import bpy
import bpy.utils.previews
import os

def update_available_collections(self, context):
    available_collections = get_available_collections(self, context)
    self["name_collection_items"] = available_collections
    self.name_collection = available_collections[0][0]
    
def get_available_collections(self, context):
    if self.new_collection and os.path.isfile(bpy.path.abspath(self.new_collection)):
        try:
            with bpy.data.libraries.load(bpy.path.abspath(self.new_collection), link=False) as (data_from, data_to):
                items = [(col, col, "") for col in data_from.collections]
                items.reverse()
                if items:
                    return items
        except Exception as e:
            print(f"Error loading file: {e}")
    return [("NONE", "None", "No hay colecciones disponibles")]


def get_filtered_collections(self, context):
    filtered = [("NONE", "Empty", "Sin colección seleccionada")] 

    parent = bpy.data.collections.get("PERSONAJES")
    if parent:
        for child in parent.children:
            filtered.append((child.name, child.name, ""))

    return filtered


class UC_Updated_Character(bpy.types.PropertyGroup):
    collection_enum: bpy.props.EnumProperty(
        name="Collection",
        description=("Debe estar dentro del collection 'PERSONAJES'\n"
                     "Ejemplo: PERSONAJES>PERSONAJE_MALO\n"
                     "Y no: PERSONAJES>OTRO_COLLECTION>PERSONAJE_MALO"
                     ),
        items=get_filtered_collections,
        options={'SKIP_SAVE'}
    )
    new_collection: bpy.props.StringProperty(
        name="New Collection",
        description="Path to the new file",
        default="",
        subtype='FILE_PATH',
        update=update_available_collections,
        options={'SKIP_SAVE'}
    )
    name_collection: bpy.props.EnumProperty(
        name="Name Collection",
        description="Collections available in the selected .blend file",
        items=get_available_collections,
        options={'SKIP_SAVE'}
    )

class UC_Operator_Updated_Character(bpy.types.Operator):
    bl_idname = "mesh.append_and_replace"
    bl_label = "Update Character"
    bl_description = "Actualiza el personaje seleccionado con su nueva versión, recuerde usar el mismo nombre de colección"

    @classmethod
    def poll(cls, context):
        return bool(context.window_manager.uc_updated_character.name_collection)

    def execute(self, context):
        props = context.window_manager.uc_updated_character
        collections = bpy.data.collections
        parent_file = props.new_collection

        name_cl = ""
        cl_cont: int = 0
        for c in collections:
            if c.name in props.collection_enum:
                cl_cont += 1
        if bpy.data.collections.get(props.name_collection):
            name_cl = props.name_collection + f".{cl_cont:003}"
        else:
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

        personajes_collection = bpy.data.collections.get("PERSONAJES")
        if not personajes_collection:
            personajes_collection = bpy.data.collections.new("PERSONAJES")
            bpy.context.scene.collection.children.link(personajes_collection)

        imported_collection = bpy.data.collections.get(name_cl)

        if imported_collection:
            if imported_collection.name not in [c.name for c in personajes_collection.children]:
                personajes_collection.children.link(imported_collection)
            else:
                print(f"La colección '{imported_collection.name}' ya está en 'PERSONAJES'.")

            old_collection = bpy.data.collections.get(props.collection_enum)

            old_rig = None
            if old_collection:
                for obj in old_collection.objects:
                    if obj.type == 'ARMATURE' and obj.parent is None:
                        old_rig = obj
                        break

            new_rig = None
            for obj in imported_collection.objects:
                if obj.type == 'ARMATURE' and obj.parent is None:
                    new_rig = obj
                    break

            if old_rig and new_rig:
                if hasattr(old_rig, "animation_data") and old_rig.animation_data:
                    if not new_rig.animation_data:
                        new_rig.animation_data_create()
                    new_rig.animation_data.action = old_rig.animation_data.action
                    if hasattr(old_rig.animation_data.action, "slots"):
                        new_rig.animation_data.action_slot = old_rig.animation_data.action.slots[0]

                # Copiar la matriz de transformación
                new_rig.matrix_world = old_rig.matrix_world

                if new_rig.animation_data and new_rig.animation_data.action:
                    action = new_rig.animation_data.action
                    for fcurve in list(action.fcurves):
                        if not fcurve.data_path.startswith("pose.bones"):
                            action.fcurves.remove(fcurve)

                bpy.context.view_layer.objects.active = new_rig
                new_rig.select_set(True)
                
                if new_rig.type == 'ARMATURE':
                    try:
                        bpy.ops.object.mode_set(mode='POSE')
                        
                        # Copy bone properties
                        for new_bone in new_rig.pose.bones:
                            for old_bone in old_rig.pose.bones:
                                if new_bone.name == old_bone.name:
                                    new_bone.rotation_mode = old_bone.rotation_mode
                        
                        bpy.ops.object.mode_set(mode='OBJECT')
                    except:
                        self.report({'WARNING'}, "Could not enter pose mode")

                bpy.ops.object.transforms_to_deltas(mode='ALL')

            if old_collection:
                for obj in old_collection.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.collections.remove(old_collection)

            imported_collection.name = props.collection_enum
        else:
            self.report({'WARNING'}, f"Collection '{collection_name}' not found after import.")

        props.new_collection = ""

        return {"FINISHED"}
    
    
    
    
def register_props():
    bpy.types.WindowManager.uc_updated_character = bpy.props.PointerProperty(
        type=UC_Updated_Character,
        options={'SKIP_SAVE'}
    )

def unregister_props():
    del bpy.types.WindowManager.uc_updated_character
