import http.server
import socketserver
import threading
import json
import queue
import bpy
from .nexus_api import NexusAPI

# Thread-safe import queue
_import_queue = queue.Queue()
_queue_poller_registered = False

def _process_next_in_queue():
    """Called by Blender timer (Main Thread). Processes one import at a time."""
    try:
        # Check if scene/props are accessible
        if not bpy.context or not hasattr(bpy.context.scene, "wn_props"):
            return 1.0
            
        props = bpy.context.scene.wn_props
        if props.is_working:
            return 1.0  # Still importing, wait
            
    except Exception:
        return 1.0

    if _import_queue.empty():
        return 1.0

    asset_name = _import_queue.get()
    print(f"[WUABO Nexus Server] Queue processing: {asset_name} (remaining: {_import_queue.qsize()})")

    try:
        from .nexus_ops import import_asset_by_path
        from . import nexus_cache
        import re
        import os

        api = NexusAPI(props.api_port)
        results = nexus_cache.search_cache(asset_name, limit=200)

        if not results:
            ok, api_results = api.search_file(asset_name)
            if ok and api_results:
                results = api_results

        if results:
            results = [r for r in results if r.lower().endswith(('.ydr', '.yft', '.ydd'))]

        if not results:
            parts = re.split(r'[_.]', asset_name)
            variations = []
            for i in range(len(parts) - 1, 0, -1):
                variations.append("_".join(parts[:i]))
            
            first_part_no_num = re.sub(r'\d+$', '', parts[0])
            if first_part_no_num and first_part_no_num != parts[0]:
                variations.append(first_part_no_num)

            for var in variations:
                ok, fallback_results = api.search_file(var)
                if ok and fallback_results:
                    models = [r for r in fallback_results if r.lower().endswith(('.ydr', '.yft', '.ydd'))]
                    if models:
                        models.sort(key=len)
                        results = [models[0]]
                        break

        if results:
            exact_matches = []
            for r in results:
                base = os.path.splitext(os.path.basename(r))[0].lower()
                if base == asset_name.lower():
                    exact_matches.append(r)
            
            pool = exact_matches if exact_matches else results
            base_results = [r for r in pool if not r.lower().endswith('_hi.yft')]
            best_match = base_results[0] if base_results else pool[0]

            print(f"[WUABO Nexus Server] Importing: {best_match}")
            import_asset_by_path(best_match, bpy.context)
        else:
            print(f"[WUABO Nexus Server] No match found for: {asset_name}")

    except Exception as e:
        print(f"[WUABO Nexus Server] Error processing queue item: {e}")

    return 0.5


class NexusRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"WUABO Nexus Server is Active")

    def do_POST(self):
        if self.path == '/import':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                asset_name = data.get('asset_name')
                if asset_name:
                    # WE ONLY PUSH TO QUEUE HERE. No bpy calls allowed in this thread!
                    _import_queue.put(asset_name)
                    self._send_json({"status": "queued", "asset": asset_name, "queue_size": _import_queue.qsize()})
                else:
                    self._send_json({"status": "error", "message": "Missing asset_name"}, 400)
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)

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

def start_server(port=5556):
    global _server, _queue_poller_registered
    if _server:
        return

    # 1. Register the poller strictly in the MAIN THREAD (here)
    if not _queue_poller_registered:
        print("[WUABO Nexus Server] Registering queue poller...")
        bpy.app.timers.register(_process_next_in_queue, first_interval=1.0, persistent=True)
        _queue_poller_registered = True

    def _run():
        global _server
        try:
            handler = NexusRequestHandler
            _server = ThreadedTCPServer(("", port), handler)
            print(f"[WUABO Nexus Server] Running on port {port}")
            _server.serve_forever()
        except Exception as e:
            print(f"[WUABO Nexus Server] Fatal Error: {e}")
            _server = None

    # Start server thread
    threading.Thread(target=_run, daemon=True).start()

def stop_server():
    global _server, _queue_poller_registered
    if _server:
        try:
            _server.shutdown()
            _server.server_close()
        except:
            pass
        _server = None
        
    if _queue_poller_registered:
        try:
            bpy.app.timers.unregister(_process_next_in_queue)
        except:
            pass
        _queue_poller_registered = False
    print("[WUABO Nexus Server] Stopped")


