import bpy
import requests
import json
import threading

GIST_URL = "https://arciwise2000.github.io/HornstrompScales/charactersData.json"

class CLOUD_OT_GetNameList(bpy.types.Operator):
    bl_idname = "cloud.get_name_list"
    bl_label = "Get Character List"
    bl_description = "Busca las escalas de los personajes almacenados en la nube"
    def execute(self, context):
        thread = threading.Thread(target=self.fetch_character_list, args=(context,))
        thread.start()
        self.report({'INFO'}, "Loading character list...")
        return {'FINISHED'}

    def fetch_character_list(self, context):
        try:
            response = requests.get(GIST_URL)
            response.raise_for_status()
            data = response.json()

            if 'characters' not in data:
                self._report_error(context, "Json script error (empty 'characters')")
                return

            def update_ui():
                scene = context.scene

                if not hasattr(scene, "character_list_items"):
                    bpy.types.Scene.character_list_items = bpy.props.CollectionProperty(type=CharacterListItem)
                    bpy.types.Scene.character_list_index = bpy.props.IntProperty(default=0)
                    bpy.types.Scene.character_list_filter = bpy.props.StringProperty(name="Filter", default="")
                    scene.show_character_list = True
                else:
                    scene.show_character_list = True
                     
                scene.character_list_items.clear()

                for character in data['characters']:
                    try:
                        item = scene.character_list_items.add()
                        item.name = character['name']
                        item.scale = float(character['scale'])
                    except KeyError as e:
                        print(f"Error: {str(e)} Missing key in character data")
                    except ValueError:
                        print(f"Error: Invalid Scale {character.get('name', '?')}")

                self._report_info(context, f" {len(data['characters'])} Loaded Chracters")

            bpy.app.timers.register(update_ui, first_interval=0.1)

        except requests.exceptions.RequestException as e:
            self._report_error(context, f"Conexion error: {str(e)}")
        except json.JSONDecodeError:
            self._report_error(context, "JSON decode error: Invalid JSON format")
        except Exception as e:
            self._report_error(context, f"Error: {str(e)}")

    def _report_error(self, context, message):
        def report():
            self.report({'ERROR'}, message)
        bpy.app.timers.register(report, first_interval=0.1)

    def _report_info(self, context, message):
        def report():
            self.report({'INFO'}, message)
        bpy.app.timers.register(report, first_interval=0.1)
        
        
class CharacterListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="name")  # type: ignore
    scale: bpy.props.FloatProperty(name="scale")  # type: ignore
    
    
class CHARACTERS_UL_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='ARMATURE_DATA')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)