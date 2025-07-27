import bpy
import os
from ..addon_updater_ops import get_user_preferences

class RENDER_OT_QuickSetup(bpy.types.Operator):
    bl_idname = "render.quick_setup"
    bl_label = "Quick Render Setup"
    bl_description = "Ajusta la configuración al .blend y genera notas si es necesario"

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

            prefs = get_user_preferences(context)
            context.workspace.name = "Layout_" + prefs.layouter_name

            if bpy.data.filepath:
                blend_path = bpy.data.filepath
                blend_dir = os.path.dirname(blend_path)
                filename = os.path.splitext(os.path.basename(blend_path))[0]
                scene.render.filepath = f"//{filename}.mp4"

                notas_render_path = os.path.join(blend_dir, "NOTAS RENDER.txt")
                notas_anim_path = os.path.join(blend_dir, "NOTAS ANIMADOR.txt")

                if not os.path.exists(notas_render_path):
                    with open(notas_render_path, "w", encoding="utf-8") as f:
                        f.write("NOTAS PARA RENDER (layouter: " + prefs.layouter_name + "):\n")

                if not os.path.exists(notas_anim_path):
                    with open(notas_anim_path, "w", encoding="utf-8") as f:
                        f.write("NOAS PARA ANIMADOR (layouter: " + prefs.layouter_name + "):\n")
            else:
                scene.render.filepath = "//render_output.mp4"
                self.report({'WARNING'}, "Usando ruta de salida por defecto. Guarda el archivo .blend primero.")
                
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}
