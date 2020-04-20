bl_info = {
    "name": "B3D format (.b3d)",
    "author": "Guillaume Cartier",
    "version": (0, 0, 1),
    "blender": (2, 82, 0),
    "description": "Import / Export B3D files",
    "location": "File > Import-Export",
    "category": "Import-Export"
}

import bpy
import os

from bpy.utils import (
    register_class,
    unregister_class,
    )
from bpy_extras.io_utils import (
    ExportHelper,
    ImportHelper,
    )
from bpy.props import (
    StringProperty,
    )
from bpy.types import (
    Operator,
    TOPBAR_MT_file_export,
    TOPBAR_MT_file_import,
    )
from io_scene_b3d.import_b3d import (
    import_b3d,
    )
from io_scene_b3d.export_b3d import (
    export_b3d,
    )

together_models =  os.path.expanduser("~/Documents/Together/test/assets/model/")

# register
def register():
    classes = ( HandleImport, HandleExport )
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.TOPBAR_MT_file_import.append(HandleImport.menu_func)
    bpy.types.TOPBAR_MT_file_export.append(HandleExport.menu_func)

def unregister():
    classes = ( HandleImport, HandleExport )
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    bpy.types.TOPBAR_MT_file_import.remove(HandleImport.menu_func)
    bpy.types.TOPBAR_MT_file_export.remove(HandleExport.menu_func)

# import
class HandleImport(Operator, ImportHelper):

    bl_idname = "import.b3d"
    bl_label = "Import B3D"
    bl_description = "Import from B3D format (.b3d)"

    filename_ext = ".b3d"
    filter_glob : StringProperty(default="*.b3d", options={'HIDDEN'})

    @staticmethod
    def menu_func(self, context):
        self.layout.operator(HandleImport.bl_idname, text="B3D Format (.b3d)")

    def execute(self, context):
        import_b3d(self, self.filepath)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        self.filepath = together_models
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# export
class HandleExport(Operator, ExportHelper):

    bl_idname = "export.b3d"
    bl_label = "Export B3D"
    bl_description = "Export to B3D format (.b3d)"

    filename_ext = ".b3d"
    filter_glob : StringProperty(default="*.b3d", options={'HIDDEN'})
    
    @staticmethod
    def menu_func(self, context):
        default_path = bpy.data.filepath.replace(".blend", ".b3d")
        opts = self.layout.operator(HandleExport.bl_idname, text="B3D Format (.b3d)")
        opts.filepath = default_path

    def execute(self, context):
        export_b3d(self, self.filepath)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if not bpy.context.object:
            self.report({'ERROR'}, 'No active object to export')
            return {'CANCELLED'}
        elif bpy.context.object.type != 'MESH':
            self.report({'ERROR'}, 'Only mesh objects can be exported')
            return {'CANCELLED'}
        else:
            self.filepath = together_models + "_Idle.b3d"
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
