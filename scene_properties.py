import bpy
from bpy.props import BoolProperty
from bpy.props import EnumProperty

# Scene properties
bpy.types.Scene.render_settings_fold = BoolProperty(
    name="Show render settings",
    default=False
)
bpy.types.Scene.show_render_status = BoolProperty(
    name="",
    default=True
)
bpy.types.Scene.show_leght_info = BoolProperty(
    name="",
    default=True
)
bpy.types.Scene.import_settings_fold = BoolProperty(
    name="Show import settings",
    default=False
)
bpy.types.Scene.props_settings_fold = BoolProperty(
    name="Show prop settings",
    default=False
)
bpy.types.Scene.show_advance_prop_settings = BoolProperty(
    name="Prop cleaner settings",
    default=False
)

bpy.types.Scene.show_prop_helpInfo = BoolProperty(
    name="Check prop vertices status",
    default=False
)
bpy.types.Scene.characters_fold = BoolProperty(
    name="Characters settings",
    default=False
)
bpy.types.Scene.show_character_list = BoolProperty(
    name="",
    default=False
)
bpy.types.Scene.lock_character_loc = BoolProperty(
    name="Loc",
    description="Bloque los ejes de locacion del personaje seleccionado",
    default=True
)
bpy.types.Scene.lock_character_rot = BoolProperty(
    name="Rot",
    description="Bloque los ejes de rotacion del personaje seleccionado",
    default=True
)
bpy.types.Scene.lock_character_scale = BoolProperty(
    name="Scale",
    description="Bloque los ejes de escala del personaje seleccionado",
    default=True
)

bpy.types.Scene.extras_fold = BoolProperty(
    name="Extras settings",
    default=False
)
bpy.types.Scene.remove_empties = BoolProperty(
    name="Remove emptys",
    description="Elimina todos los emptys y deja solo los objetos",
    default=True
)
bpy.types.Scene.remove_doubles = BoolProperty(
    name="Remove double vertices",
    description="Combina los vertices duplicados",
    default=True
)
bpy.types.Scene.add_in_collection = BoolProperty(
    name="Create collection",
    description="Anida las partes del prop a un nuevo Collection",
    default=True
)
bpy.types.Scene.mergeObjects = BoolProperty(
    name="Merge meshes",
    description="Junta todos los objetos en una solo",
    default=False
)
bpy.types.Scene.only_selected_objects = BoolProperty(
    name="Only selected objects",
    description="Solo limpia los objetos seleccionados, en caso contrario limpiara todos los objetos dentro de un empty; o si no tiene empty, del collection",
    default=False
)

bpy.types.Scene.resource_import_origin_cursor = BoolProperty(
    name="",
    description="Importa el recurso en el 3D Cursor",
    default=True
)
bpy.types.Scene.resource_import_origin_camera = BoolProperty(
    name="",
    description="Importa el recurso adelante de la camara",
    default=False
)

#NO PERDURABLE PROPERTIES
def register_props():
    bpy.types.WindowManager.show_characterUpdater = bpy.props.BoolProperty(
        name="",
        default=False,
        description="Mostrar opciones de actualización de personaje",
        options={'SKIP_SAVE'}
    )
    if not hasattr(bpy.types.Scene, "resource_tabs"):
            bpy.types.Scene.resource_tabs = EnumProperty(
                name="Tabs",
                description="Selecciona la fuente de recursos",
                items=[
                    ('RESOURCES', "Resources", "Mostrar recursos locales"),
                    ('DROPBOX PROPS', "Dropbox props", "Mostrar props colaborativos"),
                ],
                default='RESOURCES'
            )



def unregister_props():
    del bpy.types.WindowManager.show_characterUpdater

