import numpy as np
import bpy
from bpy.types import (
    Operator,
)
from mathutils import (
    Vector,
    Matrix
)
from .utils import (
    console_debug,
    console_debug_data,
    vecSanmodelToBlender,
    vecBlenderToSanmodel,
)
from . import sanmodel as S

def uv_to_boneweights(uv_array):
    # uv are tuples of 2 float values
    return [e[0] for e in uv_array]

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
        used = normals[:]
        if swap_yz_axis:
            used = [vecSanmodelToBlender(n) for n in normals]
        obj.data.normals_split_custom_set_from_vertices(used)
        obj.data.calc_normals_split()

    @staticmethod
    def apply_tangents(obj, tangents, uvname):
        if obj.data.uv_layers.get(S.UV1_NAME):
            obj.data.calc_tangents(uvmap=uvname)
        # they are computed from the normals and uv map, then stored in the loops
        # can't manually set tangents? maybe to avoid having an invalid tengant space

    @staticmethod
    def create_uv_layer(obj, uv_name, uv):
        #https://b3d.interplanety.org/en/working-with-uv-maps-through-the-blender-api/
        #cube example : 6 quadfaces -> 12 triangles -> 36 vertices -> 36 uv
        obj.data.uv_layers.new(name=uv_name)
        print(f"created uv_layer {uv_name}")
        i = 0
        for poly in obj.data.polygons:
            for idx in poly.vertices:
                obj.data.uv_layers[uv_name].data[i].uv = uv[idx]
                i += 1

    @staticmethod
    def apply_uv(context, obj, uv_array, uv_name):
        if not len(uv_array):
            return
        settings = context.scene.san_settings
        used = uv_array
        if settings.mirror_uv_vertically:
            used = [(e[0], 1-e[1]) for e in uv_array]
        MESH_OT_sanmodel_import.create_uv_layer(obj, uv_name, used)

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
                color_layer.data[i].color = colors[idx]
                i += 1
        
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
            node_tree.links.new(vcolor.outputs["Color"], bsdf.inputs["Base Color"])
            if settings.use_alpha:
                mat.blend_method = "CLIP"
                node_tree.links.new(vcolor.outputs["Alpha"], bsdf.inputs["Alpha"])

    @staticmethod
    def apply_bindposes(context, obj, data):
        if len(data) == 0 or len(data) % 16 > 0:
            return
        bone_count = len(data) // 16
        bone_matrix = [Matrix(np.array(data[x*16:(x+1)*16]).reshape(4,4).tolist()) for x in range(bone_count)]

        bpy.ops.object.armature_add(align='CURSOR')
        armature = context.active_object
        armature.name = S.smd.name + 'Rig'

        # because the armature is created at the cursor and is parent to the mesh object, the mesh object must be set to 0 location, 
        # otherwise the cursor transform will be applied twice
        obj.parent = armature
        obj.location = Vector((0.0, 0.0, 0.0))

        # https://devtalk.blender.org/t/add-new-bones-to-armature/15051/3
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        edit_bones = armature.data.edit_bones
        edit_bones.remove(edit_bones[0])
        for i in range(bone_count):
            bone = edit_bones.new("Bone_" + str(i))
            MESH_OT_sanmodel_import.extract_additional_bone_data(bone, bone_matrix[i])
            console_debug_data(bone_matrix[i])
            test = bone_matrix[i]
            # https://developer.blender.org/diffusion/BS/browse/master/source/blender/editors/armature/armature_utils.c
            bone.matrix = test
        bpy.ops.object.mode_set(mode='OBJECT')

    @staticmethod
    def extract_additional_bone_data(bone, matrix):
            bone.length = matrix[3][3]
            matrix[3][3] = 1.0

    @staticmethod
    def apply_boneweights(context, obj, data):
        if len(data) == 0:
            return
        # active_object is now Armature, because of creation operator in apply_bindposes
        armature = context.active_object

        console_debug_data("bone data")
        console_debug_data(data)
        bone_count = len(armature.data.bones)
        v_groups = [ [] for i in range(bone_count)]
        for i, val in enumerate(data):
            v_groups[int(val)].append(i)
        for i in range(bone_count):
            v_group = obj.vertex_groups.new(name='Bone_' + str(i))
            v_group.add(v_groups[i], 1.0, 'ADD')

        context.view_layer.objects.active = obj
        bpy.ops.object.modifier_add(type='ARMATURE')
        context.object.modifiers["Armature"].object = armature

    def execute(self, context):
        settings = context.scene.san_settings
        if not S.smd:
            print("Error: No data available to create the object")
            return {"CANCELLED"}

        for i, seg in enumerate(S.smd.segments):
            console_debug("")
            console_debug(f"{i}: {S.seg_names[i]}:")
            console_debug(f"seg len: {len(seg)}")
            # console_debug_data(seg)
        # return {"FINISHED"}

        obj = S.smd.create_obj(context)
        self.apply_normals(obj, S.smd.segments[S.SAN_NORMALS], settings.swap_yz_axis)
        self.apply_uv(context, obj, S.smd.segments[S.SAN_UV1], S.UV1_NAME)
        self.apply_tangents(obj, S.smd.segments[S.SAN_TANGENTS], S.UV1_NAME) # requires uv1
        # self.apply_uv(context, obj, S.smd.segments[S.SAN_UV2], S.UV2_NAME) # these are in fact boneweights
        self.apply_uv(context, obj, S.smd.segments[S.SAN_UV3], S.UV3_NAME)
        if settings.use_vertex_colors:
            self.apply_colors(context, obj, S.smd.segments[S.SAN_COLORS])
        self.apply_bindposes(context, obj, S.smd.segments[S.SAN_BINDPOSES])
        if (not len(S.smd.segments[S.SAN_BINDPOSES]) and len(S.smd.segments[S.SAN_UV2])):
            console_debug("Model has no bindposes. Ignoring segments SAN_UV2 (boneweights).")
        else:
            self.apply_boneweights(context, obj, uv_to_boneweights(S.smd.segments[S.SAN_UV2]))
        print("Object created")
        return {"FINISHED"}



blender_classes = [ 
    MESH_OT_sanmodel_import,
]

def register():
    for bl_class in blender_classes:
        bpy.utils.register_class(bl_class)
    print("sanmodel_importer.py registered")

def unregister():
    for bl_class in blender_classes:
        bpy.utils.unregister_class(bl_class)
    print("sanmodel_importer.py unregistered")

if __name__ == "__main__":
    register()