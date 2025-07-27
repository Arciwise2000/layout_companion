import bpy

# Scene properties
bpy.types.Scene.render_settings_fold = bpy.props.BoolProperty(
    name="Show Render Settings",
    default=False
)
bpy.types.Scene.show_render_status = bpy.props.BoolProperty(
    name="",
    default=True
)
bpy.types.Scene.import_settings_fold = bpy.props.BoolProperty(
    name="Show Render Settings",
    default=False
)
bpy.types.Scene.props_settings_fold = bpy.props.BoolProperty(
    name="Show Prop Settings",
    default=False
)
bpy.types.Scene.show_advance_prop_settings = bpy.props.BoolProperty(
        name="Prop Cleaner Settings",
        default=False
)
bpy.types.Scene.show_prop_helpInfo = bpy.props.BoolProperty(
        name="Check Prop Verts. Status",
        default=False
)
bpy.types.Scene.characters_fold = bpy.props.BoolProperty(
    name="Characters Settings",
    default=False
)
bpy.types.Scene.show_character_list = bpy.props.BoolProperty(
    name="",
    default=True
)
bpy.types.Scene.remove_empties = bpy.props.BoolProperty(
    name="Remove Emptys",
    description="Elimina todos los emptys",
    default=True
)
bpy.types.Scene.remove_doubles = bpy.props.BoolProperty(
    name="Remove Double Vertices",
    description="Combina los vertices duplicados",
    default=True
)
bpy.types.Scene.add_in_collection = bpy.props.BoolProperty(
    name="Create Collection",
    description="Anida las partes del prop a un nuevo Collection",
    default=True
)
bpy.types.Scene.mergeObjects = bpy.props.BoolProperty(
    name="Merge Meshes",
    description="Junta todas las partes en una sola",
    default=False
)
