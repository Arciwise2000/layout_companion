import bpy
from bpy.props import BoolProperty


# Scene properties
bpy.types.Scene.render_settings_fold = BoolProperty(
    name="Show Render Settings",
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
    name="Show Render Settings",
    default=False
)
bpy.types.Scene.props_settings_fold = BoolProperty(
    name="Show Prop Settings",
    default=False
)
bpy.types.Scene.show_advance_prop_settings = BoolProperty(
    name="Prop Cleaner Settings",
    default=False
)

bpy.types.Scene.show_prop_helpInfo = BoolProperty(
    name="Check Prop Verts. Status",
    default=False
)
bpy.types.Scene.characters_fold = BoolProperty(
    name="Characters Settings",
    default=False
)
bpy.types.Scene.show_character_list = BoolProperty(
    name="",
    default=False
)
bpy.types.Scene.extras_fold = BoolProperty(
    name="Extras Settings",
    default=False
)
bpy.types.Scene.remove_empties = BoolProperty(
    name="Remove Emptys",
    description="Elimina todos los emptys",
    default=True
)
bpy.types.Scene.remove_doubles = BoolProperty(
    name="Remove Double Vertices",
    description="Combina los vertices duplicados",
    default=True
)
bpy.types.Scene.add_in_collection = BoolProperty(
    name="Create Collection",
    description="Anida las partes del prop a un nuevo Collection",
    default=True
)
bpy.types.Scene.mergeObjects = BoolProperty(
    name="Merge Meshes",
    description="Junta todas las partes en una sola",
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

def unregister_props():
    del bpy.types.WindowManager.show_characterUpdater

