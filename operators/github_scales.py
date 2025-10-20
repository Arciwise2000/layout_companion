import bpy
import requests
import json
from bpy.props import CollectionProperty, IntProperty, StringProperty,FloatProperty

GIST_URL = "https://arciwise2000.github.io/HornstrompScales/charactersData.json"
GISTMAP_URL = "https://arciwise2000.github.io/HornstrompScales/mapsData.json"


def fetch_data_from_url(url, key, property_group, scene_prop_name, item_name="name", item_value="scale"):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if key not in data:
            raise KeyError(f"Json script error (missing '{key}')")

        scene = bpy.context.scene

        if not hasattr(scene, scene_prop_name):
            bpy.types.Scene.__annotations__[scene_prop_name] = bpy.props.CollectionProperty(type=property_group)
            bpy.types.Scene.__annotations__[f"{scene_prop_name}_index"] = bpy.props.IntProperty(default=0)
            bpy.types.Scene.__annotations__[f"{scene_prop_name}_filter"] = bpy.props.StringProperty(name="Filter", default="")

        collection = getattr(scene, scene_prop_name)
        collection.clear()

        for entry in data[key]:
            try:
                item = collection.add()
                item.name = entry.get(item_name, "Unnamed")
                value = entry.get(item_value, None)
                if value is not None:
                    item.scale = float(value)
            except (KeyError, ValueError) as e:
                print(f"[WARN] Error cargando item: {str(e)}")

        return len(data[key])

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error de conexión: {str(e)}")
    except json.JSONDecodeError:
        raise RuntimeError("Error JSON: formato inválido")
    except Exception as e:
        raise RuntimeError(f"Error inesperado: {str(e)}")


class CharacterListItem(bpy.types.PropertyGroup):
    name: StringProperty(name="name")
    scale: FloatProperty(name="scale")
class MapListItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Map name")
    scale: FloatProperty(name="Map scale")


class CHARACTERS_UL_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='ARMATURE_DATA')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class MAPS_UL_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='MESH_GRID')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)



class SCALES_OT_GetCharactersList(bpy.types.Operator):
    bl_idname = "cloud.get_character_list"
    bl_label = "Get Character List"
    bl_description = "Busca las escalas de los personajes almacenados en la nube"

    def execute(self, context):
        try:
            count = fetch_data_from_url(
                url=GIST_URL,
                key="characters",
                property_group=CharacterListItem,
                scene_prop_name="character_list_items"
            )
            self.report({'INFO'}, f"{count} personajes cargados correctamente.")
            context.scene.show_settings.character_list = True
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}


class SCALES_OT_GetMapList(bpy.types.Operator):
    bl_idname = "cloud.get_map_list"
    bl_label = "Get Map List"
    bl_description = "Busca las escalas de los mapas almacenados en la nube"

    def execute(self, context):
        try:
            count = fetch_data_from_url(
                url=GISTMAP_URL,
                key="maps",
                property_group=MapListItem,
                scene_prop_name="map_list_items"
            )
            self.report({'INFO'}, f"{count} mapas cargados correctamente.")
            context.scene.show_settings.map_list = True
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}


class CHARACTER_OT_ApplyScaleToSelected(bpy.types.Operator):
    bl_idname = "character.apply_scale_to_selected"
    bl_label = "Apply Scale to Selected"
    bl_description = "Aplica la escala del personaje seleccionado al objeto activo"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                hasattr(context.scene, "character_list_items") and
                len(context.scene.character_list_items) > 0 and
                context.scene.character_list_index >= 0)

    def execute(self, context):
        scene = context.scene
        selected_character = scene.character_list_items[scene.character_list_index]
        obj = context.active_object

        obj.scale = (selected_character.scale,) * 3
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)

        loc = getattr(scene, "lock_character_loc", False)
        rot = getattr(scene, "lock_character_rot", False)
        scale = getattr(scene, "lock_character_scale", False)

        obj.lock_location = (loc, loc, loc)
        obj.lock_rotation = (rot, rot, rot)
        obj.lock_scale = (scale, scale, scale)

        self.report({'INFO'}, f"Escala {selected_character.scale} aplicada a {obj.name}")
        return {'FINISHED'}


class MAP_OT_ApplyScaleToSelected(bpy.types.Operator):
    bl_idname = "map.apply_scale_to_selected"
    bl_label = "Apply Scale to Map"
    bl_description = "Aplica la escala al mapa dentro del collection 'MAPA'"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (hasattr(context.scene, "map_list_items") and
                len(context.scene.map_list_items) > 0 and
                context.scene.map_list_index >= 0)

    def execute(self, context):
        scene = context.scene
        selected_map = scene.map_list_items[scene.map_list_index]

        mapa_collection = bpy.data.collections.get("MAPA")
        if mapa_collection is None:
            mapa_collection = bpy.data.collections.new("MAPA")
            bpy.context.scene.collection.children.link(mapa_collection)
            
        empty = next((obj for obj in mapa_collection.objects if obj.name == "MAPA_SCALE"), None)

        if empty:
            empty.scale = (selected_map.scale,) * 3
            empty.location = (0, 0, 0)
            self.report({'INFO'}, f"Escala {selected_map.scale} aplicada al empty existente 'MAPA_SCALE'.")
            return {'FINISHED'}
            
        def gather_objects_recursive(collection, result=None):
            if result is None:
                result = []

            if any(word.lower() in collection.name.lower() for word in ["instance", "instancia"]):
                return result
            if getattr(collection, "hide_render", False) or getattr(collection, "hide_viewport", False):
                return result
            if hasattr(collection, "hide_get") and collection.hide_get():
                return result

            for obj in collection.objects:
                if obj not in result:
                    result.append(obj)

            for sub_col in collection.children:
                gather_objects_recursive(sub_col, result)

            return result

        all_objects = gather_objects_recursive(mapa_collection)

        if not all_objects:
            self.report({'WARNING'}, "No se encontraron objetos dentro de la colección 'MAPA'.")
            return {'CANCELLED'}

        for obj in all_objects:
            if obj.type == 'MESH' and obj.modifiers:
                for mod in obj.modifiers:
                    if mod.type in {'ARRAY', 'CURVE'}:
                        try:
                            bpy.context.view_layer.objects.active = obj
                            obj.select_set(True)
                            bpy.ops.object.modifier_apply(modifier=mod.name)
                            print(f"[INFO] Modificador {mod.type} aplicado en objeto '{obj.name}'.")
                        except Exception as e:
                            print(f"[ERROR] No se pudo aplicar {mod.type} en '{obj.name}': {e}")

        center = (
            sum(obj.location.x for obj in all_objects) / len(all_objects),
            sum(obj.location.y for obj in all_objects) / len(all_objects),
            0.0
        )

        empty = bpy.data.objects.new("MAPA_SCALE", None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 20
        empty.location = center
        mapa_collection.objects.link(empty)
        for obj in all_objects:
            if obj.parent is None:
                obj.parent = empty
                obj.matrix_parent_inverse = empty.matrix_world.inverted()

        empty.scale = (selected_map.scale,) * 3
        empty.location = (0, 0, 0)

        self.report({'INFO'}, f"Escala {selected_map.scale} aplicada a la colección 'MAPA'.")
        return {'FINISHED'}


classes = (
    CharacterListItem,
    MapListItem,
    CHARACTERS_UL_List,
    MAPS_UL_List,
    SCALES_OT_GetCharactersList,
    SCALES_OT_GetMapList,
    CHARACTER_OT_ApplyScaleToSelected,
    MAP_OT_ApplyScaleToSelected
)


def register_character_list():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.character_list_items = CollectionProperty(type=CharacterListItem)
    bpy.types.Scene.character_list_index = IntProperty(default=0)
    bpy.types.Scene.character_list_filter = StringProperty(name="Filter", default="")

    bpy.types.Scene.map_list_items = CollectionProperty(type=MapListItem)
    bpy.types.Scene.map_list_index = IntProperty(default=0)
    bpy.types.Scene.map_list_filter = StringProperty(name="Filter", default="")
    

def unregister_character_list():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.character_list_items
    del bpy.types.Scene.character_list_index
    del bpy.types.Scene.character_list_filter

    del bpy.types.Scene.map_list_items
    del bpy.types.Scene.map_list_index
    del bpy.types.Scene.map_list_filter
