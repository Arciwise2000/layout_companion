import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
from bpy.props import FloatVectorProperty, BoolProperty, FloatProperty


draw_handler = None


class CameraFrameSettings(bpy.types.PropertyGroup):
    enabled: BoolProperty(
        name="",
        description="Activa/desactiva el dibujado del frame de cámara",
        default=False
    )
    color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.5, 0.5, 0.5),
        description="Color de las líneas guía"
    )
    width: FloatProperty(
        name="Width",
        min=0.2,
        max=3.5,
        default= 1,
        description="Grosor de las líneas guía"
    )

def get_camera_frame_bounds(context):
    scene = context.scene
    camera = scene.camera
    
    if not camera or camera.type != 'CAMERA':
        return None

    frame = camera.data.view_frame(scene=scene)

    region = context.region
    rv3d = context.region_data
    
    if not rv3d or rv3d.view_perspective != 'CAMERA':
        return None

    frame_world = [camera.matrix_world @ v for v in frame]
    frame_2d = []
    
    for v in frame_world:
        co_2d = location_3d_to_region_2d(region, rv3d, v)
        if co_2d:
            frame_2d.append(co_2d)
    
    if len(frame_2d) != 4:
        return None
    
    min_x = min(v.x for v in frame_2d)
    max_x = max(v.x for v in frame_2d)
    min_y = min(v.y for v in frame_2d)
    max_y = max(v.y for v in frame_2d)
    
    return {
        'min_x': min_x,
        'max_x': max_x,
        'min_y': min_y,
        'max_y': max_y,
        'width': max_x - min_x,
        'height': max_y - min_y
    }

def draw_camera_frame_callback():
    context = bpy.context
    scene = context.scene
    settings = scene.camera_frame_settings

    if not settings.enabled:
        return
    if not context.space_data.overlay.show_overlays:
        return

    frame = get_camera_frame_bounds(context)
    if not frame:
        return

    base_offset_x = (frame['max_x'] - frame['min_x']) * -0.04 #sides
    base_offset_y = (frame['max_y'] - frame['min_y']) * -0.05 #down
    top_offset_y  = (frame['max_y'] - frame['min_y']) * -0.1 #up

    line_thickness = settings.width

    def make_rect(v1, v2, thickness, axis='x'):
        # Crea un rectángulo entre dos puntos v1 y v2
        if axis == 'x':
            offset = Vector((0, thickness))
        else:
            offset = Vector((thickness, 0))
        return [
            v1,
            v2,
            v2 + offset,
            v1 + offset
        ]
        
    lines = []
    lines += make_rect(
        Vector((frame['min_x'] - base_offset_x, frame['min_y'] - base_offset_y)),
        Vector((frame['max_x'] + base_offset_x, frame['min_y'] - base_offset_y)),
        line_thickness,
        'x'
    )
    lines += make_rect(
        Vector((frame['max_x'] + base_offset_x, frame['min_y'] - base_offset_y)),
        Vector((frame['max_x'] + base_offset_x, frame['max_y'] + top_offset_y)),
        line_thickness,
        'y'
    )
    lines += make_rect(
        Vector((frame['max_x'] + base_offset_x, frame['max_y'] + top_offset_y)),
        Vector((frame['min_x'] - base_offset_x, frame['max_y'] + top_offset_y)),
        line_thickness,
        'x'
    )
    lines += make_rect(
        Vector((frame['min_x'] - base_offset_x, frame['max_y'] + top_offset_y)),
        Vector((frame['min_x'] - base_offset_x, frame['min_y'] - base_offset_y)),
        line_thickness,
        'y'
    )

    # Índices para dibujar los rectángulos
    indices = []
    for i in range(0, len(lines), 4):
        indices += [(i, i+1, i+2), (i+2, i+3, i)]

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {"pos": lines}, indices=indices)

    shader.bind()
    shader.uniform_float("color", settings.color)
    batch.draw(shader)
    

def register_draw_handler():
    global draw_handler
    if draw_handler is None:
        draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_camera_frame_callback, (), 'WINDOW', 'POST_PIXEL'
        )

def unregister_draw_handler():
    global draw_handler
    if draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handler, 'WINDOW')
        draw_handler = None
        
@bpy.app.handlers.persistent
def update_handler(scene):
    if scene.camera_frame_settings.enabled:
        if draw_handler is None:
            register_draw_handler()
    else:
        if draw_handler is not None:
            unregister_draw_handler()
            
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def register_handlers():
    if update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_handler)

def unregister_handlers():
    if update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_handler)
        
        


def register():
    bpy.utils.register_class(CameraFrameSettings)
    bpy.types.Scene.camera_frame_settings = bpy.props.PointerProperty(type=CameraFrameSettings)
    
    register_handlers()
    
    if hasattr(bpy.context, "scene") and bpy.context.scene:
            settings = bpy.context.scene.camera_frame_settings
            if settings.enabled and draw_handler is None:
                register_draw_handler()

def unregister():
    
    unregister_handlers()
    unregister_draw_handler()
    
    if hasattr(bpy.types.Scene, "camera_frame_settings"):
        del bpy.types.Scene.camera_frame_settings
    bpy.utils.unregister_class(CameraFrameSettings)