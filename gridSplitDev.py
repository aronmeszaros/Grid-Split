bl_info = {
    "name": "Grid Splitter",
    "author": "Your Name",
    "version": (1, 3),
    "blender": (3, 6, 0),
    "location": "View3D > N-Panel > Grid Splitter",
    "description": "Split meshes into grid using boolean operations",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
import math
import time
from bpy.props import FloatProperty, BoolProperty
from bpy.types import Panel, Operator

class GridSplitterProperties(bpy.types.PropertyGroup):
    grid_size: FloatProperty(
        name="Grid Size",
        description="Size of each grid cell in meters",
        default=2.0,
        min=0.1
    )
    cutter_height: FloatProperty(
        name="Cutter Height",
        description="Height of the cutting volume",
        default=0.3,
        min=0.01
    )
    use_fast_mode: BoolProperty(
        name="Fast Mode",
        description="Process faster but less reliably",
        default=False
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
        layout.prop(scene.grid_splitter, "cutter_height")
        layout.prop(scene.grid_splitter, "use_fast_mode")
        layout.operator("object.split_mesh_operator")

class SplitMeshOperator(Operator):
    bl_idname = "object.split_mesh_operator"
    bl_label = "Split Mesh"
    bl_description = "Split mesh into grid using boolean operations"
    
    def create_cutter(self, size, height, position):
        self.report({'INFO'}, f"Creating cutter at position {position}")
        bpy.ops.mesh.primitive_cube_add()
        cutter = bpy.context.active_object
        cutter.scale = (size/2, size/2, height/2)
        cutter.location = position
        bpy.ops.object.transform_apply(scale=True)
        return cutter
    
    def verify_boolean_result(self, obj):
        """Check if boolean operation produced valid geometry"""
        return len(obj.data.vertices) > 0 and len(obj.data.polygons) > 0
    
    def wait_for_boolean(self, context):
        """Force Blender to complete pending operations"""
        context.view_layer.update()
        context.view_layer.depsgraph.update()
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

    def retry_boolean_operation(self, current_piece, cutter, context, position_offset=0.0):
        """Attempt boolean operation with different settings"""
        # Try with exact solver first
        bool_mod = current_piece.modifiers.new(name="Boolean", type='BOOLEAN')
        bool_mod.object = cutter
        bool_mod.operation = 'INTERSECT'
        bool_mod.solver = 'EXACT'
        
        try:
            bpy.ops.object.modifier_apply(modifier="Boolean")
            if self.verify_boolean_result(current_piece):
                return True
        except:
            pass
            
        # If exact solver failed, try with fast solver
        bool_mod = current_piece.modifiers.new(name="Boolean", type='BOOLEAN')
        bool_mod.object = cutter
        bool_mod.operation = 'INTERSECT'
        bool_mod.solver = 'FAST'
        
        try:
            bpy.ops.object.modifier_apply(modifier="Boolean")
            if self.verify_boolean_result(current_piece):
                return True
        except:
            pass
            
        # If both solvers failed, try with slight position offset
        if position_offset == 0.0:
            cutter.location.x += 0.001
            cutter.location.y += 0.001
            return self.retry_boolean_operation(current_piece, cutter, context, 0.001)
            
        return False

    def cleanup_empty_pieces(self, context, grid_collection):
        """Remove pieces with no valid geometry"""
        for obj in grid_collection.objects:
            if not self.verify_boolean_result(obj):
                grid_collection.objects.unlink(obj)
                bpy.data.objects.remove(obj, do_unlink=True)

    def execute(self, context):
        if not context.active_object:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}
            
        # Store start time for progress reporting
        start_time = time.time()
        
        original = context.active_object
        grid_size = context.scene.grid_splitter.grid_size
        cutter_height = context.scene.grid_splitter.cutter_height
        fast_mode = context.scene.grid_splitter.use_fast_mode
        
        # Clean up existing collection if it exists
        if "Grid_Pieces" in bpy.data.collections:
            grid_collection = bpy.data.collections["Grid_Pieces"]
            for obj in grid_collection.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(grid_collection)
        
        # Create new collection for the grid pieces
        grid_collection = bpy.data.collections.new(name="Grid_Pieces")
        bpy.context.scene.collection.children.link(grid_collection)
        
        # Apply all transformations to original
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Calculate grid dimensions
        dims = original.dimensions
        cells_x = math.ceil(dims.x / grid_size)
        cells_y = math.ceil(dims.y / grid_size)
        total_cells = cells_x * cells_y
        
        self.report({'INFO'}, f"Starting split into {cells_x}x{cells_y} grid ({total_cells} pieces)")
        
        # Track failed operations for retry
        failed_operations = []
        
        # Create grid of boolean cutters
        current_cell = 0
        for i in range(cells_x):
            for j in range(cells_y):
                current_cell += 1
                
                # Calculate position
                pos_x = (i * grid_size) - (dims.x / 2) + (grid_size / 2)
                pos_y = (j * grid_size) - (dims.y / 2) + (grid_size / 2)
                pos_z = original.location.z
                
                # Progress report with time estimate
                elapsed_time = time.time() - start_time
                avg_time_per_cell = elapsed_time / current_cell
                remaining_cells = total_cells - current_cell
                estimated_remaining = avg_time_per_cell * remaining_cells
                
                self.report({'INFO'}, 
                    f"Processing piece {current_cell}/{total_cells} "
                    f"({int(current_cell/total_cells*100)}%) - "
                    f"Est. remaining time: {int(estimated_remaining/60)}m {int(estimated_remaining%60)}s")
                
                # Create cutter
                cutter = self.create_cutter(grid_size, cutter_height, (pos_x, pos_y, pos_z))
                
                # Create copy of original
                bpy.ops.object.select_all(action='DESELECT')
                original.select_set(True)
                context.view_layer.objects.active = original
                bpy.ops.object.duplicate()
                current_piece = context.active_object
                
                # Handle collections properly
                for coll in current_piece.users_collection:
                    coll.objects.unlink(current_piece)
                grid_collection.objects.link(current_piece)
                
                # Name the piece
                current_piece.name = f"Grid_Piece_{i+1}_{j+1}"
                
                # Apply boolean operation with retry mechanism
                try:
                    if not self.retry_boolean_operation(current_piece, cutter, context):
                        failed_operations.append({
                            'position': (i, j),
                            'coords': (pos_x, pos_y, pos_z),
                            'piece_name': f"Grid_Piece_{i+1}_{j+1}"
                        })
                        self.report({'WARNING'}, 
                            f"Failed to create valid geometry for piece {i+1}_{j+1} "
                            f"at position ({pos_x:.2f}, {pos_y:.2f}, {pos_z:.2f})")
                        
                        # Save failed piece coordinates to a text file
                        bpy.data.texts.new(name=f"failed_piece_{i+1}_{j+1}_coords.txt").write(
                            f"Position: ({pos_x}, {pos_y}, {pos_z})\n"
                            f"Grid position: ({i+1}, {j+1})"
                        )
                except Exception as e:
                    failed_operations.append({
                        'position': (i, j),
                        'coords': (pos_x, pos_y, pos_z)
                    })
                    self.report({'WARNING'}, f"Error processing piece {i+1}_{j+1}: {str(e)}")
                
                # Delete cutter
                bpy.ops.object.select_all(action='DESELECT')
                cutter.select_set(True)
                bpy.ops.object.delete()
        
        # Clean up empty pieces
        self.cleanup_empty_pieces(context, grid_collection)
        
        # Hide original instead of deleting it
        original.hide_viewport = True
        original.hide_render = True
        
        # Move original to grid collection
        for coll in original.users_collection:
            coll.objects.unlink(original)
        grid_collection.objects.link(original)
        
        # Report failed operations
        if failed_operations:
            self.report({'WARNING'}, 
                f"Failed to process {len(failed_operations)} pieces. "
                "These areas may appear as 'holes' in the final result.")
        
        total_time = time.time() - start_time
        self.report({'INFO'}, 
            f"Splitting completed in {int(total_time/60)}m {int(total_time%60)}s "
            f"with {len(failed_operations)} failed operations")
        
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