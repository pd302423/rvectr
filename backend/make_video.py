import cv2
import os
import glob
import mediapipe as mp
import numpy as np

def process_and_compile(input_dir, output_file, fps=30):
    search_path = os.path.join(input_dir, '*_all.png')
    files = sorted(glob.glob(search_path))
    
    if not files:
        print(f"No *_all.png files found in {input_dir}")
        return

    # Load OpenCV face detector
    face_cascade = cv2.CascadeClassifier('/home/pd/Documents/rvector/backend/haarcascade_frontalface_default.xml')

    first_frame = cv2.imread(files[0])
    height, width, layers = first_frame.shape

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

    print(f"Compiling {len(files)} frames into {output_file}...")

    for i, file in enumerate(files):
        img = cv2.imread(file)
        if img is None:
            continue
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        for (x, y, w, h) in faces:
            pad_x = int(w * 0.2)
            pad_y = int(h * 0.2)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(width, x + w + pad_x)
            y2 = min(height, y + h + pad_y)
            
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)

        out.write(img)
        if i % 10 == 0:
            print(f"Processed {i}/{len(files)} frames")

    out.release()
    print("Video saved successfully!")

if __name__ == '__main__':
    input_directory = '/home/pd/Documents/rvector/backend/squat_demo_out'
    output_video = '/home/pd/.gemini/antigravity-cli/brain/0ee7170b-bb9a-4e93-9706-2c2d4575d277/final_squat_overlay_blackbox.mp4'
    process_and_compile(input_directory, output_video, fps=30)
