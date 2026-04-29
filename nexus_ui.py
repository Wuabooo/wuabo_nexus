import bpy

class WN_PT_main_panel(bpy.types.Panel):
    bl_label = "WUABO NEXUS"
    bl_idname = "WN_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WUABO'

    def draw(self, context):
        layout = self.layout
        props = context.scene.wn_props
        
        # --- API Control ---
        if not props.is_api_running:
            box = layout.box()
            col = box.column(align=True)
            col.scale_y = 2.0
            col.operator("wn.start_api", text="START NEXUS BRIDGE", icon='PLAY')
            col.label(text="API must be running to search assets", icon='INFO')
            return

        # --- Header Section (Stop Button) ---
        row = layout.row()
        row.operator("wn.stop_api", text="Stop API", icon='QUIT')
        row.label(text="API ACTIVE", icon='CHECKMARK')

        # --- Status & Progress ---
        if props.is_working or props.status_message != "Ready":
            st_box = layout.box()
            col = st_box.column(align=True)
            col.label(text=props.status_message, icon='INFO')
            if props.is_working:
                col.progress(factor=props.progress / 100.0 if props.progress > 0 else 0.5)

        layout.separator()

        # --- Search Bar ---
        search_box = layout.box()
        col = search_box.column(align=True)
        row = col.row(align=True)
        row.prop(props, "search_query", text="", icon='VIEWZOOM')
        row.operator("wn.search", text="Search", icon='VIEWZOOM')
        
        # --- Import Options (Horizontal & Compact) ---
        row = layout.row(align=True)
        row.prop(props, "drawable_only", text="Static", toggle=True, icon='MESH_DATA')
        row.prop(props, "mark_as_asset", text="Asset", toggle=True, icon='ASSET_MANAGER')
        row.prop(props, "clean_after_import", text="Clean", toggle=True, icon='TRASH')
        row.prop(props, "enable_mods", text="Mods", toggle=True, icon='MODIFIER')

        # --- Search Results ---
        if len(props.search_results) > 0:
            layout.label(text=f"Results ({len(props.search_results)}):")
            res_box = layout.box()
            col = res_box.column(align=True)
            
            for i, result in enumerate(props.search_results):
                row = col.row(align=True)
                lx = result.name.lower()
                
                # Dynamic Icons
                ico = 'FILE_BLANK'
                if lx.endswith(".yft"): ico = 'CAR'
                elif lx.endswith(".ydr"): ico = 'OBJECT_DATAMODE'
                elif lx.endswith(".ytd"): ico = 'IMAGE_DATA'
                
                name = result.name.split("/")[-1]
                row.label(text=name, icon=ico)
                
                op = row.operator("wn.import_asset", text="Import")
                op.index = i

class WN_PT_settings_panel(bpy.types.Panel):
    bl_label = "Bridge Configuration"
    bl_idname = "WN_PT_settings_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WUABO'
    bl_parent_id = "WN_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        props = context.scene.wn_props
        return props.is_api_running

    def draw(self, context):
        props = context.scene.wn_props
        if not props.is_api_running:
            return

        layout = self.layout
        
        box = layout.box()
        col = box.column()
        col.label(text="API Connection", icon='URL')
        col.prop(props, "api_port")
        
        box = layout.box()
        col = box.column()
        col.label(text="File Paths", icon='FILE_FOLDER')
        col.prop(props, "gta_path", text="GTA V")
        col.prop(props, "temp_dir", text="Temp")
        
        layout.separator()
        
        col = layout.column(align=True)
        col.operator("wn.sync_config", text="Sync API Config", icon='FILE_REFRESH')
        col.operator("wn.build_cache", text="Rebuild Local Cache", icon='FILE_BACKUP')
        
        if props.is_cache_built:
            box = layout.box()
            box.label(text=props.cache_info, icon='CHECKMARK')

def register():
    bpy.utils.register_class(WN_PT_main_panel)
    bpy.utils.register_class(WN_PT_settings_panel)

def unregister():
    bpy.utils.unregister_class(WN_PT_settings_panel)
    bpy.utils.unregister_class(WN_PT_main_panel)
