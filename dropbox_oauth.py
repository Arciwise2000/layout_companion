import importlib
import subprocess
import sys
import bpy
import tempfile
import os
import secrets
import json
import threading
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from ..addon_updater_ops import get_user_preferences
import bpy.utils.previews
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher


# SISTEMA -------------------------------------------------


def is_dropbox_installed():
    try:
        import dropbox
        return True
    except ImportError:
        return False


def install_dropbox():
    python_exe = sys.executable
    try:
        subprocess.check_call([python_exe, "-m", "pip", "install", "dropbox"])
        importlib.invalidate_caches()
        import dropbox
        return True
    except Exception as e:
        print("Error instalando dropbox:", e)
        return False


class INSTALL_OT_dependencies(bpy.types.Operator):
    bl_idname = "prop.install_dependencies"
    bl_label = "Instalar librería Dropbox"

    def execute(self, context):
        ok = install_dropbox()
        if ok:
            register_dropbox()
            from .dropbox_collaborator import register_dropbox_collaboration
            register_dropbox_collaboration()
            self.report({'INFO'}, "Dropbox instalado correctamente")
        else:
            self.report({'ERROR'}, "No se pudo instalar Dropbox")
        return {'FINISHED'}


preview_collections = {}
CONFIG_PATH = Path(os.path.dirname(__file__)) / "config.json"


def load_dropbox_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de configuración: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class PropTag(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()


class LayoutCompanionPreview(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    colaborador: bpy.props.StringProperty()
    descripcion: bpy.props.StringProperty()
    image_path: bpy.props.StringProperty()
    json_filename: bpy.props.StringProperty()
    tags: bpy.props.CollectionProperty(type=PropTag)


# AUTENTICACION Y COSAS DE API DE DROPBOX------------

class PROPS_OT_DropBoxAuthenticate(bpy.types.Operator):
    bl_idname = "prop.dropbox_auth"
    bl_label = "Activate with Dropbox"

    def execute(self, context):
        config = load_dropbox_config()

        import dropbox
        from dropbox.oauth import DropboxOAuth2Flow

        APP_KEY = config.get("APP_KEY")
        REDIRECT_URI = "http://localhost:5000/callback"

        auth_data = {'code': None, 'state': None, 'error': None}
        auth_event = threading.Event()

        class AuthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    query = urlparse(self.path).query
                    params = parse_qs(query)
                    auth_data['code'] = params.get('code', [None])[0]
                    auth_data['state'] = params.get('state', [None])[0]

                    if auth_data['code']:
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(
                            "<h1>¡Autenticación exitosa! Puedes cerrar esta ventana.</h1>".encode("utf-8"))
                    else:
                        auth_data['error'] = "Falta código de autorización"
                        self.send_error(400, auth_data['error'])
                except Exception as e:
                    auth_data['error'] = f"Error en el servidor local: {str(e)}"
                finally:
                    auth_event.set()

        def run_server():
            try:
                server = HTTPServer(('localhost', 5000), AuthHandler)
                server.timeout = 1
                while not auth_event.is_set():
                    server.handle_request()
                server.server_close()
            except Exception as e:
                auth_data['error'] = f"No se pudo iniciar el servidor: {str(e)}"
                auth_event.set()

        threading.Thread(target=run_server, daemon=True).start()

        auth_flow = DropboxOAuth2Flow(
            consumer_key=APP_KEY,
            consumer_secret=None,   # si usas PKCE, esto va como None
            redirect_uri=REDIRECT_URI,
            session={},             # puedes usar un dict vacío o manejar tu propio state
            csrf_token_session_key="dropbox-auth-csrf-token",
            use_pkce=True,          # 🚀 activa PKCE
            token_access_type="offline"
        )

        authorize_url = auth_flow.start()
        webbrowser.open(authorize_url)

        timeout = 60
        auth_event.wait(timeout)

        if auth_data['error']:
            self.report({'ERROR'}, auth_data['error'])
            return {'CANCELLED'}

        if not auth_data['code']:
            self.report({'ERROR'}, "Tiempo de espera agotado")
            return {'CANCELLED'}

        try:
            result = auth_flow.finish({
                "code": auth_data["code"],
                "state": auth_data["state"]
            })

            prefs = get_user_preferences(context)
            if prefs:
                prefs.dropbox_access_token = result.access_token
                bpy.ops.wm.save_userpref()

            previews = fetch_dropbox_assets(result.access_token)
            register_dropbox_previews(previews)

            self.report({'INFO'}, "¡Autenticación exitosa!")
        except Exception as e:
            self.report({'ERROR'}, f"Error al obtener token: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class PROPS_OT_DropBoxLogout(bpy.types.Operator):
    bl_idname = "prop.dropbox_logout"
    bl_label = "Logout"

    def execute(self, context):
        try:
            prefs = get_user_preferences(context)
            if prefs:
                prefs.dropbox_access_token = ""
                bpy.ops.wm.save_userpref()

            context.window_manager.layout_companion_previews.clear()

            if "dropbox" in preview_collections:
                bpy.utils.previews.remove(preview_collections["dropbox"])
                del preview_collections["dropbox"]

            cleanup_temp_files()

            self.report({'INFO'}, "Sesión de Dropbox cerrada correctamente.")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"No se pudo cerrar sesión: {str(e)}")
            return {'CANCELLED'}


class PROPS_OT_DropBoxImportBlend(bpy.types.Operator):
    bl_idname = "prop.dropbox_import_blend"
    bl_label = "Import"
    bl_description = "Importa el prop seleccionado"

    def execute(self, context):
        prefs = get_user_preferences(context)
        import dropbox
        access_token = prefs.dropbox_access_token if prefs else None

        if not access_token:
            self.report({'ERROR'}, "No hay sesión de Dropbox activa.")
            return {'CANCELLED'}

        active_preview = get_active_dropbox_preview(context)
        if not active_preview:
            self.report({'ERROR'}, "No se ha seleccionado ningún asset.")
            return {'CANCELLED'}

        json_base = os.path.splitext(active_preview.json_filename)[0]
        blend_name = json_base + ".blend"

        dbx = dropbox.Dropbox(access_token)
        target_path = f"/Apps/Layout Companion/Props/{blend_name}"

        temp_folder = get_temp_folder()
        local_blend_path = temp_folder / blend_name

        try:
            metadata, res = dbx.files_download(target_path)
            with open(local_blend_path, "wb") as f:
                f.write(res.content)

            self.report({'INFO'}, f"Archivo descargado: {blend_name}")

            with bpy.data.libraries.load(str(local_blend_path), link=False) as (data_from, data_to):
                if not data_from.collections:
                    self.report(
                        {'ERROR'}, f"No se encontraron collections en {blend_name}")
                    return {'CANCELLED'}

                data_to.collections = list(data_from.collections)

            imported_collections = {
                col.name: col for col in data_to.collections if col}
            root_collections = []
            scene = context.scene

            if scene.resource_import_origin_camera:
                bpy.ops.resource.place_origin(origin_type="camera")

            for col in imported_collections.values():

                for obj in [o for o in col.objects if o.parent is None]:
                    obj.location = scene.cursor.location

                is_child = False
                for potential_parent in imported_collections.values():
                    if col.name in [child.name for child in potential_parent.children]:
                        is_child = True
                        break
                if not is_child:
                    root_collections.append(col)
            for root in root_collections:
                if root.name not in bpy.context.scene.collection.children:
                    bpy.context.scene.collection.children.link(root)

            self.report({'INFO'}, "Prop importado!.")

        except dropbox.exceptions.ApiError:
            self.report({'ERROR'}, f"No se encontró {blend_name} en Dropbox.")
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error al importar: {str(e)}")
            return {'CANCELLED'}

        finally:
            if local_blend_path.exists():
                try:
                    os.remove(local_blend_path)
                except:
                    pass

        return {'FINISHED'}


class PROPS_OT_DropBoxRefreshPreviews(bpy.types.Operator):
    bl_idname = "prop.dropbox_refresh_previews"
    bl_label = ""
    bl_description = "Recarga la lista de assets desde Dropbox"

    def execute(self, context):
        prefs = get_user_preferences(context)
        if not prefs or not prefs.dropbox_access_token:
            self.report({'ERROR'}, "No hay sesión activa de Dropbox")
            return {'CANCELLED'}

        def on_assets_loaded(previews, error=None):
            wm = bpy.context.window_manager

            if error == "expired_token":
                bpy.ops.prop.dropbox_logout()
                wm.popup_menu(lambda self, ctx: self.layout.label(
                    text="El token de Dropbox ha expirado. Vuelva a autenticarse."
                ), title="Dropbox", icon='ERROR')
                return

            if previews:
                register_dropbox_previews(previews)
                wm.popup_menu(lambda self, ctx: self.layout.label(
                    text="Lista actualizada"
                ), title="Dropbox", icon='INFO')
            else:
                wm.popup_menu(lambda self, ctx: self.layout.label(
                    text="No hay previews disponibles"
                ), title="Dropbox", icon='ERROR')

            # Forzar refresco UI
            for window in wm.windows:
                for area in window.screen.areas:
                    if area.type in {'VIEW_3D', 'PROPERTIES'}:
                        area.tag_redraw()

        # Llamada asincrónica con control de errores
        fetch_dropbox_assets_async_safe(
            prefs.dropbox_access_token, on_assets_loaded)

        self.report({'INFO'}, "Descargando previews desde Dropbox...")
        return {'FINISHED'}


def fetch_dropbox_assets_async_safe(access_token, callback):
    from dropbox.exceptions import AuthError

    def worker():
        try:
            previews = fetch_dropbox_assets(access_token)
            bpy.app.timers.register(lambda: callback(previews, None))
        except AuthError as e:
            if getattr(e.error, 'is_expired_access_token', lambda: False)():
                bpy.app.timers.register(
                    lambda: callback(None, "expired_token"))
            else:
                bpy.app.timers.register(lambda: callback(None, "auth_error"))
        except Exception as e:
            print(f"[Dropbox] Error general: {e}")
            bpy.app.timers.register(lambda: callback(None, "general_error"))

    threading.Thread(target=worker, daemon=True).start()

# ENUM DE PROPS, CACHE Y UI------------


def get_temp_folder():
    base_temp = Path(tempfile.gettempdir())
    safe_folder = base_temp / "layout_companion_previews"
    safe_folder.mkdir(exist_ok=True)
    return safe_folder


def fetch_dropbox_assets(access_token):

    import dropbox
    from dropbox.exceptions import AuthError

    dbx = dropbox.Dropbox(access_token)
    target_path = "/Apps/Layout Companion/Props"
    temp_folder = get_temp_folder()
    previews = []

    try:
        # 1️⃣ Obtener todos los archivos de una vez
        entries = dbx.files_list_folder(target_path, recursive=True).entries

        # Filtrar solo JSON
        json_files = [
            e for e in entries
            if isinstance(e, dropbox.files.FileMetadata) and e.name.endswith(".json")
        ]

        def process_json(entry):
            """Descarga y procesa un solo JSON con su imagen"""
            try:
                metadata, res = dbx.files_download(entry.path_lower)
                data = json.loads(res.content)

                json_path = temp_folder / entry.name
                with open(json_path, "wb") as f:
                    f.write(res.content)

                # Manejar imagen asociada
                thumbnail_name = data.get("thumbnail")
                image_path = None

                if thumbnail_name:
                    try:
                        _, img_res = dbx.files_download(
                            f"{target_path}/{thumbnail_name}")
                        image_path = temp_folder / thumbnail_name
                        with open(image_path, "wb") as f:
                            f.write(img_res.content)
                    except Exception as e:
                        print(
                            f"[Dropbox] Error al descargar imagen {thumbnail_name}: {e}")

                raw_tags = data.get("tags", [])
                if not isinstance(raw_tags, list):
                    raw_tags = [raw_tags]

                return {
                    "name": data.get("nombre_demostrativo", entry.name),
                    "image_path": str(image_path) if image_path else None,
                    "tags": [str(t).strip() for t in raw_tags if str(t).strip()],
                    "descripcion": data.get("descripcion", ""),
                    "colaborador": data.get("colaborador", ""),
                    "json_filename": entry.name
                }

            except Exception as e:
                print(f"[Dropbox] Error procesando {entry.name}: {e}")
                return None

        # 2️⃣ Descargar JSON e imágenes en paralelo
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(
                process_json, entry): entry for entry in json_files}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    previews.append(result)

    except AuthError:
        raise
    except Exception as e:
        print(f"[Dropbox] Error al listar carpeta: {e}")

    return previews


def store_previews_in_context(previews):
    wm = bpy.context.window_manager
    wm.layout_companion_previews.clear()
    for item in previews:
        preview = wm.layout_companion_previews.add()
        preview.name = item["name"]
        preview.colaborador = item["colaborador"]
        preview.descripcion = item["descripcion"]
        preview.image_path = item["image_path"]
        preview.json_filename = item["json_filename"]

        preview.tags.clear()
        for t in item.get("tags", []):
            tag_item = preview.tags.add()
            tag_item.name = t


def register_dropbox_previews(previews):
    temp_folder = get_temp_folder()
    pcoll = preview_collections.get("dropbox")
    if not pcoll:
        pcoll = bpy.utils.previews.new()
        pcoll.my_previews_dir = str(temp_folder)
        pcoll.my_previews = []
        preview_collections["dropbox"] = pcoll

    enum_items = []
    for i, item in enumerate(previews):
        image_path = item.get("image_path")
        if not image_path:
            # saltar items sin imagen
            continue
        filename = os.path.basename(image_path)
        thumb = pcoll.get(filename)
        if not thumb:
            try:
                thumb = pcoll.load(filename, image_path, 'IMAGE')
            except Exception as e:
                print(
                    f"[register_dropbox_previews] Error cargando imagen {image_path}: {e}")
                continue
        enum_items.append((filename, item["name"], item.get(
            "descripcion", ""), thumb.icon_id, i))

    pcoll.my_previews = enum_items

    # Guardar también la info en el WindowManager.collection (para mostrar metadata y tags)
    store_previews_in_context(previews)

    # Llamar al update de búsqueda para auto-seleccionar el primer resultado (si procede)
    # Usamos bpy.context porque esta función se llama desde main thread normalmente
    try:
        wm = bpy.context.window_manager
        # Forzamos la ejecución del callback de update manualmente para sincronizar selección
        dropbox_search_update(wm, bpy.context)
    except Exception:
        pass


def get_active_dropbox_preview(context):
    wm = context.window_manager
    selected_name = wm.dropbox_preview_enum
    for item in wm.layout_companion_previews:
        if os.path.basename(item.image_path) == selected_name:
            return item
    return None


def load_previews_from_cache():
    """Carga los previews desde el directorio temporal usando los archivos JSON guardados."""
    temp_folder = get_temp_folder()
    previews = []

    for json_file in temp_folder.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            thumbnail_name = data.get("thumbnail")
            if not thumbnail_name:
                continue

            image_path = temp_folder / thumbnail_name
            if not image_path.exists():
                continue

            # Normalizar tags como hacemos en fetch_dropbox_assets
            raw_tags = data.get("tags", [])
            if not isinstance(raw_tags, list):
                raw_tags = [raw_tags]
            tags_list = [str(t).strip() for t in raw_tags if str(t).strip()]

            previews.append({
                "name": data.get("nombre_demostrativo", json_file.stem),
                "image_path": str(image_path),
                "tags": tags_list,
                "descripcion": data.get("descripcion", ""),
                "colaborador": data.get("colaborador", ""),
                "json_filename": json_file.name
            })
        except Exception as e:
            print(f"Error al cargar preview desde caché {json_file}: {e}")

    return previews


def cleanup_temp_files():
    temp_folder = get_temp_folder()
    for file in temp_folder.glob("*"):
        try:
            if file.is_file():
                file.unlink()
        except Exception as e:
            print(f"Error al eliminar archivo temporal {file}: {e}")


# PAGINACION Y BUSQUEDA -------------------------------------------------

def compute_filtered_items(context):
    """
    Devuelve la lista de tuplas para EnumProperty (id, nombre, descripcion, icon_id, index)
    ordenada por similitud con context.window_manager.dropbox_search.
    """
    wm = context.window_manager
    pcoll = preview_collections.get("dropbox")
    if not pcoll or not getattr(wm, "layout_companion_previews", None):
        return []

    all_items = list(pcoll.my_previews) if getattr(
        pcoll, "my_previews", None) else []
    search = (wm.dropbox_search or "").strip().lower()
    if not search:
        # Sin búsqueda: devolver lista tal cual (mantener icon_id y demás)
        return all_items

    # Construir mapping de tags por identificador (basename de image_path)
    tags_map = {}
    for p in wm.layout_companion_previews:
        try:
            key = os.path.basename(p.image_path) if p.image_path else None
            if not key:
                continue
            tags_map[key] = [t.name.lower() for t in p.tags]
        except Exception:
            continue

    scored = []
    for item in all_items:
        identifier, name, desc, icon_id, orig_index = item
        name_l = (name or "").lower()
        desc_l = (desc or "").lower()
        tags = tags_map.get(identifier, [])

        # Similaridad básica
        score_name = SequenceMatcher(None, search, name_l).ratio()
        score_desc = SequenceMatcher(
            None, search, desc_l).ratio() if desc_l else 0.0
        score_tags = 0.0
        for t in tags:
            s = SequenceMatcher(None, search, t).ratio()
            if s > score_tags:
                score_tags = s

        # Boost si contiene o empieza por
        boost = 0.0
        if search in name_l:
            boost += 0.35
        if name_l.startswith(search):
            boost += 0.15

        score = max(score_name, score_tags, score_desc) + boost
        scored.append((score, item))

    # Orden descendente por score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Filtrar por umbral; si queda vacío devolver top N como fallback
    threshold = 0.20
    filtered = [itm for score, itm in scored if score >= threshold]
    if not filtered:
        # fallback: los más cercanos (hasta 200)
        filtered = [itm for score, itm in scored[:50]]

    # Re-indexar (5º elemento) para enumeración estable en la UI
    result = []
    for idx, itm in enumerate(filtered):
        identifier, name, desc, icon_id, _ = itm
        result.append((identifier, name, desc, icon_id, idx))

    return result


def _get_filtered_enum_items(self, context):
    """Función que usará el EnumProperty.items"""
    try:
        return compute_filtered_items(context)
    except Exception:
        return []


def dropbox_search_update(self, context):
    """
    Callback cuando se escribe en la barra de búsqueda.
    Selecciona automáticamente el primer item si existe y repinta la UI.
    """
    try:
        wm = context.window_manager
        items = compute_filtered_items(context)
        if items:
            first_id = items[0][0]
            # Asegurarse de que la propiedad Enum exista antes de establecer
            if hasattr(wm, "dropbox_preview_enum"):
                try:
                    wm.dropbox_preview_enum = first_id
                except Exception:
                    # si falla al asignar (p.ej. valor no válido), lo ignoramos
                    pass

        # Forzar repintado global (más seguro que filtrar por tipo de área)
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    except Exception as e:
        print(f"[dropbox_search_update] Error: {e}")


classes = (
    PropTag,
    LayoutCompanionPreview,
    PROPS_OT_DropBoxAuthenticate,
    PROPS_OT_DropBoxRefreshPreviews,
    PROPS_OT_DropBoxImportBlend,
    PROPS_OT_DropBoxLogout
)


def register_dropbox():
    if is_dropbox_installed():
        for cls in classes:
            bpy.utils.register_class(cls)

        bpy.types.WindowManager.layout_companion_previews = bpy.props.CollectionProperty(
            type=LayoutCompanionPreview)

        # Propiedad de búsqueda (update dispara la selección automática y repintado)
        if not hasattr(bpy.types.WindowManager, "dropbox_search"):
            bpy.types.WindowManager.dropbox_search = bpy.props.StringProperty(
                name="Buscar",
                description="Filtrar assets por nombre / tags",
                default="",
                update=dropbox_search_update
            )

        # Enum dinámico para previews (items toma la lista filtrada)
        if not hasattr(bpy.types.WindowManager, "dropbox_preview_enum"):
            bpy.types.WindowManager.dropbox_preview_enum = bpy.props.EnumProperty(
                name="Dropbox Previews",
                items=_get_filtered_enum_items
            )
    else:
        bpy.utils.register_class(INSTALL_OT_dependencies)


def unregister_dropbox():
    if is_dropbox_installed():
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)

        if hasattr(bpy.types.WindowManager, "dropbox_search"):
            del bpy.types.WindowManager.dropbox_search

        if "dropbox" in preview_collections:
            bpy.utils.previews.remove(preview_collections["dropbox"])
            del preview_collections["dropbox"]

        if hasattr(bpy.types.WindowManager, "dropbox_preview_enum"):
            del bpy.types.WindowManager.dropbox_preview_enum
        del bpy.types.WindowManager.layout_companion_previews
    else:
        bpy.utils.unregister_class(INSTALL_OT_dependencies)
