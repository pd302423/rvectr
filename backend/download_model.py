import os
import requests
import time

url = "https://www.cs.utexas.edu/~pavlakos/4dhumans/hmr2_data.tar.gz"
dest = "/home/pd/.cache/4DHumans/hmr2_data.tar.gz"

os.makedirs(os.path.dirname(dest), exist_ok=True)

while True:
    headers = {}
    if os.path.exists(dest):
        downloaded = os.path.getsize(dest)
        if downloaded >= 2710589440:
            print("Download complete.")
            break
        headers['Range'] = f'bytes={downloaded}-'
        print(f"Resuming download from {downloaded} bytes...")
    else:
        downloaded = 0
        print("Starting download...")

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()

        with open(dest, "ab" if downloaded > 0 else "wb") as f:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        print(f"Error: {e}. Retrying in 2 seconds...")
        time.sleep(2)
