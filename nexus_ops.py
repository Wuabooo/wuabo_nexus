import bpy
import os
import threading
import time
import subprocess
from bpy.types import Operator
from .nexus_api import NexusAPI
from . import nexus_cache, nexus_utils

# Global process handle
_API_PROCESS = None

@bpy.app.handlers.persistent
def on_load_post(dummy):
    # This runs when a new file is opened or created
    # We check if the API is still alive and update the status
    for scene in bpy.data.scenes:
        if hasattr(scene, "wn_props"):
            props = scene.wn_props
            api = NexusAPI(props.api_port)
            # Use a quick ping to check if alive (short timeout to avoid hang)
            try:
                ok, _ = api.get_config(timeout=0.2)
                props.is_api_running = ok
                if ok:
                    props.status_message = "API Connected"
            except:
                props.is_api_running = False

class WN_OT_start_api(Operator):
    bl_idname = "wn.start_api"
    bl_label = "Start Nexus API"
    bl_description = "Launch the CodeWalker API process"

    def execute(self, context):
        global _API_PROCESS
        props = context.scene.wn_props
        
        if _API_PROCESS and _API_PROCESS.poll() is None:
            self.report({'WARNING'}, "API is already running")
            return {'CANCELLED'}

        addon_dir = os.path.dirname(__file__)
        exe_path = os.path.join(addon_dir, "bin", "CodeWalker.API.exe")
        
        if not os.path.exists(exe_path):
            self.report({'ERROR'}, f"API Executable not found at: {exe_path}")
            return {'CANCELLED'}

        # --- Read Config from JSON File ---
        config_path = os.path.join(addon_dir, "bin", "Config", "userconfig.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if "GTAPath" in cfg: props.gta_path = cfg["GTAPath"]
                    if "CodewalkerOutputDir" in cfg: props.temp_dir = cfg["CodewalkerOutputDir"]
                    if "EnableMods" in cfg: props.enable_mods = cfg["EnableMods"]
                self.report({'INFO'}, "Settings loaded from userconfig.json")
            except Exception as e:
                print(f"[WUABO Nexus] Failed to read userconfig.json: {e}")

        try:
            import ctypes
            # Request Elevation (Admin) and SHOW window (1)
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, None, os.path.dirname(exe_path), 1)
            
            props.is_api_running = True
            props.status_message = "API Started"
            self.report({'INFO'}, "Nexus API Started (Check UAC Prompt)")

            # Auto-Sync after start
            def _auto_sync():
                api = NexusAPI(props.api_port)
                # Wait for API to be responsive
                try:
                    ok, _ = api.get_config()
                    if ok:
                        # Call sync logic
                        bpy.ops.wn.sync_config()
                        props.status_message = "API Started & Synced"
                        return None # Stop timer
                except:
                    pass
                return 1.0 # Check again in 1s

            bpy.app.timers.register(_auto_sync, first_interval=2.0)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to start API: {e}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class WN_OT_stop_api(Operator):
    bl_idname = "wn.stop_api"
    bl_label = "Stop Nexus API"
    bl_description = "Close the CodeWalker API process"

    def execute(self, context):
        props = context.scene.wn_props
        api = NexusAPI(props.api_port)
        
        # Ask the API to close itself
        api.shutdown()
        
        # Cleanup status
        props.is_api_running = False
        props.status_message = "API Stopped"
        self.report({'INFO'}, "Nexus API Stopped")
        return {'FINISHED'}

class WN_OT_clear_search(Operator):
    bl_idname = "wn.clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear search results and query"

    def execute(self, context):
        props = context.scene.wn_props
        props.search_results.clear()
        props.search_query = ""
        props.status_message = "Ready"
        return {'FINISHED'}

class WN_OT_sync_config(Operator):
    bl_idname = "wn.sync_config"
    bl_label = "Sync Config"
    bl_description = "Sync Blender settings with CodeWalker.API"

    def execute(self, context):
        props = context.scene.wn_props
        api = NexusAPI(props.api_port)
        
        # Try to fetch existing config if local path is empty
        if not props.gta_path:
            ok_get, current_cfg = api.get_config()
            if ok_get and current_cfg.get("GTAPath"):
                props.gta_path = current_cfg["GTAPath"]
                self.report({'INFO'}, f"Fetched GTA Path from API: {props.gta_path}")

        ok, msg = api.set_config(
            gta_path=props.gta_path,
            output_dir=props.temp_dir,
            enable_mods=props.enable_mods
        )
        
        if ok:
            self.report({'INFO'}, "Config synced successfully")
        else:
            self.report({'ERROR'}, f"Sync failed: {msg}")
        
        return {'FINISHED'}

class WN_OT_build_cache(Operator):
    bl_idname = "wn.build_cache"
    bl_label = "Build Cache"
    bl_description = "Index all assets for instant search"

    def execute(self, context):
        props = context.scene.wn_props
        if props.is_working:
            self.report({'WARNING'}, "Another task is in progress")
            return {'CANCELLED'}

        props.is_working = True
        props.status_message = "Building cache..."

        def _thread():
            ok, msg = nexus_cache.build_cache(props.api_port)
            
            def _done():
                props.is_working = False
                props.status_message = msg
                props.is_cache_built = ok
                if ok:
                    props.cache_info = msg # This updates the text below the button
                return None
            
            bpy.app.timers.register(_done, first_interval=0.0)

        threading.Thread(target=_thread, daemon=True).start()
        return {'FINISHED'}

class WN_OT_search(Operator):
    bl_idname = "wn.search"
    bl_label = "Search"
    
    def execute(self, context):
        props = context.scene.wn_props
        query = props.search_query.strip()
        
        if not query:
            self.report({'WARNING'}, "Enter a search term")
            return {'CANCELLED'}

        props.search_results.clear()
        
        # Try cache first
        results = nexus_cache.search_cache(query)
        
        # If no cache or no results, try API
        if not results:
            api = NexusAPI(props.api_port)
            ok, api_results = api.search_file(query)
            if ok:
                results = api_results

        # Sort results: .yft/.ydr first, then ignore +hi.ytd/awc if possible
        def search_priority(x):
            lx = x.lower()
            if lx.endswith(".yft"): return 0
            if lx.endswith(".ydr"): return 1
            if lx.endswith(".ydd"): return 2
            return 8

        results.sort(key=lambda x: (search_priority(x), x.lower()))

        for res in results:
            # Strictly whitelist only 3D models (.ydr, .yft, .ydd)
            lx = res.lower()
            if not (lx.endswith(".ydr") or lx.endswith(".yft") or lx.endswith(".ydd")):
                continue
            
            print(f"[WUABO Nexus] Adding to results: {res}")
            item = props.search_results.add()
            item.name = res
            
        props.status_message = f"Found {len(props.search_results)} assets"
        print(f"[WUABO Nexus] Search complete. Total displayed: {len(props.search_results)}")
        return {'FINISHED'}

def import_asset_by_path(asset_path, context):
    """Core logic to import an asset by its full RPF path."""
    props = context.scene.wn_props
    temp_dir = bpy.path.abspath(props.temp_dir)
    api = NexusAPI(props.api_port)

    if not temp_dir or not os.path.isdir(temp_dir):
        print("[WUABO Nexus] Error: Invalid temp directory")
        return False

    props.is_working = True
    basename = os.path.basename(asset_path)
    props.status_message = f"Downloading {basename}..."

    def _thread():
        # 1. Determine files to download
        files_to_download = [asset_path]
        
        # Vehicle logic: get base and hi models together
        if asset_path.lower().endswith(".yft"):
            if not asset_path.lower().endswith("_hi.yft"):
                target_name = os.path.basename(asset_path).replace(".yft", "_hi.yft")
            else:
                target_name = os.path.basename(asset_path).replace("_hi.yft", ".yft")
                
            ok_s, res_s = api.search_file(target_name)
            if ok_s and res_s and res_s[0] not in files_to_download:
                files_to_download.append(res_s[0])
                print(f"[WUABO Nexus] Found paired model: {res_s[0]}")

        # 2. Download Model XMLs
        for f_path in files_to_download:
            props.status_message = f"Downloading {os.path.basename(f_path)}..."
            ok, msg = api.download_files(f_path, temp_dir, xml=True)
            if not ok:
                print(f"[WUABO Nexus] Warning: Failed to download {f_path}: {msg}")

        # 3. Deep Texture Discovery (for all files)
        paths_to_download = []
        for f_path in files_to_download:
            base_no_ext = os.path.splitext(os.path.basename(f_path))[0]
            
            # 1. Always try a YTD with the exact same name (Crucial for YDDs / Peds)
            ok_s, res_s = api.search_file(base_no_ext + ".ytd")
            if ok_s and res_s:
                if res_s[0] not in paths_to_download:
                    paths_to_download.append(res_s[0])
            
            # 2. Check XML internal TextureDictionary references (For YDR/YFT)
            xml_path = os.path.join(temp_dir, os.path.basename(f_path) + ".xml")
            if os.path.exists(xml_path):
                tex_dict_name = nexus_utils.get_texture_dictionary_name(xml_path)
                if tex_dict_name and tex_dict_name.lower() != base_no_ext.lower():
                    ok_s, res_s = api.search_file(tex_dict_name + ".ytd")
                    if ok_s and res_s:
                        if res_s[0] not in paths_to_download:
                            paths_to_download.append(res_s[0])
        
        # Shared textures
        is_vehicle = any(f.lower().endswith(".yft") for f in files_to_download)
        if is_vehicle:
            for share in ["vehshare.ytd", "vehshare_truck.ytd"]:
                ok_s, res_s = api.search_file(share)
                if ok_s and res_s: paths_to_download.append(res_s[0])

        if paths_to_download:
            api.download_files(list(set(paths_to_download)), temp_dir, xml=False)
            nexus_utils.flatten_textures(temp_dir)

        # 3. Import in Blender
        def _main_thread():
            try:
                if not hasattr(bpy.ops, "sollumz"):
                    _finish_work(props, "Sollumz not found!")
                    return
                
                existing_objs = set(bpy.data.objects)
                
                # Import all XMLs found for this asset
                xml_files = [f for f in os.listdir(temp_dir) if f.lower().endswith(".xml") and any(os.path.splitext(os.path.basename(p))[0] in f for p in files_to_download)]
                
                for xml_name in xml_files:
                    print(f"[WUABO Nexus] Importing to Blender: {xml_name}")
                    bpy.ops.sollumz.import_assets(directory=temp_dir, files=[{"name": xml_name}])
                
                new_objs = [o for o in bpy.data.objects if o not in existing_objs]
                _polish_import(new_objs, asset_path, props)
                
                props.status_message = f"Imported {basename}"
            except Exception as e:
                print(f"[WUABO Nexus] Import error: {e}")
                props.status_message = f"Error: {e}"
            finally:
                if props.clean_after_import:
                    print(f"[WUABO Nexus] Cleaning temp files in {temp_dir}...")
                    # Delete the XML and common texture types
                    for f in os.listdir(temp_dir):
                        if f.lower().endswith((".xml", ".dds", ".png", ".jpg", ".tga", ".ytd")):
                            try:
                                os.remove(os.path.join(temp_dir, f))
                            except Exception as e:
                                print(f"[WUABO Nexus] Could not delete {f}: {e}")
                
                props.is_working = False
            return None

        bpy.app.timers.register(_main_thread, first_interval=0.0)

    threading.Thread(target=_thread, daemon=True).start()
    return True

def _finish_work(props, msg):
    def _f():
        props.status_message = msg
        props.is_working = False
        return None
    bpy.app.timers.register(_f, first_interval=0.0)

def _polish_import(new_objects, asset_path, props):
    if not new_objects: return
    
    try:
        # Ensure we are in Object Mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Sollumz types to keep/remove
        COLLISION_TYPES = {"sollumz_bound_composite", "sollumz_bound_box", "sollumz_bound_sphere", 
                           "sollumz_bound_capsule", "sollumz_bound_cylinder", "sollumz_bound_disc", 
                           "sollumz_bound_geometry", "sollumz_bound_geometry_bvH"}

        # Find the main root (Drawable or Fragment)
        root = None
        for obj in new_objects:
            if getattr(obj, "sollum_type", "") in {"sollumz_drawable", "sollumz_fragment"}:
                root = obj
                break
        
        if props.drawable_only:
            geometries = []
            to_remove = []
            
            for obj in new_objects:
                if obj.name not in bpy.data.objects: continue
                s_type = getattr(obj, "sollum_type", "").lower()
                print(f"[WUABO Nexus] Debug: {obj.name} | SollumType: {s_type} | Type: {obj.type}")
                
                # UNIVERSAL GEOMETRY DETECTION
                # If it's a mesh and NOT a collision/bound type, we rescue it
                is_collision = "bound" in s_type or "collision" in s_type
                if obj.type == 'MESH' and not is_collision:
                    print(f"[WUABO Nexus] Rescuing visual mesh: {obj.name}")
                    geometries.append(obj)
                    
                    # Apply modifiers and Unparent
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)
                    for mod in list(obj.modifiers):
                        try: bpy.ops.object.modifier_apply(modifier=mod.name)
                        except: pass
                    
                    world_mat = obj.matrix_world.copy()
                    obj.parent = None
                    obj.matrix_world = world_mat
                    continue

                # Everything else that isn't a rescued mesh gets marked for removal
                # (Armatures, Dummies, Empty parents, Collisions)
                to_remove.append(obj)

            print(f"[WUABO Nexus] Geometries rescued: {len(geometries)}, Objects to remove: {len(to_remove)}")

            # 3. Final removal
            bpy.ops.object.select_all(action='DESELECT')
            for obj in to_remove:
                if obj.name in bpy.data.objects:
                    try: bpy.data.objects.remove(obj, do_unlink=True)
                    except: pass
            
            # 4. Join and Rename
            if geometries:
                geometries = [o for o in geometries if o.name in bpy.data.objects]
                if geometries:
                    bpy.ops.object.select_all(action='DESELECT')
                    for geo in geometries:
                        geo.select_set(True)
                    
                    bpy.context.view_layer.objects.active = geometries[0]
                    if len(geometries) > 1:
                        bpy.ops.object.join()
                    
                    root = bpy.context.view_layer.objects.active
                    root.name = os.path.splitext(os.path.basename(asset_path))[0]
                    root.sollum_type = 'sollumz_none' 

        if props.mark_as_asset and root:
            root.asset_mark()
            root.asset_generate_preview()

    except Exception as e:
        print(f"[WUABO Nexus] Polish Error: {e}")

class WN_OT_import(Operator):
    bl_idname = "wn.import_asset"
    bl_label = "Import"
    index: bpy.props.IntProperty()

    def execute(self, context):
        props = context.scene.wn_props
        if self.index < 0 or self.index >= len(props.search_results):
            return {'CANCELLED'}
        
        asset_path = props.search_results[self.index].name
        import_asset_by_path(asset_path, context)
        return {'FINISHED'}


classes = [
    WN_OT_start_api,
    WN_OT_stop_api,
    WN_OT_sync_config,
    WN_OT_build_cache,
    WN_OT_search,
    WN_OT_clear_search,
    WN_OT_import
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_post.append(on_load_post)
    # Initial check (using timer to avoid _RestrictData error during registration)
    bpy.app.timers.register(lambda: on_load_post(None), first_interval=1.0)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load_post)
