import bpy
from ..scene_utils import is_collection_exist
from bpy.props import FloatVectorProperty
from mathutils import Vector, Euler
import math
 
class LayoutNotesProperties(bpy.types.PropertyGroup):
    text_color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1, 0, 0),
        description="Color del texto de la nota"
    )
    grease_pencil_color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1, 0, 0,1),
        description="Color del Grease Pencil"
    )




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
        
        color = context.scene.layout_notes_settings.text_color
        rgb_color = list(color) + [1.0]
        
        base_name = "Emission_Note"
        unique_name = get_unique_material_name(base_name)
        mat = create_material(unique_name, rgb_color)
        
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        
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

        obj.location = (-0.32, -0.17, focal_compensation(cam))

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

class OT_EXTRAS_RenderNoteGP(bpy.types.Operator):
    bl_idname = "extra.create_note_gp"
    bl_label = ""
    bl_description = "Crea una nota de dibujo"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        coll_name = "NOTAS_LAYOUT"
        if coll_name in bpy.data.collections:
            coll = bpy.data.collections[coll_name]
        else:
            coll = bpy.data.collections.new(coll_name)
            context.scene.collection.children.link(coll)

        bpy.ops.object.grease_pencil_add(location=(0, 0, 0))
        gp_object = context.active_object
        gp_object.name = "GP_Note"
        
        gp_object.hide_render = True
        cam = context.scene.camera
        if not cam:
            self.report({'ERROR'}, "No hay cámara en la escena.")
            bpy.data.objects.remove(gp_object)
            return {'CANCELLED'}
        
        for c in gp_object.users_collection:
            c.objects.unlink(gp_object)
        coll.objects.link(gp_object)
        
        gp_object.parent = cam

        gp_object.location = (-0.32, -0.17, focal_compensation(cam))
        gp_object.rotation_euler = (0, 0, 0)


        gp_data = gp_object.data
        
        color = context.scene.layout_notes_settings.grease_pencil_color
        bpy.ops.material.new()
        bpy.context.object.active_material.grease_pencil.color = color

        bpy.ops.object.select_all(action='DESELECT')
        gp_object.select_set(True)
        context.view_layer.objects.active = gp_object
        bpy.ops.object.mode_set(mode='PAINT_GREASE_PENCIL')
        
        brush = context.tool_settings.gpencil_paint.brush
        brush.size = 2
        brush.strength = 1.0
        return {'FINISHED'}

class OT_EXTRAS_SetScaleToZero(bpy.types.Operator):
    bl_idname = "extra.zero_scale"
    bl_label = ""
    bl_description = "Oculta el objeto seleccionado a escala : (0,0,0)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
       
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No hay objeto activo")
            return {'CANCELLED'}
        
        current_frame = context.scene.frame_current
        
        obj.keyframe_insert(data_path="scale", frame=current_frame - 1)
        
        obj.scale = (0.0, 0.0, 0.0)
        obj.keyframe_insert(data_path="scale", frame=current_frame)
        
        return {'FINISHED'}


class OT_EXTRAS_move_camera_to_cursor(bpy.types.Operator):
    bl_idname = "extra.move_camera"
    bl_label = "Move dolly rig to cursor"
    bl_options = {'REGISTER', 'UNDO'}

    offset_distance: bpy.props.FloatProperty(
        name="Root distance",
        default=5.0,
        description="Distancia detrás del Aim para colocar el Root"
    )
    root_zero_height: bpy.props.BoolProperty(
        name="Keep root in 0 height",
        default=True,
        description="Mantiene la altura del root siempre en Z = 0"
    )
    centrally_align: bpy.props.BoolProperty(
        name="Centrally align",
        default=True,
        description="Ignora la direccion vertical y alinea la camara al aim"
    )
    auto_keying: bpy.props.BoolProperty(
        name="Auto keying",
        default=True,
        description="Ignora la direccion vertical y alinea la camara al aim"
    )

    def execute(self, context):
        rig_name = "Dolly_Rig"
        root_bone_name = "Root"
        camera_bone_name = "Camera"
        aim_bone_name = "Aim"

        rig = bpy.data.objects.get(rig_name)
       
        if rig is None or rig.type != 'ARMATURE':
            self.report({'ERROR'}, f"No se encontró el armature '{rig_name}'")
            return {'CANCELLED'}
       
        pb_root = rig.pose.bones.get(root_bone_name)
        pb_aim = rig.pose.bones.get(aim_bone_name)
        pb_camera = rig.pose.bones.get(camera_bone_name)
        
        if pb_root is None or pb_aim is None or pb_camera is None:
            raise Exception("No se encontraron los huesos Root, Camera o Aim")
        
        area = next((a for a in context.window.screen.areas if a.type == 'VIEW_3D'), None)
        if not area:
            return {'CANCELLED'}
        
        cursor_loc = context.scene.cursor.location.copy()
        
        region_3d = area.spaces.active.region_3d
        view_dir = quantize_vector_direction(region_3d.view_rotation @ Vector((0.0, 0.0, 1.0)), step_degrees=5)
        bone_view_pos = cursor_loc - (view_dir * self.offset_distance)
        if self.root_zero_height: 
            bone_view_pos.z = 0
        
        current_frame = context.scene.frame_current
        if self.auto_keying:
            prev_frame = current_frame - 1
            insert_loc_rot_keys([pb_root, pb_aim, pb_camera], prev_frame)

        pb_root.matrix.translation = bone_view_pos
        bpy.context.view_layer.update()
        pb_aim.matrix.translation = cursor_loc
        
        if  self.centrally_align:
            pb_camera.location.z = pb_aim.location.z
            
        bpy.context.view_layer.update()
        
        if self.auto_keying:
            insert_loc_rot_keys([pb_root, pb_aim, pb_camera], current_frame)
            
        return {'FINISHED'}

def insert_loc_rot_keys(pose_bones, frame):
    for pb in pose_bones:
        pb.keyframe_insert(data_path="location", frame=frame)
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)


def quantize_vector_direction(vec, step_degrees=5.0):
    eul = vec.to_track_quat('Z', 'Y').to_euler()

    step_radians = math.radians(step_degrees)

    eul.x = round(eul.x / step_radians) * step_radians
    eul.y = round(eul.y / step_radians) * step_radians
    eul.z = round(eul.z / step_radians) * step_radians

    quat = eul.to_quaternion()
    quantized_vec = quat @ Vector((0.0, 0.0, -1.0))
    return quantized_vec.normalized()

def focal_compensation(cam):
    focal_ref = 50.0
    depth_ref = -1.0
    focal_actual = cam.data.lens if cam and cam.type == 'CAMERA' else focal_ref
    depth_scaled = depth_ref * (focal_actual / focal_ref)
    return depth_scaled

def create_material(name, color_rgba):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    emission = nodes.new(type='ShaderNodeEmission')
    output = nodes.new(type='ShaderNodeOutputMaterial')

    emission.location = (-200, 0)
    output.location = (0, 0)

    emission.inputs['Color'].default_value = color_rgba
    emission.inputs['Strength'].default_value = 1

    links.new(emission.outputs['Emission'], output.inputs['Surface'])

    return mat


def get_unique_material_name(base_name):
    existing = bpy.data.materials
    if base_name not in existing:
        return base_name

    index = 1
    while True:
        new_name = f"{base_name}_{str(index).zfill(3)}"
        if new_name not in existing:
            return new_name
        index += 1




    
def register_extras():
    for cls in (
        LayoutNotesProperties,
        OT_EXTRAS_BakeParticles,
        OT_EXTRAS_RenderNote,
        OT_EXTRAS_RenderNoteGP,
        OT_EXTRAS_SetScaleToZero,
        OT_EXTRAS_move_camera_to_cursor
    ):
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.layout_notes_settings = bpy.props.PointerProperty(type=LayoutNotesProperties)

def unregister_extras():
    
    if hasattr(bpy.types.Scene, "layout_notes_settings"):
        del bpy.types.Scene.layout_notes_settings
    
    for cls in reversed((
        LayoutNotesProperties,
        OT_EXTRAS_BakeParticles,
        OT_EXTRAS_RenderNote,
        OT_EXTRAS_RenderNoteGP,
        OT_EXTRAS_SetScaleToZero,
        OT_EXTRAS_move_camera_to_cursor
    )):
        bpy.utils.unregister_class(cls)