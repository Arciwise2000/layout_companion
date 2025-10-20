import bpy
import os
import re
from pathlib import Path
from datetime import datetime
from .drive_importer import get_drive_service, load_drive_config, get_temp_folder
from .drive_importer import import_blend_from_drive
from googleapiclient.errors import HttpError
from bpy.props import CollectionProperty, IntProperty, StringProperty, BoolProperty
from .drive_importer import compute_filtered_items_generic
from bpy.utils import previews

#region PROPERTIES

class FilesListItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Name")
    file_id: StringProperty(name="File ID")
    json_id: StringProperty(name="JSON ID")
    folder_id: StringProperty(name="Folder ID")
    thumb_id: StringProperty(name="Thumb ID", default="")
    
    type: StringProperty(name="Type", default="")
    rigger: StringProperty(name="Rigger", default="")
    last_update: StringProperty(name="Last Update", default="")
    version: StringProperty(name="Version", default="")
    
    json_loaded: BoolProperty(name="JSON Loaded", default=False)
    thumb_icon: StringProperty(name="Thumbnail Icon", default="")
    visible: BoolProperty(name="visible", default=True)

class FILES_UL_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        
        item_name = Path(item.name).stem
        if item_name.lower().endswith(".blend"):
            icon_name = 'BLENDER'
        elif item_name.lower().endswith(".rar") or item_name.lower().endswith(".zip"): 
            icon_name = 'COMPRESSED'
        elif "." not in item.name:
            icon_name = 'FILE_FOLDER'
        else:
            icon_name = 'FILE'

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            display_name = Path(item.name).stem
            finalname = display_name
            if finalname.lower().endswith(".json"):
                finalname = finalname[:-5] # Remove the 5 characters: ".json"
        
            if finalname.lower().endswith(".blend"):
                finalname = finalname[:-6] # Remove the 6 characters: ".blend"
                
            row = layout.row(align=True)
            if icon_name != "COMPRESSED":
                row.label(text=finalname, icon=icon_name)
            else:
                custom_icons = getattr(context.window_manager, "custom_icons", None)
                row.label(text=finalname, icon_value=custom_icons["compressed"].icon_id)
            if item.version:
                row.label(text=f"v{item.version}", icon='INFO')
                
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
    
    def filter_items(self, context, data, propname):
        """Filtrado con scoring de similitud - máximo 5 resultados"""
        scene = context.scene
        items = getattr(data, propname)
        
        flt_flags = [0] * len(items)
        flt_neworder = []
        
        search_term = scene.files_list_filter.strip()
        
        if not search_term:
            flt_flags = [self.bitflag_filter_item] * len(items)
            return flt_flags, flt_neworder
        
        all_items = list(items)
        
        def get_name(item):
            return item.name
        
        def get_tags(item):
            name_parts = Path(item.name).stem.lower().split('_')
            return name_parts
        
        filtered_items = compute_filtered_items_generic(
            all_items,
            search_term,
            get_name_func=get_name,
            get_tags_func=get_tags
        )
        
        filtered_items = filtered_items[:10]
        
        filtered_set = set(filtered_items)
        
        for i, item in enumerate(items):
            if item in filtered_set:
                flt_flags[i] = self.bitflag_filter_item
        
        if filtered_items:
            item_to_index = {id(item): i for i, item in enumerate(items)}
            
            new_order = []
            for filtered_item in filtered_items:
                original_index = item_to_index.get(id(filtered_item))
                if original_index is not None:
                    new_order.append(original_index)
            
            for i in range(len(items)):
                if i not in new_order:
                    new_order.append(i)
            
            flt_neworder = new_order
        
        return flt_flags, flt_neworder

#endregion


#region FILTER CALLBACK

def update_files_filter(self, context):
    for area in context.screen.areas:
        area.tag_redraw()

#endregion



#region PREVIEW COLLECTION

preview_collections = {}

def get_preview_collection():
    global preview_collections
    
    if "drive_thumbnails" not in preview_collections:
        pcoll = previews.new()
        preview_collections["drive_thumbnails"] = pcoll
    
    return preview_collections["drive_thumbnails"]


def load_thumbnail_to_preview(thumb_path, thumb_id):
    pcoll = get_preview_collection()
    
    if thumb_id in pcoll:
        return thumb_id
    
    if not os.path.exists(thumb_path):
        print(f"[Drive] Thumbnail no encontrado: {thumb_path}")
        return None
    
    try:
        pcoll.load(thumb_id, thumb_path, 'IMAGE')
        return thumb_id
    except Exception as e:
        print(f"[Drive] Error cargando preview: {e}")
        return None


def clear_preview_collection():
    global preview_collections
    
    if "drive_thumbnails" in preview_collections:
        previews.remove(preview_collections["drive_thumbnails"])
        del preview_collections["drive_thumbnails"]
        print("[Drive] Preview collection limpiada")

#endregion

#region JSON & THUMBNAIL LOADING

def extract_drive_id_from_link(link: str) -> str:
    if not link:
        return ""

    match = re.search(r"/d/([a-zA-Z0-9_-]+)", link)
    if not match:
        match = re.search(r"id=([a-zA-Z0-9_-]+)", link)
    if match:
        return match.group(1)
    return ""

def read_json_from_drive(file_id, token):
    import requests
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print(f"[Drive] Timeout leyendo JSON: {file_id}")
        return None
    except Exception as e:
        print(f"[Drive] Error leyendo JSON: {e}")
        return None

def load_json_for_item(item):
    if not item.json_id:
        print(f"[Drive] No hay JSON ID para {item.name}")
        return False
    
    try:
        service = get_drive_service()
        creds = service._http.credentials
        token = creds.token
        
        json_data = read_json_from_drive(item.json_id, token)
        
        if json_data:
            update_item_with_json(item, json_data)
            return True
        else:
            print(f"[Drive] No se pudo leer el JSON para {item.name}")
            return False
            
    except Exception as e:
        print(f"[Drive] Error cargando JSON: {e}")
        return False

def update_item_with_json(item, json_data):
    if not json_data:
        return
    
    item.type = json_data.get("tipo", "")
    
    rig_link = json_data.get("rigLink", "")
    thumb_link = json_data.get("thumbnailLink", "")
    
    if rig_link:
        item.file_id = extract_drive_id_from_link(rig_link)
    
    if thumb_link:
        item.thumb_id = extract_drive_id_from_link(thumb_link)
    
    rigger_data = json_data.get("modelador", {})
    if isinstance(rigger_data, dict):
        rigger_values = [str(v) for v in rigger_data.values() if v and str(v).lower() != "none"]
        item.rigger = " ".join(rigger_values) if rigger_values else "Unknown"
    else:
        item.rigger = str(rigger_data) if rigger_data else "Unknown"
    
    last_update = json_data.get("fechaUltimaActualizacion", "")
    if last_update:
        try:
            dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
            item.last_update = dt.strftime("%d/%m/%y")
        except Exception as e:
            print(f"[Drive] Error parseando fecha '{last_update}': {e}")
            item.last_update = last_update
    
    item.version = str(json_data.get("version", ""))
    item.json_loaded = True
    
    print(f"[Drive] ✓ Metadata cargada: {item.name}")

def download_drive_thumbnail(file_id):
    import requests
    
    if not file_id:
        return None
    
    try:
        service = get_drive_service()
        creds = service._http.credentials
        token = creds.token
        headers = {"Authorization": f"Bearer {token}"}
        temp_dir = get_temp_folder()

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        elif "png" in content_type:
            ext = ".png"
        else:
            ext = ".jpg"  # Default
        
        thumb_path = temp_dir / f"thumb_{file_id}{ext}"

        with open(thumb_path, "wb") as f:
            f.write(response.content)

        print(f"[Drive] ✓ Thumbnail descargado: {file_id}")
        return str(thumb_path)

    except requests.exceptions.Timeout:
        print(f"[Drive] Timeout descargando thumbnail: {file_id}")
        return None
    except Exception as e:
        print(f"[Drive] Error descargando thumbnail: {e}")
        return None


def on_file_selection_changed(scene):
    if len(scene.files_list_items) == 0:
        return

    if not scene.get_json_automatically:
        return

    idx = scene.files_list_index
    if idx < 0 or idx >= len(scene.files_list_items):
        return

    item = scene.files_list_items[idx]
    
    if not item.json_loaded and item.folder_id:
        try:
            json_data = load_json_for_item(item)
            if json_data:
                update_item_with_json(item, json_data)
        except Exception as e:
            print(f"[Drive] Error cargando JSON para {item.name}: {e}")
    
    if item.thumb_id and not item.thumb_icon and scene.show_horns_thumbnail:
        try:
            thumb_path = download_drive_thumbnail(item.thumb_id)
            if thumb_path:
                preview_id = load_thumbnail_to_preview(thumb_path, item.thumb_id)
                if preview_id:
                    item.thumb_icon = preview_id
        except Exception as e:
            print(f"[Drive] Error cargando thumbnail para {item.name}: {e}")

#endregion

#region OPERATORS

class DRIVE_OT_ListMainFolders(bpy.types.Operator):
    bl_idname = "drive.list_main_folders"
    bl_label = "Get Trends"
    bl_description = "Obtiene las carpetas dentro de la carpeta principal"

    def execute(self, context):
        scene = context.scene
        clean_folders(context)
        
        try:
            cfg = load_drive_config("M_FOLDER_ID")
            main_folder_id = cfg.get("M_FOLDER_ID")

            if not main_folder_id:
                self.report({'ERROR'}, "No se encontró M_FOLDER_ID en la configuración")
                return {'CANCELLED'}

            service = get_drive_service()
            query = f"'{main_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = service.files().list(
                q=query,
                spaces='drive',
                fields="files(id, name)",
                orderBy="name"  # Ordenar alfabéticamente
            ).execute()

            folders = results.get('files', [])

            for f in folders:
                item = scene.files_list_items.add()
                item.name = f['name']
                item.file_id = f['id']
                item.visible = True
                
            self.report({'INFO'}, f"{len(folders)} carpetas encontradas")
            return {'FINISHED'}

        except HttpError as e:
            self.report({'ERROR'}, f"Error de Google Drive: {e}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error: {e}")
            print(f"[Drive] Error listando carpetas: {e}")
            return {'CANCELLED'}


class DRIVE_OT_EnterToFolder(bpy.types.Operator):
    bl_idname = "drive.open_folder"
    bl_label = "Open Folder"
    bl_description = "Abre la carpeta seleccionada y muestra sus archivos JSON"

    @classmethod
    def poll(cls, context):
        return (len(context.scene.files_list_items) > 0 and 
                context.scene.drive_main_page)

    def execute(self, context):
        scene = context.scene

        if len(scene.files_list_items) == 0:
            self.report({'WARNING'}, "No hay carpetas para abrir")
            return {'CANCELLED'}

        idx = scene.files_list_index
        if idx < 0 or idx >= len(scene.files_list_items):
            self.report({'WARNING'}, "Selecciona una carpeta primero")
            return {'CANCELLED'}

        selected_folder = scene.files_list_items[idx]

        try:
            folder_id = selected_folder.file_id
            
            if not folder_id:
                self.report({'ERROR'}, "ID de carpeta inválido")
                return {'CANCELLED'}

            service = get_drive_service()
            clean_folders(context)
            
            def list_drive_files_recursive(parent_id, depth=0):
                if depth > 10:
                    return []
                
                query = f"'{parent_id}' in parents and trashed=false"
                results = service.files().list(
                    q=query,
                    spaces='drive',
                    fields="files(id, name, mimeType, size)",
                    pageSize=1000
                ).execute()

                files = results.get('files', [])
                all_files = []

                for f in files:
                    name = f["name"]
                    mime = f["mimeType"]

                    if mime == "application/vnd.google-apps.folder":
                        if name.lower() in ["old", "obsolete", "backup"]:
                            continue
                        sub_files = list_drive_files_recursive(f["id"], depth + 1)
                        all_files.extend(sub_files)
                    else:
                        f["parent_id"] = parent_id
                        all_files.append(f)

                return all_files

            all_files = list_drive_files_recursive(folder_id)

            if not all_files:
                self.report({'INFO'}, f"La carpeta '{selected_folder.name}' está vacía")
                return {'CANCELLED'}

            excluded_extensions = {'.blend', '.png', '.jpg', '.jpeg', '.txt', '.pdf'}
            filtered_files = [
                f for f in all_files
                if f["name"].lower().endswith('.json') and 
                   Path(f["name"]).suffix.lower() not in excluded_extensions
            ]

            if len(filtered_files) == 0:
                self.report({'INFO'}, f"No hay archivos en '{selected_folder.name}'")
                return {'CANCELLED'}

            for f in filtered_files:
                item = scene.files_list_items.add()
                original_name = f["name"]
                
                item.name = original_name
                item.json_id = f["id"]
                item.folder_id = f.get("parent_id", "")
                item.file_id = ""
                item.visible = True 
            
            scene.drive_main_page = False
            scene.active_drive_folder_id = folder_id
            
            self.report({'INFO'}, f"{len(filtered_files)} archivos encontrados")
            return {'FINISHED'}

        except HttpError as e:
            self.report({'ERROR'}, f"Error de Google Drive: {e}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error: {e}")
            print(f"[Drive] Error: {e}")
            return {'CANCELLED'}


class DRIVE_OT_ImportFile(bpy.types.Operator):
    bl_idname = "drive.import_file"
    bl_label = "Import"
    bl_description = "Importa el archivo .blend del item seleccionado"

    @classmethod
    def poll(cls, context):
        scene = context.scene
        idx = scene.files_list_index
        return not (len(scene.files_list_items) == 0 or idx < 0 or idx >= len(scene.files_list_items))

    def execute(self, context):
        scene = context.scene
        idx = scene.files_list_index
        selected_item = scene.files_list_items[idx]

        if not selected_item.json_loaded:
            self.report({'WARNING'}, "Cargando información del archivo...")
            load_json_for_item(selected_item)
            
            if not selected_item.json_loaded:
                self.report({'ERROR'}, "No se pudo cargar la información del archivo")
                return {'CANCELLED'}

        if not selected_item.file_id:
            self.report({'ERROR'}, "No se encontró el link del archivo .blend en el JSON")
            return {'CANCELLED'}
        
        item_name = Path(selected_item.name).stem
        if item_name.lower().endswith(".rar") or item_name.lower().endswith(".zip"):
            url = f"https://drive.google.com/file/d/{selected_item.file_id}/view?usp=drivesdk"
            bpy.ops.wm.url_open(url=url)
            return {'FINISHED'}
        try:
            import_blend_from_drive(
                context, 
                file_id=selected_item.file_id,
                type=selected_item.type
            )
            
            self.report({'INFO'}, f"✓ {item_name} importado")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error importando: {str(e)}")
            return {'CANCELLED'}


class DRIVE_OT_RefreshFolders(bpy.types.Operator):
    bl_idname = "drive.refresh_folders"
    bl_label = "Refresh"
    bl_description = "Vuelve al inicio y recarga las carpetas"

    def execute(self, context):
        scene = context.scene
        
        try:
            clean_folders(context)
            scene.drive_main_page = True
            scene.active_drive_folder_id = ""
            bpy.ops.drive.list_main_folders()
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error: {e}")
            return {'CANCELLED'}


class DRIVE_OT_ClearFilter(bpy.types.Operator):
    bl_idname = "drive.clear_filter"
    bl_label = "Clear Filter"
    bl_description = "Limpia el filtro de búsqueda"

    def execute(self, context):
        context.scene.files_list_filter = ""
        return {'FINISHED'}

#endregion

#region UTILITIES

def clean_folders(context):
    scene = context.scene
    scene.files_list_items.clear()
    bpy.ops.drive.clear_filter()

#endregion

#region REGISTER

classes = (
    FilesListItem,
    FILES_UL_List,
    DRIVE_OT_ListMainFolders,
    DRIVE_OT_RefreshFolders,
    DRIVE_OT_EnterToFolder,
    DRIVE_OT_ImportFile,
    DRIVE_OT_ClearFilter
)


def register_horns_resources():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.horns_advance_settings = BoolProperty(
        name="Advanced Settings",
        description="Mostrar opciones avanzadas",
        default=False,
        options={'SKIP_SAVE'}
    )
    bpy.types.Scene.drive_main_page = BoolProperty(
    name="",
    description="",
    default=True
    )
    bpy.types.Scene.get_json_automatically = BoolProperty(
        name="Auto-load metadata",
        description="Cargar automáticamente información al seleccionar archivos",
        default=True
    )
    bpy.types.Scene.show_horns_thumbnail = BoolProperty(
        name="Show file thumbnail",
        description="Muestra un preview del .blend a importar",
        default=True
    )
    
    bpy.types.Scene.active_drive_folder_id = StringProperty(
        name="Active Drive Folder ID",
        default=""
    )
    
    bpy.types.Scene.files_list_items = CollectionProperty(type=FilesListItem)
    
    bpy.types.Scene.files_list_index = IntProperty(
        default=0,
        update=lambda self, context: on_file_selection_changed(context.scene)
    )
    
    bpy.types.Scene.files_list_filter = StringProperty(
        name="Filter",
        description="Filtrar archivos por nombre, tipo, rigger o versión",
        default="",
        update=update_files_filter
    )


def unregister_horns_resources():
    # Limpiar preview collection ANTES de unregister
    clear_preview_collection()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.drive_main_page
    del bpy.types.Scene.active_drive_folder_id
    del bpy.types.Scene.get_json_automatically
    del bpy.types.Scene.horns_advance_settings
    del bpy.types.Scene.show_horns_thumbnail
    del bpy.types.Scene.files_list_items
    del bpy.types.Scene.files_list_index
    del bpy.types.Scene.files_list_filter

#endregion