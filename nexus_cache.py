import os
import json
import bpy
from .nexus_api import NexusAPI

CACHE_FILENAME = "nexus_cache.json"

_INTERNAL_CACHE = None

def get_cache_path():
    # Store in Documents/wuabo_nexus for persistence
    docs = os.path.expanduser("~/Documents")
    folder = os.path.join(docs, "wuabo_nexus")
    if not os.path.exists(folder):
        os.makedirs(folder)
    return os.path.join(folder, CACHE_FILENAME)

def save_cache(data):
    global _INTERNAL_CACHE
    try:
        with open(get_cache_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        _INTERNAL_CACHE = data
        return True
    except Exception as e:
        print(f"[WUABO Nexus] Cache save error: {e}")
        return False

def load_cache(force_reload=False):
    global _INTERNAL_CACHE
    if _INTERNAL_CACHE and not force_reload:
        return _INTERNAL_CACHE
        
    path = get_cache_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            _INTERNAL_CACHE = json.load(f)
            return _INTERNAL_CACHE
    except Exception as e:
        print(f"[WUABO Nexus] Cache load error: {e}")
        return None

def build_cache(api_port, progress_cb=None):
    api = NexusAPI(api_port)
    ok, assets = api.get_all_assets()
    if not ok:
        return False, f"API Error: {assets}"
    
    cache_data = {
        "version": 1,
        "assets": assets
    }
    
    if save_cache(cache_data):
        return True, f"Cache built with {len(assets)} assets"
    return False, "Failed to save cache file"

def search_cache(query, limit=100):
    cache_data = load_cache()
    if not cache_data:
        return []
    
    query = query.lower()
    results = []
    assets = cache_data.get("assets", [])
    
    for asset in assets:
        if query in asset.lower():
            results.append(asset)
            if len(results) >= limit:
                break
    return results

def find_ytd_in_cache(model_name, cache_data=None):
    if not cache_data:
        cache_data = load_cache()
    if not cache_data:
        return None
        
    target = model_name.lower() + ".ytd"
    for asset in cache_data.get("assets", []):
        if asset.lower().endswith(target):
            return asset
    return None

def init_cache_status(props):
    """Called on startup to check if cache exists."""
    cache_data = load_cache()
    if cache_data:
        count = len(cache_data.get("assets", []))
        props.is_cache_built = True
        props.cache_info = f"Cache ready ({count} assets)"
        return True
    return False
