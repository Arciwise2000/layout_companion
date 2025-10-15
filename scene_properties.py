import bpy

from bpy.props import BoolProperty, PointerProperty, EnumProperty

class FoldSettings(bpy.types.PropertyGroup):
    render_settings_fold: BoolProperty(
        name="Show render settings",
        default=False
    )
    import_settings_fold: BoolProperty(
        name="Show import settings",
        default=False
    )
    props_settings_fold: BoolProperty(
        name="Show prop settings",
        default=False
    )
    scales_fold: BoolProperty(
        name="Scales settings",
        default=False
    )
    extras_fold: BoolProperty(
        name="Extras settings",
        default=False
    )


class ShowSettings(bpy.types.PropertyGroup):
    render_status: BoolProperty(
        name="",
        default=True
    )
    leght_info: BoolProperty(
        name="",
        default=True
    )
    prop_helpInfo: BoolProperty(
        name="",
        default=False
    )
    character_list: BoolProperty(
        name="",
        default=False
    )
    map_list: BoolProperty(
        name="",
        default=False
    )
    advance_prop_settings: BoolProperty(
    name="Prop cleaner settings",
    default=False
    )


class PropsAdvancedSettings(bpy.types.PropertyGroup):
    remove_empties: BoolProperty(
        name="Remove emptys",
        description="Elimina todos los emptys y deja solo los objetos",
        default=True
    )
    remove_doubles: BoolProperty(
        name="Remove double vertices",
        description="Combina los vertices duplicados",
        default=True
    )
    add_in_collection: BoolProperty(
        name="Create collection",
        description="Anida las partes del prop a un nuevo Collection",
        default=True
    )
    mergeObjects: BoolProperty(
        name="Merge meshes",
        description="Junta todos los objetos en una solo",
        default=False
    )
    only_selected_objects: BoolProperty(
        name="Only selected objects",
        description="Solo limpia los objetos seleccionados, en caso contrario limpiara todos los objetos dentro de un empty; o si no tiene empty, del collection",
        default=False
    )
    add_final_empty: BoolProperty(
    name="Make a empty to hndle the prop",
    description="Crea un empty para manejar que el animador peuda manejar el prop mas facil",
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
    bpy.utils.register_class(FoldSettings)
    bpy.utils.register_class(ShowSettings)
    bpy.utils.register_class(PropsAdvancedSettings)
    
    bpy.types.Scene.show_settings = PointerProperty(type=ShowSettings)
    bpy.types.Scene.fold_settings = PointerProperty(type=FoldSettings)
    bpy.types.Scene.props_advanced_settings = PointerProperty(type=PropsAdvancedSettings)
    
    
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
                    ('DRIVE PROPS', "Collab", "Mostrar props colaborativos"),
                    ('HORNS FILES', "Drive", "Mostrar recursos de horns"),
                    ('MANIQUIES', "Maniquies", "Mostrar maniquies")
                ],
                default='RESOURCES'
            )



def unregister_props():
    del bpy.types.WindowManager.show_characterUpdater
    
    if hasattr(bpy.types.Scene, "resource_tabs"):
        del bpy.types.Scene.resource_tabs
    
    if hasattr(bpy.types.Scene, "fold_settings"):
        del bpy.types.Scene.fold_settings
    
    if hasattr(bpy.types.Scene, "show_settings"):
        del bpy.types.Scene.show_settings
        
    if hasattr(bpy.types.Scene, "props_advanced_settings"):
        del bpy.types.Scene.props_advanced_settings
        
    bpy.utils.unregister_class(PropsAdvancedSettings)
    bpy.utils.unregister_class(ShowSettings)
    bpy.utils.unregister_class(FoldSettings)
