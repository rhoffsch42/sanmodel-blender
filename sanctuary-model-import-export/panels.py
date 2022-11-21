import bpy
from bpy.types import (
    Operator,
    Panel,
)
from mathutils import (
    Vector,
)
from . import sanmodel as S

from .utils import (
    console_notice,
    console_debug,
    console_debug_data,
)

class MESH_OT_debug_diff_sanmodel(Operator):
    """debug operator: diff for the 2 last imported .sanmodel"""
    bl_idname = "test.debug_diff_sanmodel"
    bl_label = "debug diff sanmodel"

    @staticmethod
    def list_numdiff(a, b):
        len_a = len(a)
        len_b = len(b)
        len_min = min(len_a, len_b)
        console_debug(f"\tlen a: {len_a}")
        console_debug(f"\tlen b: {len_b}")
        console_debug(f"\tlen b - a: {len_b - len_a}")
        for i in range(0, len_min):
            if a[i] != b[i]:
                dif = (Vector(b[i])-Vector(a[i]))[:]
                console_debug(f"\t{i}: {dif}")

    def execute(self, context):
        if S.smd==None or S.smd_old==None:
            console_debug("diff: {S.smd} and/or {S.smd_old} is 'None'\n")
            return {"FINISHED"}
        for i, e in enumerate(S.seg_names):
            dif = S.smd.segments[i] != S.smd_old.segments[i]
            if dif:
                console_debug(f"{S.seg_names[i]} diff:")
                MESH_OT_debug_diff_sanmodel.list_numdiff(S.smd.segments[i], S.smd_old.segments[i])
        console_debug("checkdiff end\n")
        return {"FINISHED"}
class MESH_OT_debug_sanmodel(Operator):
    """debug operator for currently selected object [0]"""
    bl_idname = "test.debug_sanmodel"
    bl_label = "debug sanmodel"

 
    def execute(self, context):
        settings = context.scene.san_settings
        if not (context.selected_objects):
            console_notice("no object selected")
            self.report({"INFO"}, "No object selected")
            return {"CANCELLED"}

        obj = context.selected_objects[0]
        me = obj.data
        uv_layer = me.uv_layers.active.data

        console_notice("t")
        # for poly in me.polygons:
        #     console_debug("Polygon index: %d, length: %d" % (poly.index, poly.loop_total))

        #     # range is used here to show how the polygons reference loops,
        #     # for convenience 'poly.loop_indices' can be used instead.
        #     for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
        #         console_debug("    Vertex: %d" % me.loops[loop_index].vertex_index)
        #         # console_debug("    UV: %r" % uv_layer[loop_index].uv)

        console_debug(f"original mesh polygons: {len(me.polygons)}")
        console_debug(f"original mesh uv_layer ({me.uv_layers.active.name}): {len(me.uv_layers.active.data)}")
        console_debug(f"original mesh vertices: {len(me.vertices)}")
        console_debug(f"original mesh loops: {len(me.loops)}")
        # for loop in me.loops:
            # console_debug(f"{loop.vertex_index}: {loop.normal} {loop.tangent} {loop.bitangent} {loop.bitangent_sign}")
        # console_debug([e.uv[:] for e in me.uv_layers.active.data])
        console_debug("- - -")
        # mesh = MESH_OT_sanmodel_export.prepare_mesh(context, obj)
        # console_debug(f"evaluated mesh polygons: {len(mesh.polygons)}")
        # console_debug(f"evaluated mesh uv_layer ({mesh.uv_layers.active.name}): {len(mesh.uv_layers.active.data)}")
        # console_debug(f"evaluated mesh vertices: {len(mesh.vertices)}")
        # console_debug(f"evaluated mesh loops: {len(mesh.loops)}")
        # for loop in mesh.loops:
            # console_debug(f"{loop.vertex_index}: {loop.normal} {loop.tangent} {loop.bitangent} {loop.bitangent_sign}")
        # console_debug([e.uv[:] for e in mesh.uv_layers.active.data])
        console_debug("--------------")
        console_debug(S.smd)
        console_debug(S.seg_names)
        return {"FINISHED"}


#https://blender.stackexchange.com/questions/57306/how-to-create-a-custom-ui/57332#57332
#https://www.youtube.com/watch?v=opZy2OJp8co&list=PLa1F2ddGya_8acrgoQr1fTeIuQtkSd6BW
class SanmodelPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "sanmodel"
class VIEW_3D_PT_sanmodel_import_panel(SanmodelPanel, Panel):
    bl_label = "Import"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_import_panel"

    def draw(self, context):
        settings = context.scene.san_settings
        layout = self.layout

        # import button
        box = layout.box()
        box.operator("import.open_filebrowser",
            text = settings.path,
            icon = "IMPORT",
            )

        # details
        if settings.valid_file and S.smd:
            details = box.column(align=True)
            details.label(text="name: " + settings.name)
            details.label(text="vertices: " + settings.vertices)
            details.label(text="normals: " + settings.normals)
            details.label(text="tangents: " + settings.tangents)
            details.label(text="uv: " + settings.uv)
            details.label(text="uv2: " + settings.uv2)
            details.label(text="uv3: " + settings.uv3)
            details.label(text="colors: " + settings.colors)
            details.label(text="triangles: " + settings.triangles)
            details.label(text="bones: " + settings.bindposes)
            details.label(text="boneweights: " + settings.boneweights)

            # create model
            layout.operator("mesh.sanmodel_import",
                text="Create new object",
                icon="MESH_CUBE")
class VIEW_3D_PT_sanmodel_export_panel(SanmodelPanel, Panel):
    bl_label = "Export"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_export_panel"
    
    def draw(self, context):
        settings = context.scene.san_settings
        # rna_model_name = settings.bl_rna.properties["model_name"]

        col = self.layout.column(align=False)
        col.prop(settings, "model_name")
        col.operator("export.open_filebrowser",
            text="export",
            icon="EXPORT")
class VIEW_3D_PT_sanmodel_settings_panel(SanmodelPanel, Panel):
    bl_label = "Settings"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_settings_panel"
    
    def draw(self, context):
        settings = context.scene.san_settings
        layout = self.layout
        # rna_path = settings.bl_rna.properties["path"]
        rna_swap_yz = settings.bl_rna.properties["swap_yz_axis"]
        rna_mirror_uv_vertically = settings.bl_rna.properties["mirror_uv_vertically"]
        rna_use_vertex_color = settings.bl_rna.properties["use_vertex_colors"]
        rna_use_alpha = settings.bl_rna.properties["use_alpha"]
        rna_shading_nodes = settings.bl_rna.properties["shading_nodes"]
        
        # settings
        # layout.prop(settings, rna_path.identifier, text=rna_path.name)
        layout.prop(settings, rna_swap_yz.identifier, text=rna_swap_yz.name)
        layout.prop(settings, rna_mirror_uv_vertically.identifier, text=rna_mirror_uv_vertically.name)
        layout.prop(settings, rna_use_vertex_color.identifier, text=rna_use_vertex_color.name)
        if settings.use_vertex_colors:
            layout.prop(settings, rna_use_alpha.identifier, text=rna_use_alpha.name)
        layout.prop(settings, rna_shading_nodes.identifier, text=rna_shading_nodes.name)
class VIEW_3D_PT_sanmodel_debug_panel(SanmodelPanel, Panel):
    bl_label = "Debug"
    bl_idname = "SANMODEL_PANEL_PT_sanmodel_debug_panel"
    
    def draw(self, context):
        # settings = context.scene.san_settings
        layout = self.layout
        layout.operator("test.debug_sanmodel",
            text = "selected object debug",
            icon = "INFO")
        layout.operator("test.debug_diff_sanmodel",
            text = "diff of the 2 last imported .sanmodel",
            icon = "ARROW_LEFTRIGHT")

# UI example : File > import
# def import_menu_draw(self, context):
#     self.layout.operator("test.open_filebrowser",
#             text="Sanctuary model (.sanmodel)",
#             icon="EVENT_S")
# def export_menu_draw(self, context):
#     self.layout.operator("export.export_filebrowser",
#             text="Sanctuary model (.sanmodel)",
#             icon="EVENT_S")

blender_classes = [ 
    VIEW_3D_PT_sanmodel_import_panel,
    VIEW_3D_PT_sanmodel_export_panel,
    VIEW_3D_PT_sanmodel_settings_panel,
    VIEW_3D_PT_sanmodel_debug_panel,
    MESH_OT_debug_sanmodel,
    MESH_OT_debug_diff_sanmodel
]

def register():
    for bl_class in blender_classes:
        bpy.utils.register_class(bl_class)
    # bpy.types.TOPBAR_MT_file_import.append(import_menu_draw)
    # bpy.types.TOPBAR_MT_file_export.append(export_menu_draw)
    console_notice("panels.py registered")

def unregister():
    for bl_class in blender_classes:
        bpy.utils.unregister_class(bl_class)
    # bpy.types.TOPBAR_MT_file_import.remove(import_menu_draw)
    # bpy.types.TOPBAR_MT_file_export.remove(export_menu_draw)
    console_notice("panels.py unregistered")

if __name__ == "__main__":
    register()
