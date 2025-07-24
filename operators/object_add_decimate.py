import bpy
from ..LC_utils import add_decimate_modifier  # Import correcto si usas paquetes

class OBJECT_OT_AddDecimateModifier(bpy.types.Operator):
    bl_idname = "object.add_decimate_modifier"
    bl_label = "Añadir Decimate"
    bl_description = "Añade un modificador Decimate al objeto seleccionado"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'
    
    def execute(self, context):
        success = add_decimate_modifier()
        if not success:
            self.report({'WARNING'}, "No mesh found to apply Decimate modifier.")
        return {'FINISHED'}