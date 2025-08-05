import bpy
import math

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
    
def add_decimate_modifier():
    """Adds a Decimate modifier to the selected object."""
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        return False
    
    last_obj = None
    for obj in selected_objects:
        if obj.type == 'MESH':  # Only applicable to mesh objects
            if "Decimate" not in obj.modifiers:
                decimate_mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
                decimate_mod.ratio = 0.9
        
        last_obj = obj
    
    if last_obj:
        bpy.context.view_layer.objects.active = last_obj
        for area in bpy.context.window.screen.areas:
            if area.type == 'PROPERTIES':
                for space in area.spaces:
                    if space.type == 'PROPERTIES':
                        space.context = 'MODIFIER'
                        break
    return True

    
class OBJECT_OT_AddSmoothByAngle(bpy.types.Operator):
    bl_idname = "object.add_smooth_by_angle"
    bl_label = "Añadir Smooth by Angle"
    bl_description = "Suaviza las caras del objeto que tengan un angulo menor al colocado '30 grados'"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'
    
    def execute(self, context):
        success = add_smooth_by_angle()
        if not success:
            self.report({'WARNING'}, "No mesh found to apply Smooth by angle modifier.")
        return {'FINISHED'}
    
import bpy
import math

def add_smooth_by_angle():
    bpy.ops.object.shade_auto_smooth()
    
    return True