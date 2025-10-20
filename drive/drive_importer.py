import bpy
import tempfile
import os
import json
from pathlib import Path
import bpy.utils.previews
from difflib import SequenceMatcher
import shutil
import base64

#region VARIABLLES

preview_collections = {}
CS_ID = "R09DU1BYLXlycHlFdFhVVEYxdk51UGRsY3Ryc0FhZTU5Wlc=" 
CONFIG_PATH = Path(__file__).parent / "config.json"
TOKEN_PATH = Path(__file__).parent / "token.json"

SESSION_TEMP_DIR = Path(tempfile.gettempdir()) / "blender_drive_session"
SHARED_FOLDER_ID = None

SCOPES = ["https://www.googleapis.com/auth/drive"]

class PropTag(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()

class LayoutCompanionPreview(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    colaborador: bpy.props.StringProperty()
    descripcion: bpy.props.StringProperty()
    image_path: bpy.props.StringProperty()
    json_filename: bpy.props.StringProperty()
    json_id: bpy.props.StringProperty()
    parent_id: bpy.props.StringProperty()
    tags: bpy.props.CollectionProperty(type=PropTag)

#endregion

#region ACCOUNT SERVICE


def load_drive_config(folder_key="C_FOLDER_ID"):
    global SHARED_FOLDER_ID
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    SHARED_FOLDER_ID = cfg.get(folder_key)
    if not SHARED_FOLDER_ID:
        raise ValueError(f"{folder_key} no encontrado en config.json")
    return cfg


def get_drive_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import base64, json
    from pathlib import Path

    global SHARED_FOLDER_ID
    
    # Cargar config de log.json
    cfg_data = None
    with open(Path(__file__).parent / "log.json", "r") as f:
        cfg_data = json.load(f)["installed"]
        
    # Cargar ID de carpeta compartida
    load_drive_config()

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error al intentar refrescar el token: {e}. Iniciando autenticación completa.")
                creds = None
                
        if not creds or not creds.valid:
            c_s = base64.b64decode(CS_ID).decode('utf-8')
            cfg_data["client_secret"] = c_s
            
            flow = InstalledAppFlow.from_client_config(
                {"installed": cfg_data}, SCOPES)
            
            creds = flow.run_local_server(port=0)

        # Guardar token
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
        
    service = build("drive", "v3", credentials=creds)
    return service

#endregion

#region IMPORT

class DRIVE_OT_ImportCollabBlend(bpy.types.Operator):
    bl_idname = "prop.drive_import_blend"
    bl_label = "Import"
    bl_description = "Importa el prop seleccionado desde Google Drive"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from googleapiclient.errors import HttpError
        from .drive_importer import get_active_drive_preview

        active_preview = get_active_drive_preview(context)
        if not active_preview:
            self.report({'ERROR'}, "No se ha seleccionado ningún asset.")
            return {'CANCELLED'}

        json_base = os.path.splitext(active_preview.json_filename)[0]
        blend_name = json_base + ".blend"
        parent_id = active_preview.parent_id or SHARED_FOLDER_ID

        try:
            import_blend_from_drive(context,None,"any",blend_name,parent_id)

            self.report({'INFO'}, f"{blend_name} importado correctamente.")
            return {'FINISHED'}

        except FileNotFoundError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        except RuntimeError as e:
            # La función utilitaria ya convierte errores HTTP y otros en RuntimeError
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        except HttpError as e:
            self.report({'ERROR'}, f"Error HTTP: {e}")
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error inesperado: {e}")
            print("ImportCollabBlend Error:", e)
            return {'CANCELLED'}

#endregion

#region PREVIEWS

class DRIVE_OT_RefreshPreviews(bpy.types.Operator):
    bl_idname = "prop.drive_refresh_previews"
    bl_label = ""
    bl_description = "Recarga la lista de assets desde Google Drive"

    def execute(self, context):
        try:
            previews = fetch_drive_assets()
            if previews:
                register_drive_previews(previews)
            self.report({'INFO'}, "Previews cargados desde Drive")
        except Exception as e:
            self.report({'ERROR'}, f"Error al refrescar: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}

#region Threading download (for collabs)

def fetch_drive_assets():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import requests
    
    creds = get_drive_service()._http.credentials
    token = creds.token
    temp_folder = get_temp_folder()
    previews = []

    all_files = list_folder_recursive(get_drive_service(), SHARED_FOLDER_ID)
    file_index = {}
  
    for f in all_files:
        parent = f.get("parents", [SHARED_FOLDER_ID])[0]
        file_index.setdefault(parent, {})[f["name"]] = f

    json_files = [f for f in all_files if f["name"].lower().endswith(".json")]

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    def process_file(file_meta):
        try:
            data = read_json_from_drive_session(session, file_meta["id"])
            
            local_json = temp_folder / file_meta["name"]
            with open(local_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            image_path = None
            thumbnail_name = data.get("thumbnail")
            if thumbnail_name:
                parent_id = file_meta.get("parents", [SHARED_FOLDER_ID])[0]
                thumb = file_index.get(parent_id, {}).get(thumbnail_name)
                if thumb:
                    local_thumb = temp_folder / thumbnail_name
                    try:
                        download_file_session(session, thumb["id"], str(local_thumb))
                        image_path = str(local_thumb)
                    except Exception as e:
                        print(f"[Drive] Error descargando thumbnail {thumbnail_name}: {e}")

            raw_tags = data.get("tags", [])
            if not isinstance(raw_tags, list):
                raw_tags = [raw_tags]

            return {
                "name": data.get("nombre_demostrativo", file_meta["name"]),
                "image_path": image_path,
                "tags": [str(t).strip() for t in raw_tags if str(t).strip()],
                "descripcion": data.get("descripcion", ""),
                "colaborador": data.get("colaborador", ""),
                "json_filename": file_meta["name"],
                "json_id": file_meta["id"],
                "parent_id": file_meta.get("parents", [SHARED_FOLDER_ID])[0]
            }

        except Exception as e:
            print(f"[Drive] Error procesando {file_meta.get('name')}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=10) as executor: 
        futures = [executor.submit(process_file, f) for f in json_files]
        for future in as_completed(futures):
            result = future.result()
            if result:
                previews.append(result)

    session.close()
    return previews

def download_file_session(session, file_id, local_path):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    
    with session.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(131072):
                f.write(chunk)
    print(f"[Drive] Descargado: {os.path.basename(local_path)}")

def read_json_from_drive_session(session, file_id):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

#endregion

def download_file(service, file_id, local_path, wm=None):
    from googleapiclient.http import MediaIoBaseDownload

    file_metadata = service.files().get(fileId=file_id, fields="size, name").execute()
    file_size = int(file_metadata.get("size", 0))
    file_name = file_metadata.get("name", "archivo")

    print(f"Descargando {file_name} ({file_size / (1024*1024):.2f} MB)...")

    request = service.files().get_media(fileId=file_id)
    with open(local_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False

        while not done:
            status, done = downloader.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                if wm:
                    wm.progress_update(percent)

    return local_path


def import_blend_from_drive(context, file_id=None, type="any", file_name=None, parent_id=None):

    from googleapiclient.errors import HttpError

    wm = context.window_manager
    scene = context.scene

    try:
        service = get_drive_service()
    except Exception as e:
        raise RuntimeError(f"Drive no configurado: {e}")

    temp_folder = get_temp_folder()
    actual_file_id = None  # ✅ Variable unificada para el ID del archivo

    try:
        wm.progress_begin(0, 100)
        wm.progress_update(10)
        
        if file_id:
            actual_file_id = file_id  # ✅ Usar el ID proporcionado
            if not file_name:
                try:
                    file_metadata = service.files().get(
                        fileId=file_id, 
                        fields="name"
                    ).execute()
                    file_name = file_metadata.get("name", f"asset_{file_id}.blend")
                    print(f"[Drive] Nombre obtenido: {file_name}")
                except Exception as e:
                    print(f"[Drive] No se pudo obtener nombre: {e}")
                    file_name = f"asset_{file_id}.blend"
        else:
            if not file_name:
                raise ValueError("Debe proporcionar file_id o file_name")
            
            parent_id = parent_id or SHARED_FOLDER_ID
        
            q = f"name = '{file_name}' and '{parent_id}' in parents and trashed = false"
            resp = service.files().list(q=q, fields="files(id, name)").execute()
            files = resp.get("files", [])
            
            if not files:
                raise FileNotFoundError(f"No se encontró {file_name} en Drive")
            
            actual_file_id = files[0]["id"]  # ✅ Asignar a la variable unificada
            print(f"[Drive] Archivo encontrado: ID={actual_file_id}")
        
        if not actual_file_id:
            raise ValueError("No se pudo obtener el ID del archivo")
        
        if not file_name.lower().endswith('.blend'):
            file_name += '.blend'
        
        local_blend_path = temp_folder / file_name
        
        wm.progress_update(20)
        
        download_file(service, actual_file_id, str(local_blend_path), wm=wm)
        
        wm.progress_update(60)
        
        if not local_blend_path.exists():
            raise RuntimeError(f"El archivo no se descargó correctamente: {file_name}")
        
        with bpy.data.libraries.load(str(local_blend_path), link=False) as (data_from, data_to):
            if not data_from.collections:
                raise RuntimeError(f"No se encontraron collections en {file_name}")
            data_to.collections = list(data_from.collections)

        wm.progress_update(80)
        
        imported_collections = {col.name: col for col in data_to.collections if col}
        root_collections = []

        if getattr(scene, "resource_import_origin_camera", False):
            try:
                bpy.ops.resource.place_origin(origin_type="camera")
            except Exception as e:
                print(f"[Drive] No se pudo aplicar origen de cámara: {e}")

        for col in imported_collections.values():
            if type != "mapa":
                for obj in [o for o in col.objects if o.parent is None]:
                    obj.location = scene.cursor.location

            is_child = any(col.name in [child.name for child in p.children]
                           for p in imported_collections.values())
            if not is_child:
                root_collections.append(col)

        for root in root_collections:
            if root.name not in scene.collection.children:
                scene.collection.children.link(root)

        wm.progress_update(100)
        print(f"[Drive] ✓ {file_name} importado correctamente")

    except HttpError as e:
        error_msg = f"Error HTTP al descargar archivo: {e}"
        print(f"[Drive] {error_msg}")
        raise RuntimeError(error_msg)
    except FileNotFoundError as e:
        print(f"[Drive] {str(e)}")
        raise  # Re-lanzar como FileNotFoundError para mantener el tipo
    except Exception as e:
        error_msg = f"Error importando archivo: {e}"
        print(f"[Drive] {error_msg}")
        raise RuntimeError(str(e))
    finally:
        wm.progress_end()
        if 'local_blend_path' in locals() and local_blend_path.exists():
            try:
                os.remove(local_blend_path)
                print(f"[Drive] Archivo temporal eliminado: {file_name}")
            except Exception as e:
                print(f"[Drive] No se pudo eliminar temporal: {e}")
                

class DRIVE_OT_DeletePermProp(bpy.types.Operator):
    bl_idname = "prop.drive_delete"
    bl_label = "Delete Prop from Drive"
    bl_description = "Elimina el prop seleccionado de Drive (¡cuidado, es permanente!)"

    def execute(self, context):
        active_preview = get_active_drive_preview(context)
        if not active_preview:
            self.report({'ERROR'}, "No se ha seleccionado ningún asset para eliminar.")
            return {'CANCELLED'}

        try:
            service = get_drive_service()
        except Exception as e:
            self.report({'ERROR'}, f"Drive no configurado: {e}")
            return {'CANCELLED'}

        json_id = active_preview.json_id
        parent_id = active_preview.parent_id or SHARED_FOLDER_ID

        json_name = active_preview.json_filename
        blend_name = os.path.splitext(json_name)[0] + ".blend"
        thumbnail_name = None

        try:
            temp_folder = get_temp_folder()
            cached_json = temp_folder / json_name
            if cached_json.exists():
                try:
                    with open(cached_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        thumbnail_name = data.get("thumbnail")
                except Exception:
                    pass
            else:
                temp_json = temp_folder / json_name
                download_file(service, json_id, str(temp_json))
                with open(temp_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    thumbnail_name = data.get("thumbnail")
                try:
                    os.remove(temp_json)
                except:
                    pass
        except Exception as e:
            print(f"[Drive] No se pudo obtener thumbnail desde {json_name}: {e}")

        deleted_files = []
        errors = []

        try:
            service.files().delete(fileId=json_id).execute()
            deleted_files.append(json_name)
        except HttpError as e:
            errors.append(f"{json_name}: {e}")
        except Exception as e:
            errors.append(f"{json_name}: {e}")

        try:
            q = f"name = '{blend_name}' and '{parent_id}' in parents and trashed = false"
            resp = service.files().list(q=q, fields="files(id, name)").execute()
            files = resp.get("files", [])
            if files:
                try:
                    service.files().delete(fileId=files[0]["id"]).execute()
                    deleted_files.append(blend_name)
                except Exception as e:
                    errors.append(f"{blend_name}: {e}")
        except Exception as e:
            errors.append(f"{blend_name}: {e}")

        if thumbnail_name:
            try:
                q = f"name = '{thumbnail_name}' and '{parent_id}' in parents and trashed = false"
                resp = service.files().list(q=q, fields="files(id, name)").execute()
                files = resp.get("files", [])
                if files:
                    try:
                        service.files().delete(fileId=files[0]["id"]).execute()
                        deleted_files.append(thumbnail_name)
                    except Exception as e:
                        errors.append(f"{thumbnail_name}: {e}")
            except Exception as e:
                errors.append(f"{thumbnail_name}: {e}")

        if deleted_files:
            self.report({'INFO'}, "Prop eliminado permanentemente: " + ", ".join(deleted_files))
        if errors:
            self.report({'ERROR'}, "Errores: " + ", ".join(map(str, errors)))

        return {'FINISHED'}

#endregion

#region CACHE

class DRIVE_OT_CleanupCollabCache(bpy.types.Operator):
    bl_idname = "props.cleanup_cache"
    bl_label = "Limpiar Caché"
    bl_description = "Elimina todos los archivos temporales de la carpeta de caché"

    def execute(self, context):
        try:
            clear_temp_folder()
            wm = bpy.context.window_manager
            wm.layout_companion_previews.clear()
            self.report({'INFO'}, "Caché limpiada con éxito.")
        except Exception as e:
            self.report({'ERROR'}, f"Error al limpiar caché: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}

def get_temp_folder():
    SESSION_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_TEMP_DIR

def clear_temp_folder():
    if SESSION_TEMP_DIR.exists():
        shutil.rmtree(SESSION_TEMP_DIR, ignore_errors=True)

#endregion

#region PREVIEWS

def list_folder_recursive(service, folder_id):
    files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, parents, mimeType)",
            pageToken=page_token
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files

def register_drive_previews(previews):
    temp_folder = get_temp_folder()
    pcoll = preview_collections.get("drive")
    if not pcoll:
        pcoll = bpy.utils.previews.new()
        pcoll.my_previews_dir = str(temp_folder)
        pcoll.my_previews = []
        preview_collections["drive"] = pcoll

    enum_items = []
    for i, item in enumerate(previews):
        image_path = item.get("image_path")
        if not image_path:
            continue
        
        filename = os.path.basename(image_path)
        thumb = pcoll.get(filename)
        if not thumb:
            try:
                thumb = pcoll.load(filename, image_path, 'IMAGE')
            except Exception as e:
                print(f"[register_drive_previews] Error cargando imagen {image_path}: {e}")
                continue
        enum_items.append((filename, item["name"], item.get("descripcion", ""), thumb.icon_id, i))

    pcoll.my_previews = enum_items

    # Guardar info en WindowManager.collection
    store_previews_in_context(previews)

    # Forzar update de búsqueda / selección
    try:
        wm = bpy.context.window_manager
        drive_search_update(wm, bpy.context)
    except Exception:
        pass

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
        preview.json_id = item.get("json_id", "")
        preview.parent_id = item.get("parent_id", "")

        preview.tags.clear()
        for t in item.get("tags", []):
            tag_item = preview.tags.add()
            tag_item.name = t

def get_active_drive_preview(context):
    wm = context.window_manager
    selected_name = getattr(wm, "drive_preview_enum", "")
    for item in wm.layout_companion_previews:
        if item.image_path and os.path.basename(item.image_path) == selected_name:
            return item
    return None

#endregion

#region PAGINACION Y BUSQUEDA

def compute_filtered_items_generic(all_items, search_term, get_name_func=None, get_tags_func=None, get_desc_func=None):
    """
    Función genérica de filtrado con scoring mejorado
    Prioriza coincidencias exactas de palabras
    """
    from difflib import SequenceMatcher
    
    search = (search_term or "").strip().lower()
    if not search:
        return all_items
    
    search_words = search.replace('_', ' ').replace('-', ' ').split()
    
    scored = []
    for item in all_items:
        name = get_name_func(item) if get_name_func else str(item)
        name_l = name.lower()
        
        tags = []
        if get_tags_func:
            tags = [str(t).lower() for t in (get_tags_func(item) or [])]
        
        score_exact_words = 0.0
        matched_words = 0
        
        for search_word in search_words:
            # Buscar coincidencia exacta en tags
            if search_word in tags:
                score_exact_words += 2.0  # Peso alto para coincidencia exacta
                matched_words += 1
            # Buscar coincidencia parcial en nombre
            elif search_word in name_l:
                score_exact_words += 1.0
                matched_words += 1
        
        # Si no hay palabras coincidentes, score muy bajo
        if matched_words == 0:
            score_exact_words = 0.0
        
        # === SCORING POR SIMILITUD DE SECUENCIA ===
        score_name = SequenceMatcher(None, search, name_l).ratio() * 0.5
        
        # === SCORING POR TAGS (similitud) ===
        score_tags = 0.0
        if get_tags_func:
            for t in tags:
                s = SequenceMatcher(None, search, t).ratio()
                score_tags = max(score_tags, s * 0.3)
        
        # === SCORING POR DESCRIPCIÓN ===
        score_desc = 0.0
        if get_desc_func:
            desc = get_desc_func(item) or ""
            desc_l = desc.lower()
            if desc_l:
                score_desc = SequenceMatcher(None, search, desc_l).ratio() * 0.3
        
        # === BOOST POR POSICIÓN ===
        boost = 0.0
        if name_l.startswith(search):
            boost += 1.5
        elif search in name_l:
            boost += 0.5
        
        # === BONUS POR PORCENTAJE DE PALABRAS COINCIDENTES ===
        if search_words:
            match_ratio = matched_words / len(search_words)
            boost += match_ratio * 2.0
        
        # SCORE FINAL: Priorizar coincidencias exactas
        score = score_exact_words + score_name + score_tags + score_desc + boost
        
        scored.append((score, item))
    
    # Ordenar por score descendente
    scored.sort(key=lambda x: x[0], reverse=True)

    # Filtrar por umbral mínimo
    threshold = 0.5
    filtered = [item for score, item in scored if score >= threshold]
    
    # Si no hay resultados, devolver top 5
    if not filtered:
        filtered = [item for score, item in scored[:5]]
    
    return filtered

def compute_filtered_items(context):
    wm = context.window_manager
    pcoll = preview_collections.get("drive")
    if not pcoll or not getattr(wm, "layout_companion_previews", None):
        return []

    all_items = list(pcoll.my_previews) if getattr(pcoll, "my_previews", None) else []
    search = (wm.drive_search or "").strip().lower()
    
    if not search:
        return all_items

    # Crear mapping de tags
    tags_map = {}
    for p in wm.layout_companion_previews:
        try:
            key = os.path.basename(p.image_path) if p.image_path else None
            if not key:
                continue
            tags_map[key] = [t.name.lower() for t in p.tags]
        except Exception:
            continue
    
    def get_name(item):
        return item[1]
    
    def get_desc(item):
        return item[2] 
    
    def get_tags(item):
        identifier = item[0]
        return tags_map.get(identifier, [])
    
    from difflib import SequenceMatcher
    scored = []
    for item in all_items:
        identifier, name, desc, icon_id, orig_index = item
        name_l = (name or "").lower()
        desc_l = (desc or "").lower()
        tags = tags_map.get(identifier, [])

        score_name = SequenceMatcher(None, search, name_l).ratio()
        score_desc = SequenceMatcher(None, search, desc_l).ratio() if desc_l else 0.0
        score_tags = 0.0
        for t in tags:
            s = SequenceMatcher(None, search, t).ratio()
            if s > score_tags:
                score_tags = s

        boost = 0.0
        if search in name_l:
            boost += 0.35
        if name_l.startswith(search):
            boost += 0.15

        score = max(score_name, score_tags, score_desc) + boost
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    
    threshold = 0.20
    filtered = [itm for score, itm in scored if score >= threshold]
    if not filtered:
        filtered = [itm for score, itm in scored[:10]]

    result = []
    for idx, itm in enumerate(filtered):
        identifier, name, desc, icon_id, _ = itm
        result.append((identifier, name, desc, icon_id, idx))

    return result


def _get_filtered_enum_items(self, context):
    try:
        return compute_filtered_items(context)
    except Exception:
        return []

def drive_search_update(self, context):
    try:
        wm = context.window_manager
        items = compute_filtered_items(context)
        if items:
            first_id = items[0][0]
            if hasattr(wm, "drive_preview_enum"):
                try:
                    wm.drive_preview_enum = first_id
                except Exception:
                    pass

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    except Exception as e:
        print(f"[drive_search_update] Error: {e}")

#endregion

#region REGISTERS

classes = (
    PropTag,
    LayoutCompanionPreview,
    DRIVE_OT_CleanupCollabCache,
    DRIVE_OT_RefreshPreviews,
    DRIVE_OT_ImportCollabBlend,
    DRIVE_OT_DeletePermProp
)


def register_drive():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.drive_advance_settings = bpy.props.BoolProperty(
        name="Advance Settings",
        options={'SKIP_SAVE'},
        default=False
    )
    bpy.types.WindowManager.layout_companion_previews = bpy.props.CollectionProperty(
        type=LayoutCompanionPreview)

    # Propiedad de búsqueda (update dispara la selección automática y repintado)
    if not hasattr(bpy.types.WindowManager, "drive_search"):
        bpy.types.WindowManager.drive_search = bpy.props.StringProperty(
            name="Buscar",
            description="Filtrar assets por nombre / tags",
            default="",
            update=drive_search_update
        )

    # Enum dinámico para previews (items toma la lista filtrada)
    if not hasattr(bpy.types.WindowManager, "drive_preview_enum"):
        bpy.types.WindowManager.drive_preview_enum = bpy.props.EnumProperty(
            name="Drive Previews",
            items=_get_filtered_enum_items
        )


def unregister_drive():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.WindowManager, "drive_search"):
        del bpy.types.WindowManager.drive_search

    if "drive" in preview_collections:
        bpy.utils.previews.remove(preview_collections["drive"])
        del preview_collections["drive"]

    if hasattr(bpy.types.WindowManager, "drive_preview_enum"):
        del bpy.types.WindowManager.drive_preview_enum
    del bpy.types.WindowManager.layout_companion_previews
#endregion