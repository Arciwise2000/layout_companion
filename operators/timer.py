import time
import bpy


def register_timer_props():
    bpy.types.Scene.session_start_time = bpy.props.FloatProperty(name="Session Start Time", default=time.time())
    
def reset_session_time(self, context):
    context.scene.session_start_time = time.time()
    

def session_timer():
    wm = bpy.context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return 60.0  # Actualiza cada minuto

def start_timer():
    bpy.app.timers.register(session_timer)
