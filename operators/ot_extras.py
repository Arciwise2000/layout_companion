import bpy

from ..LC_utils import is_collection_exist

class OT_EXTRAS(bpy.types.Operator):
    bl_idname = "ot.blend_extras"
    bl_label = "Bake all Particles without cache"
    bl_description = "Bakea todas las particulas sin cache dentro de EFECTOS"
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        collection = is_collection_exist("EFECTOS")
        if not collection:
            self.report({'ERROR'}, "No se encontró la colección: EFECTOS")
            return {'CANCELLED'}
        
        scene = context.scene
        for object in collection.objects:
            for modifier in object.modifiers:
                if modifier.type == 'PARTICLE_SYSTEM':
                    modifier.particle_system.point_cache.use_disk_cache = True
                    modifier.particle_system.point_cache.name = object.name + "_Cache"
                    with bpy.context.temp_override(
                        scene=scene,
                        active_object=object,
                        point_cache=modifier.particle_system.point_cache): bpy.ops.ptcache.bake(bake=True)

        return {'FINISHED'}