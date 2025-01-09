bl_info = {
    "name": "Grid Splitter",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > N-Panel > Grid Splitter",
    "description": "Split meshes into grid using boolean operations",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
import math
from bpy.props import FloatProperty, StringProperty
from bpy.types import Panel, Operator

class GridSplitterProperties(bpy.types.PropertyGroup):
    grid_size: FloatProperty(
        name="Grid Size",
        description="Size of each grid cell in meters",
        default=2.0,
        min=0.1,
        max=10.0
    )

class VIEW3D_PT_grid_splitter(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Grid Splitter'
    bl_label = "Grid Splitter"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene.grid_splitter, "grid_size")
        layout.operator("object.split_mesh_operator")

class SplitMeshOperator(Operator):
    bl_idname = "object.split_mesh_operator"
    bl_label = "Split Mesh"
    bl_description = "Split mesh into grid using boolean operations"
    
    def create_cutter(self, size, position):
        self.report({'INFO'}, f"Creating cutter at position {position}")
        bpy.ops.mesh.primitive_cube_add(size=size)
        cutter = bpy.context.active_object
        cutter.location = position
        return cutter

    def execute(self, context):
        if not context.active_object:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}
            
        original = context.active_object
        grid_size = context.scene.grid_splitter.grid_size
        
        # Calculate grid dimensions
        dims = original.dimensions
        cells_x = math.ceil(dims.x / grid_size)
        cells_y = math.ceil(dims.y / grid_size)
        total_cells = cells_x * cells_y
        
        self.report({'INFO'}, f"Starting split into {cells_x}x{cells_y} grid ({total_cells} pieces)")
        
        # Create grid of boolean cutters
        current_cell = 0
        for i in range(cells_x):
            for j in range(cells_y):
                current_cell += 1
                self.report({'INFO'}, f"Processing piece {current_cell}/{total_cells} ({int(current_cell/total_cells*100)}%)")
                
                # Calculate position
                pos_x = (i * grid_size) - (dims.x / 2) + (grid_size / 2)
                pos_y = (j * grid_size) - (dims.y / 2) + (grid_size / 2)
                pos_z = original.location.z
                
                # Create cutter
                cutter = self.create_cutter(grid_size, (pos_x, pos_y, pos_z))
                
                # Create copy of original
                bpy.ops.object.select_all(action='DESELECT')
                original.select_set(True)
                context.view_layer.objects.active = original
                bpy.ops.object.duplicate()
                current_piece = context.active_object
                
                # Name the piece
                current_piece.name = f"Grid_Piece_{i+1}_{j+1}"
                
                # Apply boolean intersection
                bool_mod = current_piece.modifiers.new(name="Boolean", type='BOOLEAN')
                bool_mod.object = cutter
                bool_mod.operation = 'INTERSECT'
                
                # Apply modifier
                bpy.ops.object.modifier_apply(modifier="Boolean")
                
                # Delete cutter
                bpy.ops.object.select_all(action='DESELECT')
                cutter.select_set(True)
                bpy.ops.object.delete()
        
        # Delete original
        bpy.ops.object.select_all(action='DESELECT')
        original.select_set(True)
        bpy.ops.object.delete()
        
        self.report({'INFO'}, "Splitting completed successfully!")
        return {'FINISHED'}

classes = (
    GridSplitterProperties,
    VIEW3D_PT_grid_splitter,
    SplitMeshOperator
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.grid_splitter = bpy.props.PointerProperty(type=GridSplitterProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.grid_splitter

if __name__ == "__main__":
    register()