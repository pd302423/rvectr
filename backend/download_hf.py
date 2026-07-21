import os
import requests
import time

url = "https://huggingface.co/spaces/brjathu/HMR2.0/resolve/main/logs/train/multiruns/hmr2/0/checkpoints/epoch%3D35-step%3D1000000.ckpt"
dest = "/home/pd/.cache/4DHumans/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"

os.makedirs(os.path.dirname(dest), exist_ok=True)

# 2.5 GB
TOTAL_SIZE = 2500000000 
CHUNK_RECONNECT = 50 * 1024 * 1024  # 50MB before dropping connection

while True:
    headers = {}
    if os.path.exists(dest):
        downloaded = os.path.getsize(dest)
        if downloaded >= 2533314051: # The actual size of the checkpoint
            print("Download complete.")
            break
        
        headers['Range'] = f'bytes={downloaded}-{downloaded + CHUNK_RECONNECT - 1}'
        print(f"Resuming download from {downloaded} bytes...")
    else:
        downloaded = 0
        headers['Range'] = f'bytes=0-{CHUNK_RECONNECT - 1}'
        print("Starting download...")

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        # 206 Partial Content or 200 OK
        if response.status_code not in [200, 206]:
            if response.status_code == 416: # range not satisfiable (done)
                break
            response.raise_for_status()

        with open(dest, "ab" if downloaded > 0 else "wb") as f:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
                    
    except Exception as e:
        print(f"Error: {e}. Retrying in 2 seconds...")
        time.sleep(2)
