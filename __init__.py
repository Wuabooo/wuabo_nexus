bl_info = {
    "name": "WUABO Nexus",
    "author": "Antigravity",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > WUABO",
    "description": "Premium GTA V Asset Bridge for CodeWalker & Sollumz",
    "category": "Import-Export",
}

import bpy
from . import nexus_props, nexus_ops, nexus_ui, nexus_server

def register():
    nexus_props.register()
    nexus_ops.register()
    nexus_ui.register()
    nexus_server.start_server()
    print("[WUABO Nexus] Registered successfully")

def unregister():
    nexus_server.stop_server()
    nexus_ui.unregister()
    nexus_ops.unregister()
    nexus_props.unregister()
    print("[WUABO Nexus] Unregistered")

if __name__ == "__main__":
    register()
