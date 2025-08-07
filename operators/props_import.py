import bpy
import dropbox
import json
import tempfile
from pathlib import Path

# Cargar configuración
def load_config():
    config_path = Path(__file__).parent / "dropbox/config.json"
    with open(config_path, "r") as f:
        return json.load(f)
    
config = load_config()
TOKEN = config["dropbox_token"]