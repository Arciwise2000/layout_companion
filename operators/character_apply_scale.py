import bpy

class CHARACTER_OT_ApplyScaleToSelected(bpy.types.Operator):
    bl_idname = "character.apply_scale_to_selected"
    bl_label = "Apply Scale to Selected"
    bl_description = "Aplica la escala del personaje seleccionado al objeto activo"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and 
                hasattr(context.scene, "character_list_items") and
                context.scene.character_list_index >= 0 and
                len(context.scene.character_list_items) > context.scene.character_list_index)
    
    def execute(self, context):
        scene = context.scene
        selected_character = scene.character_list_items[scene.character_list_index]
        obj = context.active_object
        
        obj.scale = (selected_character.scale, selected_character.scale, selected_character.scale)
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        
        loc = scene.lock_character_loc
        rot = scene.lock_character_rot
        scale = scene.lock_character_scale

        obj.lock_location = (loc,loc, loc)
        obj.lock_rotation = (rot, rot, rot)
        obj.lock_scale = (scale, scale, scale)
            
        self.report({'INFO'}, f"Escala {selected_character.scale} aplicada a {obj.name}")
        return {'FINISHED'}