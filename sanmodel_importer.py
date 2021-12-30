# addon progress:
    # import:
    # [x] name
    # [x] vertices
    # [x] normals
    # [ ] tangents
    # [ ] uv
    # [ ] uv2
    # [ ] uv3
    # [x] colors
    #       imported in a "Vertex Color" node linked to a "Principled BSDF" node
    # [x] triangles
    # [ ] boneWeights
    # [ ] bindposes
    #
    # export:
    # [x] name
    # [x] vertices
    # [ ] normals
    # [ ] tangents
    # [ ] uv
    # [ ] uv2
    # [ ] uv3
    # [x] colors
    #       when "Use Nodes" is enabled: the shader node should be "Principled BSDF": the "Base Color" and "Alpha" field are used, a "Vertex Color" node can be linked as inputs
    #       when "Use Nodes" is disabled: default diffuse color of the material
    #       note: rendered color from the default diffuse color seam brighter than with the "Vertex Color" node, even if RGBA values are equal
    # [x] triangles
    # [ ] boneWeights
    # [ ] bindposes

# File structure of a .sanmodel (4bytes numbers, except for the name 1byte per character):
    # |-----------------------------------------------------------------------------------------
    # |        DATA            |      SIZE in bytes
    # |-----------------------------------------------------------------------------------------
    # | model name             |  1 per character (the name is null terminated)
    # | vertices amount        |  4
    # | vertices array         |  4 * vertices amount * 3
    # | normals amount         |  4
    # | normals array          |  4 * normals amount * 3
    # | tangents amount        |  4
    # | tangents array         |  4 * tangents amount * 4
    # | uv amount              |  4
    # | uv array               |  4 * uv amount * 2
    # | uv2 amount             |  4
    # | uv2 array              |  4 * uv2 amount * 2
    # | uv3 amount             |  4
    # | uv3 array              |  4 * uv3 amount * 2
    # | colors amount          |  4
    # | colors array           |  4 * colors amount * 4
    # | triangles index amount |  4
    # | triangles index array  |  4 * triangle index amount
    # | boneWeights amount     |  4
    # | boneWeights array      |  4 * boneWeights amount
    # | bindposes amount       |  4
    # | bindposes array        |  4 * bindposes amount * 16
    # |-----------------------------------------------------------------------------------------
    #
    # [name\0]
    # [vertices_n][array of n*3]
    # [normals_n][array of n*3]
    # [tangents_n][array of n*4]
    # [uv_n][array of n*2]
    # [uv2_n][array of n*2]
    # [uv3_n][array of n*2]
    # [colors_n][array of n*4]
    # [triangles_n][array of n*1]
    # [boneWeights_n][array of n*1]
    # [bindposes_n][array of n*16]
    #
    # mesh segments and initial variable type from Unity C#
    # vertices      Vector3 float
    # normals       Vector3 float
    # tangents      Vector4 float
    # uv            Vector2 float
    # uv2           Vector2 float
    # uv3           Vector2 float
    # colors        rgba float
    # triangles     int
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

SAN_ENDIAN = "<"
SAN_VERTICES = 0
SAN_NORMALS = 1
SAN_TANGENTS = 2
SAN_UV = 3
SAN_UV1 = 4
SAN_UV2 = 5
SAN_COLORS = 6
SAN_TRIANGLES = 7
SAN_BONEWEIGHTS = 8
SAN_BINDPOSES = 9

# int.from_bytes(b'\x00\x00\x00\xff', byteorder='big') # 255
# int.from_bytes(b'\x00\x00\x00\xff', byteorder='little') # 4278190080
# https://docs.python.org/3/library/struct.html
def reinterpret_float_to_int(float_value):
    return struct.unpack(SAN_ENDIAN+"i", struct.pack(SAN_ENDIAN+"f", float_value))[0]

class SanImportSettings(PropertyGroup):
    invert_yz_axis : BoolProperty(
        name="Invert Y and Z axis",
        description="Invert y and z coordinates of vertices",
        default = False
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
    # my_int : IntProperty(
    #     name = "Triangles drawn",
    #     description="A integer property",
    #     default = 23,
    #     min = 10,
    #     max = 100
    #     )

class sanmodel_data():
    content: bytes
    name: StringIO
    segments: list
    
    def process_data(self, context):
        settings = context.scene.san_settings

        # read name
        self.name, self.content = self.content.split(b'\0', 1)
        self.name = self.name.decode()
        content_len = len(self.content)
        bsize = 4 # size for each value in bytes
        print("model name: %s\ncontent len: %d bytes, %d values" % (self.name, content_len, content_len/bsize))
        if (content_len % bsize) > 0:
            assert "File corrupted. Data length not a multiple of %d" % bsize # filelen - name_len - 1

        print("---------------- File content (without the name) -----------------")
        print(self.content)
        print("---------------- END ---------------------------------------------")
        # convert bytes to floats
        self.content = np.array(list(struct.iter_unpack(SAN_ENDIAN+"f", self.content[0:content_len])), dtype=float).flatten()
        
        # build segments arrays
        self.segments = []
        seg_vars = [3, 3, 4, 2, 2, 2, 4, 1, 1, 16] # cf file structure
        for vars in seg_vars:
            if not len(self.content):
                print(f"missing data to read, meaning the file is invalid")
                return False
            segment_len = reinterpret_float_to_int(self.content[0]) * vars
            print(f"segment_len : {segment_len}")
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
            assert "Slicing left some data, this shouldn't be the case."
        
        #reinterpret triangles and boneWeights data as int
        for i in range(7, 9):
            for j in range(len(self.segments[i])):
                self.segments[i][j] = reinterpret_float_to_int(self.segments[i][j]) # and automatically recasted as float because it's a float array
        
        # rebuild float arrays to tuple arrays
        # from : [0, 1, 2, 3, 4, 5, 6, 7, 8]
        # to : [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
        # tuple len is seg_vars[i]
        seg_vars[SAN_TRIANGLES] = 3 # group triangles as tuple(1,2,3)
        r = len(seg_vars) - 2 # for now, ignore the 2 last
        for i in range(r):
            tmp = []
            for j in range(len(self.segments[i])//seg_vars[i]):
                tmp.append(tuple(self.segments[i][j*seg_vars[i]:j*seg_vars[i]+seg_vars[i]]))
            self.segments[i] = tmp
        seg_vars[SAN_TRIANGLES] = 1

        #invert z and y axis to match unity
        if settings.invert_yz_axis:
            print("---------------invert y z")
            print(self.segments[SAN_VERTICES])
            for i, vertex in enumerate(self.segments[SAN_VERTICES]):
                self.segments[SAN_VERTICES][i] = tuple([vertex[0], vertex[2], vertex[1]])
            print(self.segments[SAN_VERTICES])
            print("---------------invert y z done")
        return True
    
    def create_obj(self, context, start, drawn):
        print("building mesh...")
        mesh = bpy.data.meshes.new(self.name + "Mesh")
        # inject data
        vert1 = start * 3
        vert2 = (start + drawn) * 3
        tri1 = start
        tri2 = (start + drawn)
        mesh.from_pydata(self.segments[SAN_VERTICES][vert1:vert2],[],self.segments[SAN_TRIANGLES][tri1:tri2])
        
        mesh.update(calc_edges=False)
        # create new obj with the mesh
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = context.scene.cursor.location
        context.scene.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        return obj


class MESH_OT_sanmodel_import(Operator):
    """import a sanmodel file"""
    bl_idname = "mesh.sanmodel_import"
    bl_label = "Import sanmodel file"
    
    path: bpy.props.StringProperty(
        description="Full path of the sanmodel file",
        default="",
        )
    
    @staticmethod
    def apply_normals(obj, normals):
        obj.data.use_auto_smooth = True # or it will not work
        # for i, n in enumerate(normals):
        #     normals[i] = Vector((1,1,1)).normalized()[:]
        #     print(f"{n} -> {normals[i]}")
        obj.data.normals_split_custom_set_from_vertices(normals)
        obj.data.calc_normals_split()
    
    @staticmethod
    def apply_tangents(obj, tangents):
        pass
    
    @staticmethod
    def apply_colors(context, obj, colors):
        settings = context.scene.san_settings

        if len(colors) == 0:
            return
        print("applying colors...")
        if False:# 1 color per face
            materials = colors
            for c in materials:
                mat = bpy.data.materials.new("san_mat") # set new material to variable
                mat.diffuse_color = c # change color
                print(f"created mat {mat.name}")
                obj.data.materials.append(mat) # add the material to the object
            for i, face in enumerate(obj.data.polygons):
                    # print('Material index of face ' + str(face.index) + ' : ' + str(face.material_index))
                    face.material_index = i
                    print(f"mat {obj.data.materials[i].name} applied to triangle {i}")
        else:# 1 color per vertex
            # https://blenderscripting.blogspot.com/2013/03/vertex-color-map.html
            # further https://blenderscripting.blogspot.com/2013/03/painting-vertex-color-map-using.html
            if not obj.data.vertex_colors:
                obj.data.vertex_colors.new()
            color_layer = obj.data.vertex_colors.active  

            i = 0
            for poly in obj.data.polygons:
                for idx in poly.vertices:
                    # print(f"applying color #{idx}")
                    color_layer.data[i].color = colors[idx]
                    i += 1
            print(f"colors applied: {i}")
            
            # create a mat from the vertex_color
            mat = bpy.data.materials.new('vertex_material')
            # todo: settings: [x] transparency
            obj.data.materials.append(mat)
            # https://blender.stackexchange.com/questions/160042/principled-bsdf-via-python-api
            mat.use_nodes = True
            node_tree = mat.node_tree
            bsdf = node_tree.nodes.get("Principled BSDF")
            assert(bsdf) # make sure it exists to continue
            vcol = node_tree.nodes.new(type="ShaderNodeVertexColor")
            vcol.layer_name = color_layer.name
            node_tree.links.new(vcol.outputs[0], bsdf.inputs[0]) # 0:0 = 'Base Color'
            if settings.use_alpha:
                mat.blend_method = "BLEND"
                node_tree.links.new(vcol.outputs[1], bsdf.inputs[19]) # 1:19 = 'Alpha'

    def execute(self, context):
        settings = context.scene.san_settings
        smd = sanmodel_data()

        if self.path == "":
            self.report(
                {'ERROR'},
                f"Error with the specified file")
            print(f"'{self.path}' not found")
            return {'CANCELLED'}

        print(f"opening '{self.path}' ...")
        with open(self.path, 'rb') as fs:#todo:check for error
            smd.content = (fs.read())
        
        if not smd.process_data(context):
            return {'CANCELLED'}
        for i in range(12, 13):
            obj = smd.create_obj(context, 0, i)
            self.apply_normals(obj, smd.segments[SAN_NORMALS])
            self.apply_tangents(obj, smd.segments[SAN_TANGENTS])
            if settings.use_vertex_colors:
                self.apply_colors(context, obj, smd.segments[SAN_COLORS])
            obj.location[0] += i*5
            obj.scale *= 250

        seg_names = ["vertices", "normals", "tangents", "uv", "uv2", "uv3", "colors", "triangles", "boneWeeights", "bindposes"]
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

        # [name\0]
        # [vertices_n][array of n*3]
        # [normals_n][array of n*3]
        # [tangents_n][array of n*4]
        # [uv_n][array of n*2]
        # [uv2_n][array of n*2]
        # [uv3_n][array of n*2]
        # [colors_n][array of n*4]
        # [triangles_n][array of n*1]
        # [boneWeights_n][array of n*1]
        # [bindposes_n][array of n*16]

    @staticmethod
    def prepare_mesh(context, obj):
        # https://blender.stackexchange.com/questions/57327/get-hard-shading-normals-in-bpy
        # https://docs.blender.org/api/current/bpy.types.Depsgraph.html?highlight=depsgraph
        
        # mesh = obj.to_mesh(preserve_all_data_layers=False)
        
        # This applies all the modifiers (without altering the scene)
        depsgraph = context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh = object_eval.to_mesh()

        # Triangulate for web export
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

        return mesh

    @staticmethod
    def extract_vertices(mesh):
        return np.array([[v.co.x, v.co.y, v.co.z] for v in mesh.vertices], dtype=SAN_ENDIAN+"f").flatten()
    @staticmethod
    def extract_normals(mesh, amount):
        # within a face with multiple triangles, if a shared vertex has different normals in the loops, the last one will override others
        normals = np.empty(amount*3, dtype=SAN_ENDIAN+"f")
        for loop in mesh.loops:
            idx = loop.vertex_index
            normals[idx*3:idx*3+3] = loop.normal[:]
            # print(f"extracting normal #{idx}")
            # print(normals[idx*4:idx*4+4])
        return normals
    @staticmethod
    def extract_tangents(mesh):
        return []
    @staticmethod
    def extract_uv1(mesh):
        return []
    @staticmethod
    def extract_uv2(mesh):
        return []
    @staticmethod
    def extract_uv3(mesh):
        return []
    @staticmethod
    def extract_colors(obj, amount):
        # there should only be 1 mat per mesh
        #https://blender.stackexchange.com/questions/122251/how-to-get-diffuse-color-of-a-material-via-python
        if not len(obj.material_slots):
            print(f"no material found, ignoring colors")
            return []
        colors = np.empty(amount*4, dtype=SAN_ENDIAN+"f")
        #if there is a linked vertex color array, read that insteed
        if False:# 1 color per face
            for face in obj.data.polygons: 
                print('Material index of face ' + str(face.index) + ' : ' + str(face.material_index))
                mat = obj.material_slots[face.material_index]
                if mat.material.use_nodes:
                    nodes = mat.material.node_tree.nodes
                    name = nodes.active.name #this is wrong, should use nodes.get("BSDF_PRINCIPLED")
                    print(f"node: {name}")
                    if nodes.active.type != "BSDF_PRINCIPLED":
                        print(f"BSDF_PRINCIPLED is not used for the colors, ignoring colors")
                        return []
                    node = nodes[name]
                    print(f"The color of it's {node.type} is {str(node.inputs[0].default_value[0:4])}")
                    # this is the default value,
                    # need to check if there is a vertex color linked and grab the values
                    colors = np.append(colors, np.array(node.inputs[0].default_value[0:4], dtype=SAN_ENDIAN+"f")) # 0 = 'Base Color' # RGBA
                else:
                    #todo: get base color, it is 1 color for the entire model
                    print(f"BSDF_PRINCIPLED is not used for the colors, ignoring colors")
                    return []
        else:# 1 color per vertex, or 1 color for all vertex
            mat = obj.active_material
            if mat.use_nodes:
                print(f"BSDF_PRINCIPLED is not used for the colors, getting 1 color for all vertices")
                return np.array([mat.diffuse_color for i in range(0, amount)], dtype=SAN_ENDIAN+"f").flatten()
            bsdf = mat.node_tree.nodes.get("Principled BSDF") # "Principled BSDF" is the name, "BSDF_PRINCIPLED" is the type
            if not bsdf:
                print(f"BSDF_PRINCIPLED is not used for the colors, ignoring colors")
                return []
            if not obj.data.vertex_colors:
                print(f"vertex color is not used for the colors, getting 1 color from BSDF_PRINCIPLED for all vertices")
                return np.array([bsdf.inputs.get("Base Color").default_value[0:4] for i in range(0, amount)], dtype=SAN_ENDIAN+"f").flatten()
            color_layer = obj.data.vertex_colors.active
            
            # within a face with multiple triangles, if a shared vertex has different colors in the polygons, the last one will override others
            i = 0
            for poly in obj.data.polygons:
                for idx in poly.vertices:
                    colors[idx*4:idx*4+4] = color_layer.data[i].color
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
    def extract_triangles(mesh):
        return np.array([[t.vertices[0], t.vertices[1], t.vertices[2]] for t in mesh.loop_triangles], dtype=SAN_ENDIAN+"i").flatten()
    @staticmethod
    def extract_boneWeights(mesh):
        return []
    @staticmethod
    def extract_bindposes(mesh):
        return []

    def execute(self, context):
        export_path = pathlib.Path(self.path)
        print("export as " + export_path.name)
        
        # [name\0]
        name = export_path.stem + "\0"
        data = bytearray(name, "utf-8")
        # print(data)

        # bl_mesh = self.prepare_mesh(context, bpy.data.objects['Cube'])
        if not (context.selected_objects):
            print("no object selected")
            return {'CANCELLED'}
        bl_mesh = self.prepare_mesh(context, context.selected_objects[0])
        
        seg_vars = [3, 3, 4, 2, 2, 2, 4, 1, 1, 16] # cf file structure
        len_vertices = len(bl_mesh.vertices)
        segments = [
            self.extract_vertices(bl_mesh),
            self.extract_normals(bl_mesh, len_vertices),
            self.extract_tangents(bl_mesh),
            self.extract_uv1(bl_mesh),
            self.extract_uv2(bl_mesh),
            self.extract_uv3(bl_mesh),
            self.extract_colors(context.selected_objects[0], len_vertices),
            self.extract_triangles(bl_mesh),
            self.extract_boneWeights(bl_mesh),
            self.extract_bindposes(bl_mesh),
        ]
        # self.content = np.array(list(struct.iter_unpack(SANMODEL_ENDIAN+"f", self.content[0:content_len])), dtype=float).flatten()
        for i, s in enumerate(segments):
            array_size = len(s)
            export_size = array_size // seg_vars[i]
            if (array_size != export_size * seg_vars[i]):
                print(f"Error: array size is not a multiple of {seg_vars[i]}")
                return {'CANCELLED'}
            barray = bytearray(s)#todo: force endian
            data[len(data):] = struct.pack(SAN_ENDIAN+"i", export_size) #bytearray([export_size])
            data[len(data):] = barray
            print(f"segment #{i} : {array_size}")
            print(barray)
        print("\nexport full data:")
        print(data)
        f = open(self.path, 'wb')
        f.write(data)
        f.close()
        return {'FINISHED'}
        
        # https://blender.stackexchange.com/questions/57327/get-hard-shading-normals-in-bpy
        # UV Textures by name
        texture_uvs = bl_mesh.tessface_uv_textures.get('UVMap')
        faces = bl_mesh.polygons

        _vertices = []
        _normals = []
        _uvs = []
        _uvs2 = []

        # Used for split normals export
        face_index_pairs = [(face, index) for index, face in enumerate(faces)]

        # Calculate the split normals from the shading
        bl_mesh.calc_normals_split()
        loops = bl_mesh.loops

        for face, face_index in face_index_pairs:
            # gather the face vertices
            face_vertices = [bl_mesh.vertices[v] for v in face.vertices]
            face_vertices_length = len(face_vertices)

            vertices = [(v.co.x, v.co.y, v.co.z) for v in face_vertices] # len devrait etre 9 pour un triangle

            # This is where you extract the split normals from the mesh
            normals = [(loops[l_idx].normal.x, loops[l_idx].normal.y, loops[l_idx].normal.z) for l_idx in face.loop_indices]

            uvs = [None] * face_vertices_length

            if texture_uvs:
                uv_layer = texture_uvs.data[face.index].uv
                uvs = [(uv[0], uv[1]) for uv in uv_layer]

            _vertices += vertices
            _normals += normals
            _uvs += uvs
            # _uvs2 += uvs2
        

        return {'FINISHED'}
    
class OT_TestOpenFilebrowser(Operator, ImportHelper):#todo: filter .sanmodel
    bl_idname = "test.open_filebrowser"
    bl_label = "Open"
    
    def execute(self, context):
        """Do something with the selected file(s)."""
        bpy.ops.mesh.sanmodel_import(path=self.filepath)
        return {'FINISHED'}

class OT_TestExportFilebrowser(Operator, ExportHelper):#todo: filter .sanmodel
    bl_idname = "test.export_filebrowser"
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

    def execute(self, context):
        if not (context.selected_objects):
            print("no object selected")
            return {'CANCELLED'}
        obj = context.selected_objects[0]
        me = obj.data
        # uv_layer = me.uv_layers.active.data

        for poly in me.polygons:
            print("Polygon index: %d, length: %d" % (poly.index, poly.loop_total))

            # range is used here to show how the polygons reference loops,
            # for convenience 'poly.loop_indices' can be used instead.
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                print("    Vertex: %d" % me.loops[loop_index].vertex_index)
                # print("    UV: %r" % uv_layer[loop_index].uv)
        return {'FINISHED'}


#https://blender.stackexchange.com/questions/57306/how-to-create-a-custom-ui/57332#57332
#https://www.youtube.com/watch?v=opZy2OJp8co&list=PLa1F2ddGya_8acrgoQr1fTeIuQtkSd6BW
class VIEW_3D_PT_sanmodel_import_panel(Panel):
    bl_label = "Import"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_import_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'sanmodel'
    
    def draw(self, context):
        settings = context.scene.san_settings
        
        # only? way to access the custom properties fields/details
        # first property index is 2
        rna_invert_yz = settings.bl_rna.properties[2]
        rna_use_vertex_color = settings.bl_rna.properties[3]
        rna_use_alpha = settings.bl_rna.properties[4]
        self.layout.prop(settings, rna_invert_yz.identifier, text=rna_invert_yz.name)
        self.layout.prop(settings, rna_use_vertex_color.identifier, text=rna_use_vertex_color.name)
        if settings.use_vertex_colors:
            self.layout.prop(settings, rna_use_alpha.identifier, text=rna_use_alpha.name)

        col = self.layout.column(align=True)
        props = col.operator("test.open_filebrowser",
            text="import",
            icon="IMPORT")
        props = self.layout.operator("test.debug_sanmodel",
            text = "selected objects debug",
            icon = "INFO")
class VIEW_3D_PT_sanmodel_export_panel(Panel):
    bl_label = "Export"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'sanmodel'
    
    def draw(self, context):
        settings = context.scene.san_settings

        col = self.layout.column(align=True)
        props = col.operator("test.export_filebrowser",
            text="export",
            icon="EXPORT")
        props = self.layout.operator("test.debug_sanmodel",
            text = "selected objects debug",
            icon = "INFO")

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

def import_menu_draw(self, context):
    self.layout.operator("test.open_filebrowser",
            text="Sanctuary model (.sanmodel)",
            icon="EVENT_S")
def export_menu_draw(self, context):
    self.layout.operator("test.export_filebrowser",
            text="Sanctuary model (.sanmodel)",
            icon="EVENT_S")

blender_classes = [
    SanImportSettings,
    MESH_OT_sanmodel_import,
    MESH_OT_sanmodel_export,
    OT_TestOpenFilebrowser,
    OT_TestExportFilebrowser,
    VIEW_3D_PT_sanmodel_import_panel,
    VIEW_3D_PT_sanmodel_export_panel,
    OBJECT_OT_object_to_mesh,
    MESH_OT_debug_sanmodel
]

def register():
    print("sanmodel_import.py registered")
    for bl_class in blender_classes:
        bpy.utils.register_class(bl_class)
    bpy.types.TOPBAR_MT_file_import.append(import_menu_draw)
    bpy.types.TOPBAR_MT_file_export.append(export_menu_draw)
    bpy.types.Scene.san_settings = PointerProperty(type=SanImportSettings)

def unregister():
    print("sanmodel_import.py unregistered")
    for bl_class in blender_classes:
        bpy.utils.unregister_class(bl_class)
    bpy.types.TOPBAR_MT_file_import.remove(import_menu_draw)
    bpy.types.TOPBAR_MT_file_export.remove(export_menu_draw)
    del bpy.types.Scene.san_settings

# needed if editing from the blender editor
# if __name__ == "__main__":
#     register()
