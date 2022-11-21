import numpy as np
import bmesh
import struct
import pathlib
import copy
import bpy
from bpy.types import (
    Operator,
)
from .utils import (
    console_notice,
    console_debug,
    console_debug_data,
    vecSanmodelToBlender,
    vecBlenderToSanmodel,
)
from . import sanmodel as S


def boneweights_to_uv(boneweights):
    return np.array([[e, 0.0] for e in boneweights], dtype=S.SAN_ENDIAN+"f").flatten()

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
        # https://docs.blender.org/api/current/bpy.types.Depsgraph.html
        
        # mesh = obj.to_mesh(preserve_all_data_layers=False)
        
        # This applies all the modifiers (without altering the scene)
        depsgraph = context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh = object_eval.to_mesh()

        # split and triangulate
        bm = bmesh.new()
        bm.from_mesh(mesh)
        # https://docs.blender.org/api/current/bmesh.ops.html
        # https://docs.blender.org/api/current/bmesh.types.html
        bmesh.ops.split_edges(bm, edges=bm.edges) # split the edges from other faces
        bmesh.ops.triangulate(bm, faces=bm.faces)
        # UI manual way:        
        # https://docs.blender.org/manual/en/latest/modeling/meshes/editing/mesh/split.html#bpy-ops-mesh-edge-split
        # apply an edge modifier?
        # https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/edge_split.html
        
        bm.to_mesh(mesh)
        bm.free()
        del bm

        mesh.calc_normals()
        mesh.calc_normals_split()
        if mesh.uv_layers.get(S.UV1_NAME):
            mesh.calc_tangents(uvmap=S.UV1_NAME)
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
            return np.array([vecBlenderToSanmodel(v.co) for v in mesh.vertices], dtype=S.SAN_ENDIAN+"f").flatten()
        else:
            return np.array([v.co[:] for v in mesh.vertices], dtype=S.SAN_ENDIAN+"f").flatten()

    @staticmethod
    def extract_normals(mesh, amount, swap_yz_axis):
        normals = np.empty(amount*3, dtype=S.SAN_ENDIAN+"f")
        for loop in mesh.loops:
            idx = loop.vertex_index
            if swap_yz_axis:
                normals[idx*3:idx*3+3] = vecBlenderToSanmodel(loop.normal)
            else:
                normals[idx*3:idx*3+3] = loop.normal[:]
        return normals

    @staticmethod
    def extract_tangents(mesh, amount, swap_yz_axis, mirror_uv_vertically):
        tangents = np.empty(amount*4, dtype=S.SAN_ENDIAN+"f")
        for loop in mesh.loops:
            i = loop.vertex_index
            tangents[i*4:i*4+3] = vecBlenderToSanmodel(loop.tangent) if swap_yz_axis else loop.tangent[:]
            tangents[i*4+3] = loop.bitangent_sign if (mirror_uv_vertically==swap_yz_axis) else -loop.bitangent_sign
        # blender's bitangent_sign with TestCube.sanmodel (file sign is -)
        # | swap yz | mirror uv | sign |
        # |   Y     |     Y     |   -  |
        # |   N     |     N     |   -  |
        # |   Y     |     N     |   +  |
        # |   N     |     Y     |   +  |
        # this may be caused by the use of cross() when blender is computing tangents
        return tangents

    @staticmethod
    def extract_uv(mesh, amount, name, mirror_uv_vertically):
        uv_layer = mesh.uv_layers.get(name)
        if not uv_layer:
            #console_notice(f"uv_layer '{name}' not found")
            return []
        uvmap = np.empty(amount*2, dtype=S.SAN_ENDIAN+"f")
        i = 0
        for poly in mesh.polygons:
            for idx in poly.vertices:
                uv = uv_layer.data[i].uv[:]
                if mirror_uv_vertically:
                    uv = [uv[0], 1-uv[1]]
                uvmap[idx*2:idx*2+2] = uv
                i += 1
        return uvmap

    @staticmethod
    def extract_colors(obj, bmesh, amount):
        # there should only be 1 mat per mesh
        # https://blender.stackexchange.com/questions/122251/how-to-get-diffuse-color-of-a-material-via-python
        
        # if not len(obj.material_slots):
        if not obj.active_material:
            console_notice(f"no material found, ignoring colors")
            return []
        
        colors = np.empty(amount*4, dtype=S.SAN_ENDIAN+"f")
        mat = obj.active_material
        if not mat.use_nodes:
            console_notice(f"BSDF_PRINCIPLED is not used for the colors, getting 1 color for all vertices")
            return np.array([mat.diffuse_color for i in range(0, amount)], dtype=S.SAN_ENDIAN+"f").flatten()
        bsdf = mat.node_tree.nodes.get("Principled BSDF") # "Principled BSDF" is the name, "BSDF_PRINCIPLED" is the type
        if not bsdf:
            console_notice(f"BSDF_PRINCIPLED is not used for the colors, ignoring colors")
            return []
        color_layer = bmesh.vertex_colors.active
        if not color_layer:
            console_notice(f"vertex color is not used for the colors, getting 1 color from BSDF_PRINCIPLED for all vertices")
            colors = np.array([bsdf.inputs.get("Base Color").default_value[0:4] for i in range(0, amount)], dtype=S.SAN_ENDIAN+"f").flatten()
            # if settings.extract_with_global_alpha: # object alpha is different from vertices alpha
                # colors[3::4] = [bsdf.inputs.get("Alpha").default_value for i in range(0, amount)]
            return colors
        
        i = 0
        for poly in bmesh.polygons:
            for idx in poly.vertices:
                colors[idx*4:idx*4+4] = color_layer.data[i].color[:]
                i += 1
        return colors.flatten()

    @staticmethod
    def extract_indices(mesh, swap_yz_axis):
        if swap_yz_axis:
            return np.array([vecBlenderToSanmodel(t.vertices) for t in mesh.loop_triangles], dtype=S.SAN_ENDIAN+"i").flatten()
        else:
            return np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=S.SAN_ENDIAN+"i").flatten()

    @staticmethod
    def extract_boneWeights(armature, obj):
        if not armature:
            return []
        boneweights = []
        for v in obj.data.vertices:
            group = sorted([(g.group, obj.vertex_groups[g.group].weight(v.index)) for g in v.groups], key=lambda tup: tup[1], reverse=True)[0]
            boneweights.append(group[0]) if len(boneweights) > 0 else boneweights.append(0)
        console_debug(f"boneweights : {len(boneweights)}")
        console_debug_data(boneweights)
        return np.array(boneweights, dtype=S.SAN_ENDIAN+"i").flatten()

    @staticmethod
    def extract_bindposes(armature):
        if not armature:
            console_debug("no armature found")
            return []
        result = np.array([MESH_OT_sanmodel_export.inject_additional_bone_data(b) for b in armature.data.bones], dtype=S.SAN_ENDIAN+"f").flatten()
        console_debug_data(np.array2string(result))
        return result

    @staticmethod
    def inject_additional_bone_data(bone):
        # bone.matrix_local is read only
        # https://stackoverflow.com/questions/2612802/list-changes-unexpectedly-after-assignment-why-is-this-and-how-can-i-prevent-it
        matrix = copy.deepcopy(bone.matrix_local)
        matrix[3][3] = bone.length
        return matrix

    # https://blender.stackexchange.com/questions/57327/get-hard-shading-normals-in-bpy
    def execute(self, context):
        if not (context.selected_objects):
            console_notice("No Object selected")
            return {"CANCELLED"}

        settings = context.scene.san_settings
        export_path = pathlib.Path(self.path)
        console_notice("export as " + export_path.name)

        # Note: this is not compatible with exporting multiple objects! when multi export comes around, it's best to discard any selected objects that are of type armature
        if context.selected_objects[0].type == 'ARMATURE':
            bl_armature = context.selected_objects[0]
            bl_obj = bl_armature.children[0]
        else:
            bl_obj = context.selected_objects[0]
            bl_armature = bl_obj.find_armature()
        
        data = bytearray(settings.model_name + "\0", "utf-8") # [name\0]
        bl_mesh = self.prepare_mesh(context, bl_obj)
        
        len_vertices = len(bl_mesh.vertices)
        console_debug(f"vertices: {len_vertices}")

        console_debug(f"# grabbing uv_layers names (same order as in the UI)")
        uv_names = ["0", "1"] # only 2 UV layers max, because one UV segment of sanmodel is reserved for boneweights 
        for i, l in enumerate(bl_mesh.uv_layers):
            uv_names[i] = l.name
            console_debug(f"found UV layer: {l.name}")

        segments = [
            self.extract_vertices(bl_mesh, settings.swap_yz_axis),
            self.extract_normals(bl_mesh, len_vertices, settings.swap_yz_axis),
            self.extract_tangents(bl_mesh, len_vertices, settings.swap_yz_axis, settings.mirror_uv_vertically),
            self.extract_uv(bl_mesh, len_vertices, uv_names[0], settings.mirror_uv_vertically),
            # There is still a bug with boneweights when importing-exporting-reimporting-reexporting a sanmodel 
            # (importing and reexporting blender generated sanmodels) 
            # boneweights_to_uv(self.extract_boneWeights(bl_armature, bl_obj)), # UV2 segment for boneweights
            [],
            self.extract_uv(bl_mesh, len_vertices, uv_names[1], settings.mirror_uv_vertically),
            self.extract_colors(bl_obj, bl_mesh, len_vertices),
            self.extract_indices(bl_mesh, settings.swap_yz_axis),
            self.extract_bindposes(bl_armature),
        ]
        console_debug(f"tmp: boneweights to uv len : {len(segments[S.SAN_UV2])}")
        # console_debug(segments[S.SAN_UV2])

        for i, s in enumerate(segments):
            array_size = len(s)
            export_n = array_size // S.seg_vars[i]

            console_debug(f"[Write Process] segment[{i}]: {S.seg_names[i]}: {export_n}, {array_size} values ({array_size*4} bytes)")
            if (array_size != export_n * S.seg_vars[i]):
                console_notice(f"Error: array size is not a multiple of {S.seg_vars[i]}")
                return {"CANCELLED"}

            b_n = struct.pack(S.SAN_ENDIAN+"i", export_n) #bytearray([export_n])
            b_array = bytearray(s)#todo: force endian
            
            b_array_len = len(b_array)
            if (b_array_len != array_size*4):
                console_notice(f"Error with the byte data: byte array size: {b_array_len}, ie {b_array_len/4} values")
                console_notice(f"[Write Process] segment[{i}]: {S.seg_names[i]}: {export_n}, {array_size} values ({array_size*4} bytes)")
                return {"CANCELLED"}
            
            data[len(data):] = b_n
            data[len(data):] = b_array
            console_debug(f"full data len: {len(data)}")
            console_debug(f"")
        
        console_debug("export full data:")
        console_debug_data(data)
        f = open(self.path, 'wb')
        f.write(data)
        f.close()
        console_notice("export done")
        return {"FINISHED"}
   



blender_classes = [ 
    MESH_OT_sanmodel_export,
]

def register():
    for bl_class in blender_classes:
        bpy.utils.register_class(bl_class)
    console_notice("sanmodel_importer.py registered")

def unregister():
    for bl_class in blender_classes:
        bpy.utils.unregister_class(bl_class)
    console_notice("sanmodel_importer.py unregistered")

if __name__ == "__main__":
    register()