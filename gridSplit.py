import bpy
import math

def create_cutter(size, position):
    bpy.ops.mesh.primitive_cube_add(size=size)
    cutter = bpy.context.active_object
    cutter.location = position
    return cutter

def split_mesh():
    original = bpy.context.active_object
    grid_size = 2  # Size of each grid cell
    
    # Calculate grid dimensions
    dims = original.dimensions
    cells_x = math.ceil(dims.x / grid_size)
    cells_y = math.ceil(dims.y / grid_size)
    
    # Create grid of boolean cutters
    for i in range(cells_x):
        for j in range(cells_y):
            # Calculate position
            pos_x = (i * grid_size) - (dims.x / 2) + (grid_size / 2)
            pos_y = (j * grid_size) - (dims.y / 2) + (grid_size / 2)
            pos_z = original.location.z
            
            # Create cutter
            cutter = create_cutter(grid_size, (pos_x, pos_y, pos_z))
            
            # Create copy of original
            bpy.ops.object.select_all(action='DESELECT')
            original.select_set(True)
            bpy.context.view_layer.objects.active = original
            bpy.ops.object.duplicate()
            current_piece = bpy.context.active_object
            
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

split_mesh()