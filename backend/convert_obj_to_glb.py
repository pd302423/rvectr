import os
import argparse
import trimesh

def convert_obj_to_glb(input_dir, output_file):
    """
    Combines a sequence of OBJ files into a single GLB animation,
    or converts a single OBJ to GLB if there's only one.
    Note: A full animation with multiple frames as morph targets or
    skeletal animation is complex to build natively in trimesh.
    This script provides a basic single-mesh or scene conversion.
    For rich SMPL animations, Blender's Python API is recommended.
    """
    print(f"Reading OBJs from {input_dir}...")
    obj_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.obj')])
    
    if not obj_files:
        print("No OBJ files found.")
        return

    # In a real pipeline, you would use a skeletal animation or morph targets.
    # Here we just convert the first frame as a demonstration to get it into three.js
    first_mesh_path = os.path.join(input_dir, obj_files[0])
    print(f"Loading {first_mesh_path}...")
    mesh = trimesh.load(first_mesh_path)
    
    print(f"Exporting to {output_file}...")
    mesh.export(output_file)
    print("Export complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert OBJ sequence to GLB")
    parser.add_argument("--input", required=True, help="Directory containing OBJ files")
    parser.add_argument("--output", required=True, help="Output GLB file path")
    args = parser.parse_args()
    
    convert_obj_to_glb(args.input, args.output)
