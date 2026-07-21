import os
import numpy as np
import pickle
import argparse

def convert_npz_to_pkl(npz_path, pkl_path):
    print(f"Converting {npz_path} to {pkl_path}...")
    try:
        data = np.load(npz_path, allow_pickle=True)
        # Convert NpzFile to standard dict
        data_dict = {key: data[key] for key in data.files}
        
        # SMPL requires 'f' (faces) to be int32 or uint32, and sometimes specific string encodings
        if 'f' in data_dict:
            data_dict['f'] = data_dict['f'].astype(np.int32)
            
        with open(pkl_path, 'wb') as f:
            pickle.dump(data_dict, f, protocol=2)
            
        print("Success!")
    except Exception as e:
        print(f"Error during conversion: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default=".", help="Directory containing .npz files")
    args = parser.parse_args()
    
    for file in os.listdir(args.input_dir):
        if file.endswith('.npz'):
            npz_path = os.path.join(args.input_dir, file)
            pkl_path = os.path.join(args.input_dir, file.replace('.npz', '.pkl'))
            convert_npz_to_pkl(npz_path, pkl_path)
