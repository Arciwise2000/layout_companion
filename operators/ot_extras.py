import bpy
from ..scene_utils import is_collection_exist


def get_all_objects_recursive(collection):
    objects = list(collection.objects)
    for subcol in collection.children:
        objects.extend(get_all_objects_recursive(subcol))
    return objects


class OT_EXTRAS_BakeParticles(bpy.types.Operator):
    bl_idname = "extra.bake_particles"
    bl_label = "Bake all Particles without cache"
    bl_description = "Bakea todas las partículas sin cache dentro de EFECTOS"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        collection = is_collection_exist("EFECTOS")
        if not collection:
            self.report({'ERROR'}, "No se encontró la colección: EFECTOS")
            return {'CANCELLED'}

        scene = context.scene
        all_objects = get_all_objects_recursive(collection)

        particle_mods = []
        for obj in all_objects:
            for mod in obj.modifiers:
                if mod.type == 'PARTICLE_SYSTEM':
                    particle_mods.append((obj, mod))

        total = len(particle_mods)
        if total == 0:
            self.report({'WARNING'}, "No se encontraron sistemas de partículas.")
            return {'CANCELLED'}

        wm = context.window_manager
        wm.progress_begin(0, 100)

        try:
            for i, (obj, mod) in enumerate(particle_mods):
                pcache = mod.particle_system.point_cache
                pcache.use_disk_cache = True
                pcache.name = obj.name + "_Cache"

                with bpy.context.temp_override(
                    scene=scene,
                    active_object=obj,
                    point_cache=pcache
                ):
                    bpy.ops.ptcache.free_bake()
                    bpy.ops.ptcache.bake(bake=True)

                progress = int(((i + 1) / total) * 100)
                wm.progress_update(progress)

        except Exception as e:
            self.report({'ERROR'}, f"Error durante el bake: {e}")
            return {'CANCELLED'}

        finally:
            wm.progress_end()

        self.report({'INFO'}, f"Se bakearon {total} sistemas de partículas.")
        return {'FINISHED'}

    
class OT_EXTRAS_RenderNote(bpy.types.Operator):
    bl_idname = "extra.create_note"
    bl_label = ""
    bl_description = "Crea una nota de layout"
    bl_options = {'REGISTER', 'UNDO'}

    text: bpy.props.StringProperty(
        name="Text",
        description="",
        default="Nota para animador o render"
    )

    def execute(self, context):
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT'
                                    )
        coll_name = "NOTAS_LAYOUT"
        if coll_name in bpy.data.collections:
            coll = bpy.data.collections[coll_name]
        else:
            coll = bpy.data.collections.new(coll_name)
            context.scene.collection.children.link(coll)

        bpy.ops.object.text_add()
        obj = context.active_object
        obj.data.body = self.text
        obj.scale = (0.04, 0.04, 0.04)

        for c in obj.users_collection:
            c.objects.unlink(obj)
        coll.objects.link(obj)

        obj.hide_render = True

        cam = context.scene.camera
        if not cam:
            self.report({'ERROR'}, "No hay cámara en la escena.")
            bpy.data.objects.remove(obj)
            return {'CANCELLED'}
        
        obj.parent = cam
        obj.location = (-0.32, -0.17, -1)
        obj.rotation_euler = (0, 0, 0)
        
        current_frame = context.scene.frame_current
        obj.keyframe_insert(data_path="scale", frame=current_frame)
        
        obj.scale = (0.0, 0.0, 0.0)
        obj.keyframe_insert(data_path="scale", frame=current_frame - 1)

        for fcurve in obj.animation_data.action.fcurves:
            if fcurve.data_path == "scale":
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = 'CONSTANT'


        return {'FINISHED'}
    
    
def register_extras():
    for cls in (
        OT_EXTRAS_BakeParticles,
        OT_EXTRAS_RenderNote
    ):
        bpy.utils.register_class(cls)


def unregister_extras():
    for cls in reversed((
        OT_EXTRAS_BakeParticles,
        OT_EXTRAS_RenderNote
    )):
        bpy.utils.unregister_class(cls)