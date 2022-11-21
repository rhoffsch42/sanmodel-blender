bl_info = {
    "name": "Sanctuary model importer/exporter",
    "category": "Import-Export",
    "description": "Import or export a .sanmodel file, which is a model for the RTS game Sanctuary.",
    "version": (0, 3),
    "blender": (3, 2, 0),
    "warning": "Work in progress",
    "support": "COMMUNITY",
    "author": "Ater Omen <Dicord: Ater Omen#0791>, Slakxs <Discord: Slakxs#2649>",
    "location": "Operator Search",
    # "doc_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/My_Script",
    # "tracker_url": "https://developer.blender.org",
}

from . import (
    sanmodel,
    sanmodel_importer,
    sanmodel_exporter,
    panels,
    utils,
)
modules = [
    sanmodel,
    sanmodel_importer,
    sanmodel_exporter,
    panels,
]

# modulesNames = ["sanmodel","panels"]

def register():
    for m in modules:
        m.register()
    print(f"sanmodel v0.3 package registered")

def unregister():
    for m in modules:
        m.unregister()
    print(f"sanmodel v0.3 package unregistered")

if __name__ == "__main__":
    register()

# addon progress:
    # IMPORT:
    # [✅] name
    # [✅] vertices
    # [✅] normals
    # [✅] tangents: actually ignored, they are computed from the normals and uv1, it seams they can't be manually set
    #       4th value is the bitangent_sign: #https://answers.unity.com/questions/7789/calculating-tangents-vector4.html
    # [✅] uv1
    #       todo?: create the shading nodes, set the transparency "clip", change base color input as texture data, link everything (cf shader-nodes-2.png)
    # [✅] uv2
    #   Sanctuary team:
    #    "we removed BoneWeights array and instead bone weights (if exist) are stored in UV2.x where X is int of bone ID. There is limit to only 1 bone per vertex."
    #    "some things like props can have additional UV data used for shaders. Only skinned meshes use uv2.x as skinning data"
    # [✅] uv3
    # [✅] colors
    #       imported in a vertex_colors array
    #       if "Generate shading nodes" is toggled: create a "Vertex Color" node linked to a "Principled BSDF" node
    # [✅] indices
    # [❌] boneWeights
    #   Sanctuary team:
    #    "we removed BoneWeights array and instead bone weights (if exist) are stored in UV3.x where X is int of bone ID. There is limit to only 1 bone per vertex."
    # [❌] bindposes
    #
    # EXPORT:
    # [✅] name : can set a custom name in a editable field above the export button, it updates when importing model
    #       todo: updates when selecting object: need to store original model name and link it with the object
    # [✅] vertices
    # [✅] normals
    # [✅] tangents: swapping YZ axis or mirroring UV can invert bitangent_sign, this should be handled. cf MESH_OT_sanmodel_export.extract_tangents()
    # [✅] uv1: export the uv_layer named "UV1Map"
    # [✅] uv2: export the uv_layer named "UV2Map"
    # [✅] uv3: export the uv_layer named "UV3Map"
    # note: uv_layers are linked to their object, they are not global. Every object can have its own uv_layer named "UV1Map" for example
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
    # OTHER:
    # [✅] Spliting faces to avoid shared vertex with different normal or UV, and to avoid data loss
    # [✅] Quads to triangles: done
    # note: if a face is already triangularized before the export, it will split the triangles in different faces, resulting in unnecessary duplicate vertices.
    #
    # Blender <-> sanmodel(Unity) coordinates system with test_model sanmodel/fbx:
    # [❔] Colors of the TestQube are still wrong? color of each vertex is OK, the faces triangles are different from the screenshot
    #         checked the indices manually, everything seams OK. 
    # [✅] export a fbx based model, reimport the new sanmodel (fbx -> blender -> sanmodel -> blender) (rotations are not ok with the fbx importer, not our business)
    # [✅] export a sanmodel based model, reimport the new sanmodel (sanmodel -> blender -> sanmodel -> blender)
    #
    # [❌] Per object data on blender:
    #       - original import file path
    #       - original object name
    #       - original import settings (swapYZ and mirrorUV)
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
    # | uv1 amount                |  4
    # | uv1 array                 |  4 * uv1 amount * 2
    # | uv2 amount                |  4
    # | uv2 array                 |  4 * uv2 amount * 2
    # | uv3 amount                |  4
    # | uv3 array                 |  4 * uv3 amount * 2
    # | colors amount             |  4
    # | colors array              |  4 * colors amount * 4
    # | triangles indices amount  |  4
    # | triangles indices array   |  4 * triangles indices amount
    # | bindposes amount          |  4
    # | bindposes array           |  4 * bindposes amount * 16
    # |-----------------------------------------------------------------------------------------
    #
    # [name\0]
    # [vertices n][array of n*3]
    # [normals n][array of n*3]
    # [tangents n][array of n*4]
    # [uv1 n][array of n*2]
    # [uv2 n][array of n*2]
    # [uv3 n][array of n*2]
    # [colors n][array of n*4]
    # [indices n][array of n*1]
    # [bindposes n][array of n*16]
    #
    # mesh segments and initial variable type from Unity C#
    # vertices      Vector3 float
    # normals       Vector3 float
    # tangents      Vector4 float
    # uv1           Vector2 float
    # uv2           Vector2 float
    # uv3           Vector2 float
    # colors        rgba float
    # indices       int
    # bindposes     matrix4x4 = 4xVector4 float