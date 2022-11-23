
import numpy as np
from io import StringIO
import struct
import random
import os
import bpy
from array import array
from mathutils import (
    Vector,
    Matrix
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
)
from bpy.types import (
    Operator,
    Header,
    Menu,
    Panel,
    PropertyGroup,
)
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty,
)
from .utils import (
    console_notice,
    console_debug,
    console_debug_data,
    vecSanmodelToBlender,
    vecBlenderToSanmodel,
)

seg_names = ["vertices", "normals", "tangents", "uv1", "uv2 (boneweights)", "uv3", "colors", "indices", "bindposes"]
seg_vars = [3, 3, 4, 2, 2, 2, 4, 1, 16] # cf file structure
smd_old = None
smd = None
SAN_ENDIAN = "<"
SAN_VERTICES = 0
SAN_NORMALS = 1
SAN_TANGENTS = 2
SAN_UV1 = 3
SAN_UV2 = 4
SAN_UV3 = 5
SAN_COLORS = 6
SAN_INDICES = 7
SAN_BINDPOSES = 8
UV1_NAME = "UV1Map"
UV2_NAME = "UV2Map"
UV3_NAME = "UV3Map"

# int.from_bytes(b"\x00\x00\x00\xff", byteorder="big") # 255
# int.from_bytes(b"\x00\x00\x00\xff", byteorder="little") # 4278190080
# https://docs.python.org/3/library/struct.html
def reinterpret_float_to_int(float_value):
    return struct.unpack(SAN_ENDIAN+"i", struct.pack(SAN_ENDIAN+"f", float_value))[0]


class SanImportSettings(PropertyGroup):
    # internal properties
    path : StringProperty(
        name="sanmodel path",
        description="the path of the sanmodel",
        default = "...",
        options={'SKIP_SAVE'}
        )
    name : StringProperty(name="name", default = "...")
    vertices : StringProperty(name="vertices", default = "0")
    normals : StringProperty(name="normals", default = "0")
    tangents : StringProperty(name="tangents", default = "0")
    uv : StringProperty(name="uv", default = "0")
    uv2 : StringProperty(name="uv2", default = "0")
    uv3 : StringProperty(name="uv3", default = "0")
    colors : StringProperty(name="colors", default = "0")
    triangles : StringProperty(name="triangles", default = "0")
    bindposes : StringProperty(name="bones", default = "0")
    boneweights : StringProperty(name="boneweights", default = "0")  
    valid_file : BoolProperty(name="validation check", default = False)
    
    # user settings
    swap_yz_axis : BoolProperty(
        name="Swap Y and Z axis",
        description="Swap y and z coordinates of vertices",
        default = True
        )
    mirror_uv_vertically : BoolProperty(
        name="Mirror UV vertically",
        description="Blender handle some textures differently.",
        default = True
        )
    use_vertex_colors : BoolProperty(
        name="Use vertex colors",
        description="Enable or disable the use of vertex colors for triangles shading",
        default = False
        )
    use_alpha : BoolProperty(
        name="Use Alpha channel (transparency)",
        description="Enable or disable the use of Alpha channel of vertex colors for triangles shading",
        default = False
        )
    shading_nodes : BoolProperty(
        name="Generate shading nodes",
        description="Generate shading nodes depending on previous settings (vertex_color, uv)",
        default = False
        )
    
    # model_name is not used anymore for export, it may change later.
    # https://blender.stackexchange.com/questions/203442/how-to-pass-a-bpy-data-objects-bpy-data-materials-etc-to-an-operator-from-th
    model_name: StringProperty(
        name="Model name",
        description="the name of the model used when exporting",
        default="",
        maxlen=50,
        )

class SanmodelData():
    content: bytes
    name: StringIO
    segments: list
    
    def process_data(self, context):
        # read name
        try:
            self.name, self.content = self.content.split(b'\0', 1)
        except ValueError:
            console_notice("Error with the specified file, invalid data")
            return False
        self.name = self.name.decode()
        content_len = len(self.content)
        bsize = 4 # size for each value in bytes
        console_notice("model name: %s, content len: %d bytes, %d values" % (self.name, content_len, content_len/bsize))
        if (content_len % bsize) > 0:
            console_notice("Error with the specified file, invalid data: should be only 4 bytes number after the null terminated name")
            return False

        console_debug("---------------- File content (without the name) -----------------")
        console_debug_data(self.content)
        console_debug("---------------- END ---------------------------------------------")
        # convert bytes to floats
        self.content = np.array(list(struct.iter_unpack(SAN_ENDIAN+"f", self.content[0:content_len])), dtype=float).flatten()
        
        # build segments arrays
        self.segments = []
        global seg_names
        global seg_vars
        for i, vars in enumerate(seg_vars):
            if not len(self.content):
                console_notice("Error with the specified file, invalid data: missing data")
                return False
            segment_len = reinterpret_float_to_int(self.content[0]) * vars
            console_debug(f"[Read Process] segment[{i}]: {seg_names[i]}: {segment_len/seg_vars[i]}, {segment_len} values ({segment_len*4} bytes)")
            if (segment_len):
                # console_debug("slicing data:")
                data = self.content[1:1+segment_len]

                #reinterpret indices and boneWeights data as int
                if i == SAN_INDICES:
                    for j in range(len(data)):
                        data[j] = reinterpret_float_to_int(data[j])

                console_debug_data(data)
                self.segments.append(data) # will rebuild this as tuples later
                self.content = self.content[1+segment_len:]
            else:
                # console_debug("slicing nothing")
                self.content = self.content[1:]
                self.segments.append([])
        console_debug(f"data left: {len(self.content)}")
        if len(self.content):
            console_debug_data(self.content)
        if len(self.content):
            console_notice("Error with the specified file, invalid data: slicing left some data, this shouldn't be the case.")
            return False
        
        #reinterpret indices and boneWeights data as int
        #for i in range(7, 9):
        #    for j in range(len(self.segments[i])):
        #        self.segments[i][j] = reinterpret_float_to_int(self.segments[i][j]) # and automatically recasted as float because it's a float array
        
        # rebuild float arrays to tuple arrays, ex:
        # from : [0, 1, 2, 3, 4, 5, 6, 7, 8]
        # to : [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
        # tuple len is seg_vars[i]
        seg_vars[SAN_INDICES] = 3 # group indices as tuple(1,2,3) for 1 triangle/face
        r = len(seg_vars) - 1 # for now, ignore the last one (bindposes) 
        for i in range(r):
            tmp = []
            for j in range(len(self.segments[i])//seg_vars[i]):
                tmp.append(tuple(self.segments[i][j*seg_vars[i]:j*seg_vars[i]+seg_vars[i]]))
            self.segments[i] = tmp
        seg_vars[SAN_INDICES] = 1

        # SAN_INDICES: convert tuple(float,float,float) to tuple(int,int,int)
        self.segments[SAN_INDICES] = [tuple(map(int, t)) for t in self.segments[SAN_INDICES]]
        return True
    
    def create_obj(self, context):
        settings = context.scene.san_settings
        console_notice("building mesh...")
        mesh = bpy.data.meshes.new(self.name + "Mesh")

        #swap z and y axis to match unity
        vertices = self.segments[SAN_VERTICES][:]
        indices = self.segments[SAN_INDICES][:]
        if settings.swap_yz_axis:
            vertices = [vecSanmodelToBlender(v) for v in vertices]
            indices = [vecSanmodelToBlender(i) for i in indices]

        mesh.from_pydata(vertices,[],indices)
        
        mesh.update(calc_edges=True)
        # create new obj with the mesh
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = context.scene.cursor.location
        context.scene.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        return obj
 
class OT_ImportFilebrowser(Operator, ImportHelper):
    bl_idname = "import.open_filebrowser"
    bl_label = "Open"
    filename_ext = ".sanmodel"
    filter_glob: StringProperty( default='*.sanmodel', options={'HIDDEN'} )
    
    def execute(self, context):
        """Do something with the selected file(s)."""
        settings = context.scene.san_settings
        settings.valid_file = False
        global smd
        global smd_old
        smd_old = smd
        smd = SanmodelData()

        if self.filepath == "":
            console_notice(f"'{settings.path}' not found")
            self.report({'ERROR'}, f"Error with the specified file (see System Console for more detail)")
            return {"CANCELLED"}

        settings.path = self.filepath
        console_notice(f"opening '{settings.path}' ...")
        with open(settings.path, 'rb') as fs:#todo:check for error
            smd.content = (fs.read())
        
        settings.valid_file = smd.process_data(context)
        if not settings.valid_file:
            self.report({'ERROR'}, f"Error with the specified file (see System Console for more detail)")
            return {"CANCELLED"}
        
        settings.model_name = smd.name #export name
        settings.name = smd.name
        settings.vertices = str(len(smd.segments[SAN_VERTICES]))
        settings.normals = str(len(smd.segments[SAN_NORMALS]))
        settings.tangents = str(len(smd.segments[SAN_TANGENTS]))
        settings.uv = str(len(smd.segments[SAN_UV1]))
        settings.uv2 = str(len(smd.segments[SAN_UV2]))
        settings.uv3 = str(len(smd.segments[SAN_UV3]))
        settings.colors = str(len(smd.segments[SAN_COLORS]))
        settings.triangles = str(len(smd.segments[SAN_INDICES]))
        settings.bindposes = str(len(smd.segments[SAN_BINDPOSES]))
        settings.boneweights = str(len(smd.segments[SAN_UV2]))
        context.area.tag_redraw()
        console_notice("import done, you can create a blender object with the button 'Create new object'")
        return {"FINISHED"}

class OT_ExportFilebrowser(Operator, ExportHelper):
    bl_idname = "export.open_filebrowser"
    bl_label = "Save"
    filename_ext = ".sanmodel"
    filter_glob: StringProperty( default="*.sanmodel", options={"HIDDEN"} )

    some_boolean: BoolProperty(
            name="This has no effect",
            description="It's only here for dev reason.",
            default=True,
            )

    @classmethod
    def poll(cls, context):
        return (len(context.selected_objects) > 0)

    def execute(self, context):
        """Choose a name for the file to be saved"""
        bpy.ops.mesh.sanmodel_export(path=self.filepath)
        return {"FINISHED"}

blender_classes = [
    SanImportSettings,
    OT_ImportFilebrowser,
    OT_ExportFilebrowser,
]

def register():
    for bl_class in blender_classes:
        bpy.utils.register_class(bl_class)
    # bpy.types.TOPBAR_MT_file_import.append(import_menu_draw)
    # bpy.types.TOPBAR_MT_file_export.append(export_menu_draw)
    bpy.types.Scene.san_settings = PointerProperty(type=SanImportSettings)
    console_notice("sanmodel.py registered")

def unregister():
    for bl_class in blender_classes:
        bpy.utils.unregister_class(bl_class)
    # bpy.types.TOPBAR_MT_file_import.remove(import_menu_draw)
    # bpy.types.TOPBAR_MT_file_export.remove(export_menu_draw)
    del bpy.types.Scene.san_settings
    console_notice("sanmodel.py unregistered")

if __name__ == "__main__":
    register()
