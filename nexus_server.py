import http.server
import socketserver
import threading
import json
import queue
import bpy
import os
from .nexus_api import NexusAPI

# --- QUEUES ---
_download_queue = queue.Queue()  # Items to be downloaded from the cloud
_import_queue = queue.Queue()    # Items already downloaded, ready for Blender
_queue_poller_registered = False

# --- GLOBAL COUNTERS ---
_total_queued = 0
_total_downloaded = 0
_total_imported = 0
_total_skipped = 0
_current_asset = ""
_lock = threading.Lock()

# --- DUPLICATE DETECTION ---
_existing_assets = set()  # Snapshot of asset names already in the Blender file
_assets_snapshot_ready = False

def _snapshot_existing_assets():
    """Main-thread timer: snapshots all asset-marked object names in the current file."""
    global _existing_assets, _assets_snapshot_ready
    try:
        names = set()
        for obj in bpy.data.objects:
            if obj.asset_data is not None:
                names.add(obj.name.lower())
        _existing_assets = names
        _assets_snapshot_ready = True
        print(f"[WUABO Nexus] Asset snapshot: {len(names)} existing assets found in file")
    except Exception as e:
        print(f"[WUABO Nexus] Snapshot error: {e}")
        _existing_assets = set()
        _assets_snapshot_ready = True
    return None  # One-shot timer

def get_queue_size():
    """Returns (download_count, import_count)"""
    return _download_queue.qsize(), _import_queue.qsize()

def get_progress():
    """Returns full progress dict for /status endpoint and UI."""
    return {
        "total_queued": _total_queued,
        "total_downloaded": _total_downloaded,
        "total_imported": _total_imported,
        "total_skipped": _total_skipped,
        "download_pending": _download_queue.qsize(),
        "import_pending": _import_queue.qsize(),
        "current_asset": _current_asset,
        "is_done": _total_queued > 0 and (_total_imported + _total_skipped) >= _total_queued and _download_queue.empty() and _import_queue.empty()
    }

def reset_counters():
    """Reset all batch counters and snapshot existing assets."""
    global _total_queued, _total_downloaded, _total_imported, _total_skipped, _current_asset, _assets_snapshot_ready
    with _lock:
        _total_queued = 0
        _total_downloaded = 0
        _total_imported = 0
        _total_skipped = 0
        _current_asset = ""
        _assets_snapshot_ready = False
    # Schedule snapshot on main thread (safe bpy access)
    bpy.app.timers.register(_snapshot_existing_assets, first_interval=0.0)

def _download_worker():
    """Background thread that downloads files as fast as possible."""
    global _total_downloaded, _total_skipped, _current_asset
    
    while True:
        asset_name = _download_queue.get()
        if asset_name is None: break
        
        # --- DUPLICATE CHECK: Skip if asset already exists in Blender file ---
        if _assets_snapshot_ready and asset_name.lower() in _existing_assets:
            with _lock:
                _total_skipped += 1
                _total_downloaded += 1  # Count as "processed" for progress
            print(f"[WUABO Nexus] SKIPPED (already exists) [{_total_downloaded}/{_total_queued}]: {asset_name}")
            _download_queue.task_done()
            continue
        
        try:
            from . import nexus_cache
            from .nexus_ops import download_only, cached_search
            
            # 1. Resolve path
            props = bpy.context.scene.wn_props
            api = NexusAPI(props.api_port)
            results = nexus_cache.search_cache(asset_name, limit=10)
            
            if not results:
                ok, api_results = cached_search(api, asset_name)
                if ok and api_results: results = api_results

            if results:
                # Filter for model files strictly
                results = [r for r in results if r.lower().endswith(('.ydr', '.yft', '.ydd'))]
                
                if results:
                    # Exact basename match first
                    exact = [r for r in results if os.path.splitext(os.path.basename(r))[0].lower() == asset_name.lower()]
                    pool = exact if exact else results
                    
                    # Base .yft over _hi.yft
                    base_results = [r for r in pool if not r.lower().endswith('_hi.yft')]
                    best_match = base_results[0] if base_results else pool[0]
                    
                    # 2. Download to unique sub-folder
                    base_temp = bpy.path.abspath(props.temp_dir)
                    asset_folder = os.path.join(base_temp, asset_name)
                    os.makedirs(asset_folder, exist_ok=True)
                    
                    success = download_only(best_match, asset_folder, api)
                    
                    if success:
                        _import_queue.put({"name": asset_name, "path": best_match, "folder": asset_folder})
                        with _lock:
                            _total_downloaded += 1
                        print(f"[WUABO Nexus] Downloaded [{_total_downloaded}/{_total_queued}]: {asset_name}")
                    else:
                        with _lock:
                            _total_downloaded += 1
                        print(f"[WUABO Nexus] Download FAILED [{_total_downloaded}/{_total_queued}]: {asset_name}")
            else:
                with _lock:
                    _total_downloaded += 1
                print(f"[WUABO Nexus] Not found [{_total_downloaded}/{_total_queued}]: {asset_name}")
                
        except Exception as e:
            with _lock:
                _total_downloaded += 1
            print(f"[WUABO Nexus] Download error for {asset_name}: {e}")
        finally:
            _download_queue.task_done()

def _process_next_in_queue():
    """Called by Blender timer (Main Thread). Processes the IMPORT queue."""
    global _total_imported, _current_asset
    
    try:
        if not bpy.context or not hasattr(bpy.context.scene, "wn_props"):
            return 1.0
            
        props = bpy.context.scene.wn_props
        if props.is_working:
            return 0.5  # Check again soon
            
    except Exception:
        return 1.0

    if _import_queue.empty():
        return 1.0

    item = _import_queue.get()
    asset_name = item["name"]
    asset_path = item["path"]
    asset_folder = item["folder"]

    with _lock:
        _current_asset = asset_name

    print(f"[WUABO Nexus] Importing [{_total_imported + 1}/{_total_queued}]: {asset_name}")

    try:
        from .nexus_ops import import_local_asset
        import_local_asset(asset_path, asset_folder, bpy.context)
        with _lock:
            _total_imported += 1
    except Exception as e:
        with _lock:
            _total_imported += 1
        print(f"[WUABO Nexus] Import error: {e}")

    return 0.2  # Import next quickly since files are already local


class NexusRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == '/status':
            self._send_json(get_progress())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b"WUABO Nexus Server is Active")

    def do_POST(self):
        global _total_queued
        
        if self.path == '/import':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                asset_name = data.get('asset_name')
                if asset_name:
                    _download_queue.put(asset_name)
                    with _lock:
                        _total_queued += 1
                    self._send_json({
                        "status": "queued", 
                        "asset": asset_name, 
                        "total_queued": _total_queued
                    })
                else:
                    self._send_json({"status": "error", "message": "Missing asset_name"}, 400)
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)

        elif self.path == '/reset':
            reset_counters()
            from .nexus_ops import clear_search_cache
            clear_search_cache()
            self._send_json({"status": "ok", "message": "Counters and cache reset"})

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        return

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

_server = None
_workers = []

def start_server(port=5556):
    global _server, _queue_poller_registered, _workers
    if _server: return

    if not _queue_poller_registered:
        bpy.app.timers.register(_process_next_in_queue, first_interval=1.0, persistent=True)
        _queue_poller_registered = True

    # Start 5 Download Workers
    if not _workers:
        for _ in range(5):
            t = threading.Thread(target=_download_worker, daemon=True)
            t.start()
            _workers.append(t)

    def _run():
        global _server
        try:
            _server = ThreadedTCPServer(("", port), NexusRequestHandler)
            print(f"[WUABO Nexus Server] Running on port {port}")
            _server.serve_forever()
        except Exception as e:
            print(f"[WUABO Nexus Server] Fatal Error: {e}")
            _server = None

    threading.Thread(target=_run, daemon=True).start()

def stop_server():
    global _server, _queue_poller_registered
    if _server:
        try:
            _server.shutdown()
            _server.server_close()
        except: pass
        _server = None
    
    if _queue_poller_registered:
        try: bpy.app.timers.unregister(_process_next_in_queue)
        except: pass
        _queue_poller_registered = False
    print("[WUABO Nexus Server] Stopped")
