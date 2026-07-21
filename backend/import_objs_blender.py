import bpy
import os
import glob

# Clear existing objects to start fresh
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.select_by_type(type='MESH')
bpy.ops.object.delete()

obj_dir = "/home/pd/Documents/rvector/backend/squat_demo_out"
obj_files = sorted(glob.glob(os.path.join(obj_dir, "*.obj")))

# Set end frame
bpy.context.scene.frame_end = len(obj_files)
print(f"Found {len(obj_files)} OBJs to import")

for i, obj_path in enumerate(obj_files):
    frame_num = i + 1
    
    # Deselect all before importing
    bpy.ops.object.select_all(action='DESELECT')
    
    # Import the OBJ (Handle different Blender version APIs)
    try:
        bpy.ops.wm.obj_import(filepath=obj_path)
    except AttributeError:
        bpy.ops.import_scene.obj(filepath=obj_path)
        
    # The imported objects are now selected
    imported_objs = bpy.context.selected_objects
    
    for obj in imported_objs:
        # Hide on frame before
        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=frame_num - 1)
        obj.keyframe_insert(data_path="hide_render", frame=frame_num - 1)
        
        # Show on current frame
        obj.hide_viewport = False
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_viewport", frame=frame_num)
        obj.keyframe_insert(data_path="hide_render", frame=frame_num)
        
        # Hide on frame after
        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=frame_num + 1)
        obj.keyframe_insert(data_path="hide_render", frame=frame_num + 1)
    
    if i % 10 == 0:
        print(f"Imported frame {frame_num}/{len(obj_files)}")

# Save the blend file
save_path = "/home/pd/.gemini/antigravity-cli/brain/0ee7170b-bb9a-4e93-9706-2c2d4575d277/animated_squat.blend"
bpy.ops.wm.save_as_mainfile(filepath=save_path)
print(f"Successfully saved complete animation to {save_path}")
