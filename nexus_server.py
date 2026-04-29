import http.server
import socketserver
import threading
import json
import bpy
from .nexus_api import NexusAPI

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
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            asset_name = data.get('asset_name')
            if asset_name:
                print(f"[WUABO Nexus Server] Received import request for: {asset_name}")
                
                # Trigger search and import in Blender
                def _trigger():
                    from .nexus_ops import import_asset_by_path
                    from . import nexus_cache
                    import re
                    
                    props = bpy.context.scene.wn_props
                    api = NexusAPI(props.api_port)
                    
                    # 1. Try exact match from cache (higher limit to allow exact match filtering to work on tuning vehicles)
                    results = nexus_cache.search_cache(asset_name, limit=200)
                    
                    # 2. Try exact match from API
                    if not results:
                        ok, api_results = api.search_file(asset_name)
                        if ok and api_results:
                            results = api_results
                    
                    # Filter for model files strictly
                    if results:
                        results = [r for r in results if r.lower().endswith(('.ydr', '.yft', '.ydd'))]
                    
                    # 3. Fallback: Try multiple variations
                    if not results:
                        # Try variations: "metro1_add_002" -> ["metro1_add", "metro1", "metro"]
                        parts = re.split(r'[_.]', asset_name)
                        variations = []
                        for i in range(len(parts) - 1, 0, -1):
                            variations.append("_".join(parts[:i]))
                        
                        # Also try removing numbers from the end of the first part
                        first_part_no_num = re.sub(r'\d+$', '', parts[0])
                        if first_part_no_num and first_part_no_num != parts[0]:
                            variations.append(first_part_no_num)

                        for var in variations:
                            print(f"[WUABO Nexus Server] Trying fallback variation: {var}")
                            ok, fallback_results = api.search_file(var)
                            if ok and fallback_results:
                                # Filter for model files (.ydr, .yft, .ydd)
                                models = [r for r in fallback_results if r.lower().endswith(('.ydr', '.yft', '.ydd'))]
                                if models:
                                    models.sort(key=len)
                                    results = [models[0]]
                                    print(f"[WUABO Nexus Server] Found match via variation '{var}': {results[0]}")
                                    break
                    
                    if results:
                        import os
                        
                        # 1. Prioritize exact basename matches (e.g. comet5.yft over comet5_wing_f.yft)
                        exact_matches = []
                        for r in results:
                            base = os.path.splitext(os.path.basename(r))[0].lower()
                            if base == asset_name.lower():
                                exact_matches.append(r)
                                
                        pool = exact_matches if exact_matches else results
                        
                        # 2. Prioritize base .yft over _hi.yft if both exist
                        base_results = [r for r in pool if not r.lower().endswith('_hi.yft')]
                        best_match = base_results[0] if base_results else pool[0]
                        
                        print(f"[WUABO Nexus Server] Importing: {best_match}")
                        import_asset_by_path(best_match, bpy.context)
                    else:
                        print(f"[WUABO Nexus Server] No match found for: {asset_name} (tried variations)")
                    return None
                
                bpy.app.timers.register(_trigger, first_interval=0.0)
                self._send_json({"status": "queued", "asset": asset_name})
            else:
                self._send_json({"status": "error", "message": "Missing asset_name"}, 400)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        # Suppress logging to console to keep it clean
        return

_server = None

def start_server(port=5556):
    global _server
    if _server:
        return
    
    def _run():
        global _server
        try:
            handler = NexusRequestHandler
            _server = socketserver.TCPServer(("", port), handler)
            print(f"[WUABO Nexus Server] Running on port {port}")
            _server.serve_forever()
        except Exception as e:
            print(f"[WUABO Nexus Server] Error: {e}")

    threading.Thread(target=_run, daemon=True).start()

def stop_server():
    global _server
    if _server:
        _server.shutdown()
        _server.server_close()
        _server = None
        print("[WUABO Nexus Server] Stopped")
