import bpy
import os

class RENDER_OT_QuickSetup(bpy.types.Operator):
    bl_idname = "render.quick_setup"
    bl_label = "Quick Render Setup"
    bl_description = "Ajusta la configuracion al .blend"
    def execute(self, context):
        try:
            scene = context.scene
            scene.render.image_settings.file_format = 'FFMPEG'
            scene.render.ffmpeg.format = 'MPEG4'
            scene.render.resolution_percentage = 50
            scene.render.fps = 24
            scene.render.fps_base = 1.0
            scene.render.engine = "CYCLES"
            scene.render.use_simplify = True
            scene.render.simplify_subdivision = 0
            bpy.data.use_autopack = True
            if bpy.data.filepath:
                filename = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                scene.render.filepath = f"//{filename}.mp4"
            else:
                scene.render.filepath = "//render_output.mp4"
                self.report({'WARNING'}, "Using default output path, please save your .blend file first.")

            self.report({'INFO'}, "Settings Applied!")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}