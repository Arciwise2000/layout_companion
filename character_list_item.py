import bpy
class CharacterListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="name")  # type: ignore
    scale: bpy.props.FloatProperty(name="scale")  # type: ignore