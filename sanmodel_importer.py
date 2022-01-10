# addon progress:
    # IMPORT:
    # [✅] name
    # [✅] vertices
    # [✅] normals
    # [❌] tangents: what is the 4th value? check with unity
    # [✅] uv0
    #       todo: create the shading nodes, set the transparency "clip", change base color input as texture data, link everything (cf shader-nodes-2.png)
    # [✅] uv1
    # [✅] uv2
    # [✅] colors
    #       imported in a vertex_colors array
    #       if "Generate shading nodes" is toggled: create a "Vertex Color" node linked to a "Principled BSDF" node
    # [✅] indices
    # [❌] boneWeights
    # [❌] bindposes
    #
    # EXPORT:
    # [✅] name
    #       set a custom name with a field in the UI?
    # [✅] vertices
    # [✅] normals
    # [❌] tangents
    #       check if everything is alright when import part will be done
    # [✅] uv0: export the uv_layer named "UV0Map"
    # [✅] uv1: export the uv_layer named "UV1Map"
    # [✅] uv2: export the uv_layer named "UV2Map"
    # note: uv_layers are linked to their object, they are not global. Every object can have its own uv_layer named "UV0Map" for example
    # 
    # [✅] colors
    #       ✅ when no material is found: ignore colors, even if it has a vertex_colors array
    #       ✅ when Blender's "Use Nodes" is enabled: the shader node should be "Principled BSDF":
    #              - the "Base Color" field is used
    #              - or a "Vertex Color" node can be linked as inputs, the active vertex_color array is used
    #       ✅ when Blender's "Use Nodes" is disabled: default diffuse color of the material
    #       note: rendered colors from the default diffuse color seam brighter than with the "Vertex Color" node, even if RGBA values are equal
    # [✅] indices
    # [❌] boneWeights
    # [❌] bindposes
    #
    # [❌] Quads to triangles: UV are fucked up, check colors too
    #
    # Blender <-> sanmodel(Unity) coordinates system with test_model sanmodel/fbx
    # [❔] Colors of the TestQube are still wrong? color of each vertex is OK, the faces triangles are different from the screenshot
    #         checked the indices manually, everything seams OK. 
    # [❌] export a fbx based model, reimport the new sanmodel (fbx -> blender -> sanmodel -> blender) (rotations are not ok with the fbx importer, not our business)
    #          the triangled mesh is ok, UV are fucked up becquse of quad faces not handled
    # [✅] export a sanmodel based model, reimport the new sanmodel (sanmodel -> blender -> sanmodel -> blender)
    #


# File structure of a .sanmodel (4bytes numbers, except for the name 1byte per character):
    # |-----------------------------------------------------------------------------------------
    # |        DATA               |      SIZE in bytes
    # |-----------------------------------------------------------------------------------------
    # | model name                |  1 per character (the name is null terminated)
    # | vertices amount           |  4
    # | vertices array            |  4 * vertices amount * 3
    # | normals amount            |  4
    # | normals array             |  4 * normals amount * 3
    # | tangents amount           |  4
    # | tangents array            |  4 * tangents amount * 4
    # | uv0 amount                |  4
    # | uv0 array                 |  4 * uv0 amount * 2
    # | uv1 amount                |  4
    # | uv1 array                 |  4 * uv1 amount * 2
    # | uv2 amount                |  4
    # | uv2 array                 |  4 * uv2 amount * 2
    # | colors amount             |  4
    # | colors array              |  4 * colors amount * 4
    # | triangles indices amount  |  4
    # | triangles indices array   |  4 * triangles indices amount
    # | boneWeights amount        |  4
    # | boneWeights array         |  4 * boneWeights amount
    # | bindposes amount          |  4
    # | bindposes array           |  4 * bindposes amount * 16
    # |-----------------------------------------------------------------------------------------
    #
    # [name\0]
    # [vertices n][array of n*3]
    # [normals n][array of n*3]
    # [tangents n][array of n*4]
    # [uv0 n][array of n*2]
    # [uv1 n][array of n*2]
    # [uv2 n][array of n*2]
    # [colors n][array of n*4]
    # [indices n][array of n*1]
    # [boneWeights n][array of n*1]
    # [bindposes n][array of n*16]
    #
    # mesh segments and initial variable type from Unity C#
    # vertices      Vector3 float
    # normals       Vector3 float
    # tangents      Vector4 float
    # uv0           Vector2 float
    # uv1           Vector2 float
    # uv2           Vector2 float
    # colors        rgba float
    # indices       int
    # boneWeights   int
    # bindposes     matrix4x4 = 4xVector4 float

bl_info = {
    "name": "Sanctuary model importer/exporter",
    "category": "Import-Export",
    "description": "Import or export a .sanmodel file, which is a model for the RTS game Sanctuary.",
    "version": (0, 1),
    "blender": (2, 93, 6),
    "warning": "Work in progress",
    "support": "COMMUNITY",
    "author": "Ater Omen <Dicord: Ater Omen#0791>",
    "location": "Operator Search",
    # "doc_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/My_Script",
    # "tracker_url": "https://developer.blender.org",
}

import numpy as np
from io import StringIO
import struct
import random
import os
import bpy
import pathlib
import bmesh
from array import array
from mathutils import (
    Vector,
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
from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       PointerProperty,
                       )

def vecSanmodelToBlender(vec):
    return (vec[0], vec[2], vec[1])
def vecBlenderToSanmodel(vec):
    return (vec[0], vec[2], vec[1])

seg_names = ["vertices", "normals", "tangents", "uv0", "uv1", "uv2", "colors", "indices", "boneweights", "bindposes"]
seg_vars = [3, 3, 4, 2, 2, 2, 4, 1, 1, 16] # cf file structure
smd = None
SAN_ENDIAN = "<"
SAN_VERTICES = 0
SAN_NORMALS = 1
SAN_TANGENTS = 2
SAN_UV0 = 3
SAN_UV1 = 4
SAN_UV2 = 5
SAN_COLORS = 6
SAN_INDICES = 7
SAN_BONEWEIGHTS = 8
SAN_BINDPOSES = 9

# int.from_bytes(b'\x00\x00\x00\xff', byteorder='big') # 255
# int.from_bytes(b'\x00\x00\x00\xff', byteorder='little') # 4278190080
# https://docs.python.org/3/library/struct.html
def reinterpret_float_to_int(float_value):
    return struct.unpack(SAN_ENDIAN+"i", struct.pack(SAN_ENDIAN+"f", float_value))[0]

class SanImportSettings(PropertyGroup):
    # internal properties
    path : StringProperty(
        name="sanmodel path",
        description="the path of the sanmodel",
        default = "..."
        )
    name : StringProperty(name="name", default = "...")
    vertices : StringProperty(name="vertices", default = "0")
    normals : StringProperty(name="normals", default = "0")
    tangents : StringProperty(name="tangents", default = "0")
    uv : StringProperty(name="uv", default = "0")
    uv1 : StringProperty(name="uv1", default = "0")
    uv2 : StringProperty(name="uv2", default = "0")
    colors : StringProperty(name="colors", default = "0")
    triangles : StringProperty(name="triangles", default = "0")
    #todo?:bindposes
    #todo?:boneweights       
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
        default = True
        )
    use_alpha : BoolProperty(
        name="Use Alpha channel (transparency)",
        description="Enable or disable the use of Alpha channel of vertex colors for triangles shading",
        default = True
        )
    shading_nodes : BoolProperty(
        name="Generate shading nodes",
        description="Generate shading nodes depending on previous settings (vertex_color, uv)",
        default = False
        )
    # my_int : IntProperty(
    #     name = "Triangles drawn",
    #     description="A integer property",
    #     default = 23,
    #     min = 10,
    #     max = 100
    #     )

class SanmodelData():
    content: bytes
    name: StringIO
    segments: list
    
    def process_data(self, context):
        settings = context.scene.san_settings

        # read name
        try:
            self.name, self.content = self.content.split(b'\0', 1)
        except ValueError:
            print("Error with the specified file, invalid data")
            return False
        self.name = self.name.decode()
        content_len = len(self.content)
        bsize = 4 # size for each value in bytes
        print("model name: %s\ncontent len: %d bytes, %d values" % (self.name, content_len, content_len/bsize))
        if (content_len % bsize) > 0:
            print("Error with the specified file, invalid data: should be only 4 bytes number after the null terminated name")
            return False

        print("---------------- File content (without the name) -----------------")
        print(self.content)
        print("---------------- END ---------------------------------------------")
        # convert bytes to floats
        self.content = np.array(list(struct.iter_unpack(SAN_ENDIAN+"f", self.content[0:content_len])), dtype=float).flatten()
        
        # build segments arrays
        self.segments = []
        global seg_names
        global seg_vars
        for i, vars in enumerate(seg_vars):
            if not len(self.content):
                print("Error with the specified file, invalid data: missing data")
                return False
            segment_len = reinterpret_float_to_int(self.content[0]) * vars
            print(f"{seg_names[i]} segment_len : {segment_len}")
            if (segment_len):
                print("slicing data:")
                data = self.content[1:1+segment_len]
                print(data)
                self.segments.append(data) # will rebuild this as tuples later, could be done here
                self.content = self.content[1+segment_len:]
            else:
                print("slicing nothing")
                self.content = self.content[1:]
                self.segments.append([])
        print("data left: ", self.content)
        if len(self.content):
            print("Error with the specified file, invalid data: slicing left some data, this shouldn't be the case.")
            return False
        
        #reinterpret indices and boneWeights data as int
        for i in range(7, 9):
            for j in range(len(self.segments[i])):
                self.segments[i][j] = reinterpret_float_to_int(self.segments[i][j]) # and automatically recasted as float because it's a float array
        
        # rebuild float arrays to tuple arrays
        # from : [0, 1, 2, 3, 4, 5, 6, 7, 8]
        # to : [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
        # tuple len is seg_vars[i]
        seg_vars[SAN_INDICES] = 3 # group indices as tuple(1,2,3) for 1 triangle/face
        r = len(seg_vars) - 2 # for now, ignore the 2 last
        for i in range(r):
            tmp = []
            for j in range(len(self.segments[i])//seg_vars[i]):
                tmp.append(tuple(self.segments[i][j*seg_vars[i]:j*seg_vars[i]+seg_vars[i]]))
            self.segments[i] = tmp
        seg_vars[SAN_INDICES] = 1
        return True
    
    def create_obj(self, context, start, drawn):
        settings = context.scene.san_settings
        print("building mesh...")
        mesh = bpy.data.meshes.new(self.name + "Mesh")

        #swap z and y axis to match unity
        vertices = self.segments[SAN_VERTICES][:]
        indices = self.segments[SAN_INDICES][:]
        if settings.swap_yz_axis:
            vertices = [vecSanmodelToBlender(v) for v in vertices]
            indices = [vecSanmodelToBlender(i) for i in indices]

        # inject data
        vert1 = start * 3
        vert2 = (start + drawn) * 3
        tri1 = start
        tri2 = (start + drawn)
        # mesh.from_pydata(vertices[vert1:vert2],[],self.segments[SAN_INDICES][tri1:tri2])
        mesh.from_pydata(vertices,[],indices)
        
        mesh.update(calc_edges=True)
        # create new obj with the mesh
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = context.scene.cursor.location
        context.scene.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        return obj

# https://b3d.interplanety.org/en/learning-loops/
class MESH_OT_sanmodel_import(Operator):
    """import a sanmodel file"""
    bl_idname = "mesh.sanmodel_import"
    bl_label = "Import sanmodel file"
    
    path: bpy.props.StringProperty(
        description="Full path of the sanmodel file",
        default="",
        )
    
    @staticmethod
    def apply_normals(obj, normals, swap_yz_axis):
        obj.data.use_auto_smooth = True # or it will not work
        # for i, n in enumerate(normals):
        #     normals[i] = Vector((1,1,1)).normalized()[:]
        #     print(f"{n} -> {normals[i]}")
        used = normals[:]
        if swap_yz_axis:
            used = [vecSanmodelToBlender(n) for n in normals]
        obj.data.normals_split_custom_set_from_vertices(used)
        obj.data.calc_normals_split()
    
    @staticmethod
    def apply_tangents(obj, tangents):
        pass
        # obj.data.use_auto_smooth = True # or it will not work
        # for i, n in enumerate(normals):
        #     normals[i] = Vector((1,1,1)).normalized()[:]
        #     print(f"{n} -> {normals[i]}")
        # obj.data.normals_split_custom_set_from_vertices(tangents)
        # obj.data.calc_normals_split()
    
    #https://b3d.interplanety.org/en/working-with-uv-maps-through-the-blender-api/
    @staticmethod
    def create_uv_layer(obj, uv_name, uv):
        #cube example : 6 quadfaces -> 12 triangles -> 36 vertices -> 36 uv
        obj.data.uv_layers.new(name=uv_name)
        i = 0
        for poly in obj.data.polygons:
            for idx in poly.vertices:
                # print(f"applying uv #{idx}")
                # obj.data.uv_layers.active.data[i].uv = uv[idx]
                obj.data.uv_layers[uv_name].data[i].uv = uv[idx]
                i += 1
        # print(f"uv applied: {i}")

    @staticmethod
    def apply_uv0(context, obj, uv):
        if not len(uv):
            return
        settings = context.scene.san_settings
        used = uv
        if settings.mirror_uv_vertically:
            used = [(e[0], 1-e[1]) for e in uv]
        MESH_OT_sanmodel_import.create_uv_layer(obj, "UV0Map", used)

        if settings.shading_nodes:#cf shader-nodes-2.png
            pass
    
    @staticmethod
    def apply_uv1(context, obj, uv):
        if not len(uv):
            return
        settings = context.scene.san_settings
        used = uv
        if settings.mirror_uv_vertically:
            used = [(e[0], 1-e[1]) for e in uv]
        MESH_OT_sanmodel_import.create_uv_layer(obj, "UV1Map", used)
    
    @staticmethod
    def apply_uv2(context, obj, uv):
        if not len(uv):
            return
        settings = context.scene.san_settings
        used = uv
        if settings.mirror_uv_vertically:
            used = [(e[0], 1-e[1]) for e in uv]
        MESH_OT_sanmodel_import.create_uv_layer(obj, "UV2Map", used)

    @staticmethod
    def apply_colors(context, obj, colors):
        settings = context.scene.san_settings

        if len(colors) == 0:
            return
        print("applying colors...")
        # https://blenderscripting.blogspot.com/2013/03/vertex-color-map.html
        # further https://blenderscripting.blogspot.com/2013/03/painting-vertex-color-map-using.html
        if not obj.data.vertex_colors:
            obj.data.vertex_colors.new(name=obj.name+"VertexColor")
        color_layer = obj.data.vertex_colors.active  

        i = 0
        for poly in obj.data.polygons:
            for idx in poly.vertices:
                # print(f"applying color #{idx}")
                color_layer.data[i].color = colors[idx]
                i += 1
        print(f"colors applied: {i}")
        
        if settings.shading_nodes:
            # create a mat from the vertex_color
            mat = bpy.data.materials.new(obj.name+"Mat")
            # todo: settings: [x] transparency
            obj.data.materials.append(mat)
            # https://blender.stackexchange.com/questions/160042/principled-bsdf-via-python-api
            mat.use_nodes = True
            node_tree = mat.node_tree
            bsdf = node_tree.nodes.get("Principled BSDF")
            assert(bsdf) # make sure it exists to continue
            vcolor = node_tree.nodes.new(type="ShaderNodeVertexColor")
            vcolor.layer_name = color_layer.name
            node_tree.links.new(vcolor.outputs["Color"], bsdf.inputs["Base Color"]) # 0:0 = 'Base Color'
            if settings.use_alpha:
                mat.blend_method = "BLEND"
                node_tree.links.new(vcolor.outputs['Alpha'], bsdf.inputs['Alpha']) # 1:19 = 'Alpha'

    def execute(self, context):
        settings = context.scene.san_settings
        global smd
        if not smd:
            print("Error: No data available to create the object")
            return {'CANCELLED'}
        for i in range(1, 2):
            obj = smd.create_obj(context, 0, i)
            self.apply_normals(obj, smd.segments[SAN_NORMALS], settings.swap_yz_axis)
            # self.apply_tangents(obj, smd.segments[SAN_TANGENTS])
            self.apply_uv0(context, obj, smd.segments[SAN_UV0])
            self.apply_uv1(context, obj, smd.segments[SAN_UV1])
            self.apply_uv2(context, obj, smd.segments[SAN_UV2])
            if settings.use_vertex_colors:
                self.apply_colors(context, obj, smd.segments[SAN_COLORS])

        global seg_names
        for i, seg in enumerate(smd.segments):
            print("")
            print(f"{seg_names[i]}:")
            print(seg)
        return {'FINISHED'}

class MESH_OT_sanmodel_export(Operator):
    """export a sanmodel file"""
    bl_idname = "mesh.sanmodel_export"
    bl_label = "Export sanmodel file"

    path: bpy.props.StringProperty(
        description="Full path of the sanmodel file",
        default="",
    )

    @staticmethod
    def prepare_mesh(context, obj):
        # https://blender.stackexchange.com/questions/57327/get-hard-shading-normals-in-bpy
        # https://docs.blender.org/api/current/bpy.types.Depsgraph.html?highlight=depsgraph
        
        # mesh = obj.to_mesh(preserve_all_data_layers=False)
        
        # This applies all the modifiers (without altering the scene)
        depsgraph = context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh = object_eval.to_mesh()

        # Triangulate
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        del bm

        mesh.calc_normals()
        mesh.calc_normals_split()
        # mesh.calc_tessface() # obsolete
        mesh.calc_loop_triangles()

        # https://blender.stackexchange.com/questions/31738/how-to-fix-outdated-internal-index-table-in-an-addon
        # if manipulating the bmesh directly:
        # if hasattr(mesh.verts, "ensure_lookup_table"): 
        #     bm.verts.ensure_lookup_table()
        #     # only if you need to:
        #     bm.edges.ensure_lookup_table()   
        #     bm.faces.ensure_lookup_table()

        return mesh
    @staticmethod
    def extract_vertices(mesh, swap_yz_axis):
        if swap_yz_axis:
            return np.array([vecBlenderToSanmodel(v.co) for v in mesh.vertices], dtype=SAN_ENDIAN+"f").flatten()
        else:
            return np.array([v.co[:] for v in mesh.vertices], dtype=SAN_ENDIAN+"f").flatten()
    @staticmethod
    def extract_normals(mesh, amount, swap_yz_axis):
        # within a face with multiple triangles, if a shared vertex has different normals in the loops, the last one will override others
        normals = np.empty(amount*3, dtype=SAN_ENDIAN+"f")
        for loop in mesh.loops:
            idx = loop.vertex_index
            if swap_yz_axis:
                normals[idx*3:idx*3+3] = vecBlenderToSanmodel(loop.normal)
            else:
                normals[idx*3:idx*3+3] = loop.normal[:]
            # print(f"extracting normal #{idx}")
            # print(normals[idx*4:idx*4+4])
        return normals
    @staticmethod
    def extract_tangents(mesh, amount):
        # within a face with multiple triangles, if a shared vertex has different tangents in the loops, the last one will override others
        tangents = np.empty(amount*4, dtype=SAN_ENDIAN+"f")
        for loop in mesh.loops:
            idx = loop.vertex_index
            # swap_yz_axis ?
            t = []
            t[0:] = loop.tangent[:]
            t[3:] = [-1.0] # tmp: ask team what is the 4th value
            tangents[idx*4:idx*4+4] = t 
            # print(f"extracting tangent #{idx}")
            # print(tangents[idx*4:idx*4+4])
        return tangents
        #https://blender.stackexchange.com/questions/26116/script-access-to-tangent-and-bitangent-per-face-how
        me = bpy.context.active_object.data
        # tangents have to be pre-calculated
        # this will also calculate loop normal
        me.calc_tangents()
        # loop faces
        for face in me.polygons:
            # loop over face loop
            for vert in [me.loops[i] for i in face.loop_indices]:
                tangent = vert.tangent
                normal = vert.normal
                bitangent = vert.bitangent_sign * normal.cross(tangent)
    @staticmethod
    def extract_uv(mesh, amount, name, mirror_vertically):
        uvmap = np.empty(amount*2, dtype=SAN_ENDIAN+"f")
        uv_layer = mesh.uv_layers.get(name)
        if not uv_layer:
            print(f"uv_layer '{name}' not found")
            return []#todo: report UV not found
        i = 0
        for poly in mesh.polygons:
            for idx in poly.vertices:
                uv = uv_layer.data[i].uv[:]
                if mirror_vertically:
                    uv = [uv[0], 1-uv[1]]
                uvmap[idx*2:idx*2+2] = uv
                # print(f"extracting uv #{idx}")
                # print(uv[idx*2:idx*2+2])
                i += 1
        # print(f"uv extracted: {i}")
        return uvmap
    @staticmethod
    def extract_colors(obj, amount):
        # there should only be 1 mat per mesh
        #https://blender.stackexchange.com/questions/122251/how-to-get-diffuse-color-of-a-material-via-python
        if not len(obj.material_slots):
            print(f"no material found, ignoring colors")
            return []
        colors = np.empty(amount*4, dtype=SAN_ENDIAN+"f")
     
        mat = obj.active_material
        if not mat.use_nodes:
            print(f"BSDF_PRINCIPLED is not used for the colors, getting 1 color for all vertices")
            return np.array([mat.diffuse_color for i in range(0, amount)], dtype=SAN_ENDIAN+"f").flatten()
        bsdf = mat.node_tree.nodes.get("Principled BSDF") # "Principled BSDF" is the name, "BSDF_PRINCIPLED" is the type
        if not bsdf:
            print(f"BSDF_PRINCIPLED is not used for the colors, ignoring colors")
            return []
        color_layer = obj.data.vertex_colors.active
        if not color_layer:
            print(f"vertex color is not used for the colors, getting 1 color from BSDF_PRINCIPLED for all vertices")
            colors = np.array([bsdf.inputs.get("Base Color").default_value[0:4] for i in range(0, amount)], dtype=SAN_ENDIAN+"f").flatten()
            # if settings.extract_with_global_alpha: # object alpha is different from vertices alpha
                # colors[3::4] = [bsdf.inputs.get("Alpha").default_value for i in range(0, amount)]
            # print(colors)
            return colors
        
        # within a face with multiple triangles, if a shared vertex has different colors in the polygons, the last one will override others
        i = 0
        for poly in obj.data.polygons:
            for idx in poly.vertices:
                colors[idx*4:idx*4+4] = color_layer.data[i].color[:]
                # print(f"extracting color #{idx}")
                # print(colors[idx*4:idx*4+4])
                i += 1
        print(f"colors extracted: {i}")

        colors = colors.flatten()
        print("*********************************\n")
        print(f"colors: {len(colors)}")
        print(colors)
        print("*********************************\n")
        return colors
    @staticmethod
    def extract_indices(mesh, swap_yz_axis):
        if swap_yz_axis:
            return np.array([vecBlenderToSanmodel(t.vertices) for t in mesh.loop_triangles], dtype=SAN_ENDIAN+"i").flatten()
        else:
            return np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=SAN_ENDIAN+"i").flatten()
    @staticmethod
    def extract_boneWeights(mesh):
        return []
    @staticmethod
    def extract_bindposes(mesh):
        return []

    # https://blender.stackexchange.com/questions/57327/get-hard-shading-normals-in-bpy
    def execute(self, context):
        settings = context.scene.san_settings
        export_path = pathlib.Path(self.path)
        print("export as " + export_path.name)
        
        # [name\0] it currently take the file name, make a field with custom name, or take object name
        name = export_path.stem + "\0"
        data = bytearray(name, "utf-8")
        # print(data)

        # bl_mesh = self.prepare_mesh(context, bpy.data.objects['Cube'])
        if not (context.selected_objects):
            print("no object selected")
            return {'CANCELLED'}
        bl_mesh = self.prepare_mesh(context, context.selected_objects[0])
        
        len_vertices = len(bl_mesh.vertices)
        segments = [
            self.extract_vertices(bl_mesh, settings.swap_yz_axis),
            self.extract_normals(bl_mesh, len_vertices, settings.swap_yz_axis),
            self.extract_tangents(bl_mesh, len_vertices),
            self.extract_uv(bl_mesh, len_vertices, "UV0Map", settings.mirror_uv_vertically),
            self.extract_uv(bl_mesh, len_vertices, "UV1Map", settings.mirror_uv_vertically),
            self.extract_uv(bl_mesh, len_vertices, "UV2Map", settings.mirror_uv_vertically),
            self.extract_colors(context.selected_objects[0], len_vertices),
            self.extract_indices(bl_mesh, settings.swap_yz_axis),
            self.extract_boneWeights(bl_mesh),
            self.extract_bindposes(bl_mesh),
        ]
        # self.content = np.array(list(struct.iter_unpack(SANMODEL_ENDIAN+"f", self.content[0:content_len])), dtype=float).flatten()
        
        global seg_vars
        global seg_names
        for i, s in enumerate(segments):
            array_size = len(s)
            export_n = array_size // seg_vars[i]
            if (array_size != export_n * seg_vars[i]):
                print(f"Error: array size is not a multiple of {seg_vars[i]}")
                return {'CANCELLED'}
            barray = bytearray(s)#todo: force endian
            bn = struct.pack(SAN_ENDIAN+"i", export_n) #bytearray([export_n])
            data[len(data):] = bn
            data[len(data):] = barray
            print(f"segment {seg_names[i]} : {export_n} elements for {array_size} numbers")
            print(bn)
            print(barray)
        print("\nexport full data:")
        print(data)
        f = open(self.path, 'wb')
        f.write(data)
        f.close()
        return {'FINISHED'}
    
class OT_ImportFilebrowser(Operator, ImportHelper):#todo: filter .sanmodel
    bl_idname = "import.open_filebrowser"
    bl_label = "Open"
    
    def execute(self, context):
        """Do something with the selected file(s)."""
        settings = context.scene.san_settings
        settings.valid_file = False
        global smd
        smd = SanmodelData()

        if self.filepath == "":
            print(f"'{settings.path}' not found")
            self.report({'ERROR'}, f"Error with the specified file (see System Console for more detail)")
            return {'CANCELLED'}

        settings.path = self.filepath
        print(f"opening '{settings.path}' ...")
        with open(settings.path, 'rb') as fs:#todo:check for error
            smd.content = (fs.read())
        
        settings.valid_file = smd.process_data(context)
        if not settings.valid_file:
            self.report({'ERROR'}, f"Error with the specified file (see System Console for more detail)")
            return {'CANCELLED'}
        
        settings.name = smd.name
        settings.vertices = str(len(smd.segments[SAN_VERTICES]))
        settings.normals = str(len(smd.segments[SAN_NORMALS]))
        settings.tangents = str(len(smd.segments[SAN_TANGENTS]))
        settings.uv = str(len(smd.segments[SAN_UV0]))
        settings.uv1 = str(len(smd.segments[SAN_UV1]))
        settings.uv2 = str(len(smd.segments[SAN_UV2]))
        settings.colors = str(len(smd.segments[SAN_COLORS]))
        settings.indices = str(len(smd.segments[SAN_INDICES]))
        # settings.boneweights = str(len(smd.segments[SAN_BONEWEIGHTS]))
        # settings.bindposes = str(len(smd.segments[SAN_BINDPOSES]))
        context.area.tag_redraw()
        return {'FINISHED'}

class OT_ExportFilebrowser(Operator, ExportHelper):#todo: filter .sanmodel
    bl_idname = "export.open_filebrowser"
    bl_label = "Open"

    filename_ext = ".sanmodel"
    def execute(self, context):
        """Choose a name for the file to be saved"""
        bpy.ops.mesh.sanmodel_export(path=self.filepath)
        return {'FINISHED'}

class MESH_OT_debug_sanmodel(Operator):
    """debug operator for currently selected object [0]"""
    bl_idname = "test.debug_sanmodel"
    bl_label = "debug sanmodel"

    @staticmethod
    def extract_colors(obj, mesh, amount):
        # there should only be 1 mat per mesh
        #https://blender.stackexchange.com/questions/122251/how-to-get-diffuse-color-of-a-material-via-python
        if not len(obj.material_slots):
            print(f"no material found, ignoring colors")
            return []
        colors = np.empty(amount*4, dtype=SAN_ENDIAN+"f")
     
        mat = obj.active_material
        if not mat.use_nodes:
            print(f"BSDF_PRINCIPLED is not used for the colors, getting 1 color for all vertices")
            return np.array([mat.diffuse_color for i in range(0, amount)], dtype=SAN_ENDIAN+"f").flatten()
        bsdf = mat.node_tree.nodes.get("Principled BSDF") # "Principled BSDF" is the name, "BSDF_PRINCIPLED" is the type
        if not bsdf:
            print(f"BSDF_PRINCIPLED is not used for the colors, ignoring colors")
            return []
        color_layer = mesh.vertex_colors.active
        if not color_layer:
            print(f"vertex color is not used for the colors, getting 1 color from BSDF_PRINCIPLED for all vertices")
            colors = np.array([bsdf.inputs.get("Base Color").default_value[0:4] for i in range(0, amount)], dtype=SAN_ENDIAN+"f").flatten()
            # if settings.extract_with_global_alpha: # object alpha is different from vertices alpha
                # colors[3::4] = [bsdf.inputs.get("Alpha").default_value for i in range(0, amount)]
            # print(colors)
            return colors
        
        # within a face with multiple triangles, if a shared vertex has different colors in the polygons, the last one will override others
        i = 0
        for poly in mesh.polygons:
            for idx in poly.vertices:
                colors[idx*4:idx*4+4] = color_layer.data[i].color[:]
                # print(f"extracting color #{idx}")
                # print(colors[idx*4:idx*4+4])
                i += 1
        print(f"colors extracted: {i}")

        colors = colors.flatten()
        print("*********************************\n")
        print(f"colors: {len(colors)}")
        print(colors)
        print("*********************************\n")
        return colors

    def execute(self, context):
        settings = context.scene.san_settings
        if not (context.selected_objects):
            print("no object selected")
            self.report({"INFO"}, "No object selected")
            return {'CANCELLED'}
        obj = context.selected_objects[0]
        me = obj.data
        # uv_layer = me.uv_layers.active.data

        # for poly in me.polygons:
        #     print("Polygon index: %d, length: %d" % (poly.index, poly.loop_total))

        #     # range is used here to show how the polygons reference loops,
        #     # for convenience 'poly.loop_indices' can be used instead.
        #     for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
        #         print("    Vertex: %d" % me.loops[loop_index].vertex_index)
        #         # print("    UV: %r" % uv_layer[loop_index].uv)


        #https://www.programcreek.com/python/?code=ndee85%2Fcoa_tools%2Fcoa_tools-master%2FBlender%2Fcoa_tools%2Ffunctions.py
        mesh = MESH_OT_sanmodel_export.prepare_mesh(context, obj)
        len_vertices = len(mesh.vertices)
        arr = MESH_OT_debug_sanmodel.extract_colors(obj, mesh, len_vertices)
        print (len(arr) / 4)
        print(arr)

        return {'FINISHED'}


#https://blender.stackexchange.com/questions/57306/how-to-create-a-custom-ui/57332#57332
#https://www.youtube.com/watch?v=opZy2OJp8co&list=PLa1F2ddGya_8acrgoQr1fTeIuQtkSd6BW
class sanmodel_panel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'sanmodel'
class VIEW_3D_PT_sanmodel_import_panel(sanmodel_panel, Panel):
    bl_label = "Import"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_import_panel"

    def draw(self, context):
        settings = context.scene.san_settings
        layout = self.layout

        # import button
        box = layout.box()
        props = box.operator("import.open_filebrowser",
            text=settings.path,
            icon="IMPORT")

        # details
        if settings.valid_file and smd:
            details = box.column(align=True)
            details.label(text="name: " + settings.name)
            details.label(text="vertices: " + settings.vertices)
            details.label(text="normals: " + settings.normals)
            details.label(text="tangents: " + settings.tangents)
            details.label(text="uv: " + settings.uv)
            details.label(text="uv1: " + settings.uv1)
            details.label(text="uv2: " + settings.uv2)
            details.label(text="colors: " + settings.colors)
            details.label(text="triangles: " + settings.triangles)
            # details.label(text="boneweights: " + settings.boneweights)
            # details.label(text="bindposes: " + settings.bindposes)

            # create model
            props = layout.operator("mesh.sanmodel_import",
                text="Create new object",
                icon="MESH_CUBE")
            # bpy.ops.mesh.sanmodel_import(path=self.filepath)

        props = layout.operator("test.debug_sanmodel",
            text = "selected objects debug",
            icon = "INFO")
class VIEW_3D_PT_sanmodel_export_panel(sanmodel_panel, Panel):
    bl_label = "Export"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_export_panel"
    
    def draw(self, context):
        settings = context.scene.san_settings

        col = self.layout.column(align=True)
        props = col.operator("export.open_filebrowser",
            text="export",
            icon="EXPORT")
class VIEW_3D_PT_sanmodel_settings_panel(sanmodel_panel, Panel):
    bl_label = "Settings"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_settings_panel"
    
    def draw(self, context):
        settings = context.scene.san_settings
        layout = self.layout
        rna_path = settings.bl_rna.properties["path"]
        rna_swap_yz = settings.bl_rna.properties["swap_yz_axis"]
        rna_mirror_uv_vertically = settings.bl_rna.properties["mirror_uv_vertically"]
        rna_use_vertex_color = settings.bl_rna.properties["use_vertex_colors"]
        rna_use_alpha = settings.bl_rna.properties["use_alpha"]
        rna_shading_nodes = settings.bl_rna.properties["shading_nodes"]
      # settings
        #layout.prop(settings, rna_path.identifier, text=rna_path.name)
        layout.prop(settings, rna_swap_yz.identifier, text=rna_swap_yz.name)
        layout.prop(settings, rna_mirror_uv_vertically.identifier, text=rna_mirror_uv_vertically.name)
        layout.prop(settings, rna_use_vertex_color.identifier, text=rna_use_vertex_color.name)
        if settings.use_vertex_colors:
            layout.prop(settings, rna_use_alpha.identifier, text=rna_use_alpha.name)
        layout.prop(settings, rna_shading_nodes.identifier, text=rna_shading_nodes.name)

class OBJECT_OT_object_to_mesh(bpy.types.Operator):
    # https://docs.blender.org/api/current/bpy.types.Depsgraph.html
    """Convert selected object to mesh and show number of vertices"""
    bl_label = "DEG Object to Mesh"
    bl_idname = "object.object_to_mesh"

    def execute(self, context):
        # Access input original object.
        obj = context.object
        if obj is None:
            self.report({'INFO'}, "No active mesh object to convert to mesh")
            return {'CANCELLED'}
        # Avoid annoying None checks later on.
        if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
            self.report({'INFO'}, "Object can not be converted to mesh")
            return {'CANCELLED'}
        depsgraph = context.evaluated_depsgraph_get()
        # Invoke to_mesh() for original object.
        mesh_from_orig = obj.to_mesh()
        self.report({'INFO'}, f"{len(mesh_from_orig.vertices)} in new mesh without modifiers.")
        # Remove temporary mesh.
        obj.to_mesh_clear()
        # Invoke to_mesh() for evaluated object.
        object_eval = obj.evaluated_get(depsgraph)
        mesh_from_eval = object_eval.to_mesh()
        self.report({'INFO'}, f"{len(mesh_from_eval.vertices)} in new mesh with modifiers.")
        # Remove temporary mesh.
        object_eval.to_mesh_clear()
        return {'FINISHED'}

# UI example
# def import_menu_draw(self, context):
#     self.layout.operator("test.open_filebrowser",
#             text="Sanctuary model (.sanmodel)",
#             icon="EVENT_S")
# def export_menu_draw(self, context):
#     self.layout.operator("export.export_filebrowser",
#             text="Sanctuary model (.sanmodel)",
#             icon="EVENT_S")

blender_classes = [
    SanImportSettings,
    MESH_OT_sanmodel_import,
    MESH_OT_sanmodel_export,
    OT_ImportFilebrowser,
    OT_ExportFilebrowser,
    VIEW_3D_PT_sanmodel_import_panel,
    VIEW_3D_PT_sanmodel_export_panel,
    VIEW_3D_PT_sanmodel_settings_panel,
    OBJECT_OT_object_to_mesh,
    MESH_OT_debug_sanmodel
]

def register():
    for bl_class in blender_classes:
        bpy.utils.register_class(bl_class)
    # bpy.types.TOPBAR_MT_file_import.append(import_menu_draw)
    # bpy.types.TOPBAR_MT_file_export.append(export_menu_draw)
    bpy.types.Scene.san_settings = PointerProperty(type=SanImportSettings)
    print("sanmodel_import.py registered")

def unregister():
    for bl_class in blender_classes:
        bpy.utils.unregister_class(bl_class)
    # bpy.types.TOPBAR_MT_file_import.remove(import_menu_draw)
    # bpy.types.TOPBAR_MT_file_export.remove(export_menu_draw)
    del bpy.types.Scene.san_settings
    print("sanmodel_import.py unregistered")

# needed if editing from the blender editor
# if __name__ == "__main__":
#     register()
