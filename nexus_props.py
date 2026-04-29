import bpy
from bpy.props import (
    StringProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
    FloatProperty
)
from bpy.types import PropertyGroup

class NexusSearchResult(PropertyGroup):
    name: StringProperty(name="Path")


class WUABO_Nexus_Properties(PropertyGroup):
    # --- API Settings ---
    api_port: IntProperty(
        name="API Port",
        description="Port where CodeWalker.API is running",
        default=5555,
        min=1024,
        max=65535
    )
    
    gta_path: StringProperty(
        name="GTA V Path",
        description="Root folder of your GTA V installation",
        subtype='DIR_PATH'
    )
    
    temp_dir: StringProperty(
        name="Temp Directory",
        description="Folder for temporary XML and DDS files",
        subtype='DIR_PATH'
    )
    
    enable_mods: BoolProperty(
        name="Enable Mods",
        description="Include modded content in searches",
        default=False
    )
    
    # --- Search ---
    search_query: StringProperty(
        name="Search",
        description="Search for assets by name",
        default=""
    )
    
    search_results: CollectionProperty(type=NexusSearchResult)
    search_index: IntProperty(default=-1)
    
    # --- Import Options ---
    drawable_only: BoolProperty(
        name="Drawable Only",
        description="Keep only the visible mesh (removes collisions, armatures, etc.)",
        default=True
    )
    
    mark_as_asset: BoolProperty(
        name="Mark as Asset",
        description="Automatically add the imported object to the Asset Browser",
        default=True
    )
    
    clean_after_import: BoolProperty(
        name="Clean Temp Files",
        description="Delete XML and DDS files from temp folder after import",
        default=True
    )
    
    # --- Status ---
    status_message: StringProperty(name="Status", default="Ready")
    is_working: BoolProperty(default=False)
    progress: FloatProperty(name="Progress", default=0.0, min=0.0, max=100.0)
    
    # --- API Process ---
    is_api_running: BoolProperty(name="API Running", default=False)
    
    # --- Cache ---
    is_cache_built: BoolProperty(default=False)
    cache_info: StringProperty(name="Cache Info", default="Cache not built")

def register():
    from . import nexus_cache
    bpy.utils.register_class(NexusSearchResult)
    bpy.utils.register_class(WUABO_Nexus_Properties)
    bpy.types.Scene.wn_props = PointerProperty(type=WUABO_Nexus_Properties)
    
    # Check cache status on startup
    def check_init():
        if hasattr(bpy.context, "scene") and bpy.context.scene.wn_props:
            nexus_cache.init_cache_status(bpy.context.scene.wn_props)
        return None
    bpy.app.timers.register(check_init, first_interval=0.1)

def unregister():
    del bpy.types.Scene.wn_props
    bpy.utils.unregister_class(WUABO_Nexus_Properties)
    bpy.utils.unregister_class(NexusSearchResult)
