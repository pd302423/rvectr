"""
smartphone_sync.py — 3-Smartphone Multi-View Video Synchronization

Syncs 3 smartphone video streams (e.g. Front, Left, Right views) for EasyMocap:
1. Extracts audio tracks from each video file.
2. Detects the sharp audio clap / flash transient peak across all 3 tracks.
3. Calculates exact millisecond frame offsets.
4. Transcodes all 3 videos to exact Constant Frame Rate (CFR 30.000 FPS).
5. Outputs perfectly frame-aligned synchronized MP4s ready for EasyMocap 3D fitting.

Usage:
    python smartphone_sync.py --cam1 front.mp4 --cam2 left.mp4 --cam3 right.mp4 --output-dir ./synced_cams/
"""

import argparse
import os
import subprocess
import sys
import numpy as np
from scipy.io import wavfile


def extract_audio(video_path: str, wav_path: str):
    """Extract audio track as 44.1kHz mono WAV file using ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "44100",
        wav_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def find_clap_peak(wav_path: str) -> float:
    """Find timestamp (in seconds) of the loudest audio transient peak (e.g. clap)."""
    sample_rate, data = wavfile.read(wav_path)
    data = data.astype(np.float32)
    
    # Compute absolute amplitude envelope
    envelope = np.abs(data)
    
    # Find index of maximum peak
    peak_idx = np.argmax(envelope)
    peak_time_sec = peak_idx / sample_rate
    return peak_time_sec


def sync_and_transcode_video(
    video_path: str,
    start_sec: float,
    out_path: str,
    fps: float = 30.0,
    duration_sec: float | None = None
):
    """
    Trim video from start_sec and convert to exact Constant Frame Rate (CFR).
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.4f}",
        "-i", video_path,
        "-r", str(fps),
        "-vsync", "cfr",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-c:a", "aac"
    ]
    if duration_sec is not None:
        cmd.extend(["-t", f"{duration_sec:.4f}"])
    cmd.append(out_path)

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def sync_3_smartphones(cam1_path: str, cam2_path: str, cam3_path: str, output_dir: str, fps: float = 30.0):
    """Main synchronization pipeline for 3 smartphone recordings."""
    os.makedirs(output_dir, exist_ok=True)

    wav1 = os.path.join(output_dir, "temp_cam1.wav")
    wav2 = os.path.join(output_dir, "temp_cam2.wav")
    wav3 = os.path.join(output_dir, "temp_cam3.wav")

    print("[*] Extracting audio tracks for audio clap synchronization...")
    extract_audio(cam1_path, wav1)
    extract_audio(cam2_path, wav2)
    extract_audio(cam3_path, wav3)

    print("[*] Detecting audio clap peak timestamps...")
    p1 = find_clap_peak(wav1)
    p2 = find_clap_peak(wav2)
    p3 = find_clap_peak(wav3)

    print(f"    Cam 1 Clap Peak: {p1:.3f} s")
    print(f"    Cam 2 Clap Peak: {p2:.3f} s")
    print(f"    Cam 3 Clap Peak: {p3:.3f} s")

    # Clean up temporary WAVs
    for w in [wav1, wav2, wav3]:
        if os.path.exists(w):
            os.remove(w)

    print("[*] Transcoding and frame-locking videos to 30.000 CFR...")
    out1 = os.path.join(output_dir, "cam01_synced.mp4")
    out2 = os.path.join(output_dir, "cam02_synced.mp4")
    out3 = os.path.join(output_dir, "cam03_synced.mp4")

    sync_and_transcode_video(cam1_path, p1, out1, fps=fps)
    sync_and_transcode_video(cam2_path, p2, out2, fps=fps)
    sync_and_transcode_video(cam3_path, p3, out3, fps=fps)

    print(f"[✓] Synchronization Complete! Frame 0 aligned to clap event.")
    print(f"    Camera 1: {out1}")
    print(f"    Camera 2: {out2}")
    print(f"    Camera 3: {out3}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize 3 Smartphone Videos for EasyMocap")
    parser.add_argument("--cam1", required=True, help="Path to Camera 1 (Front) video")
    parser.add_argument("--cam2", required=True, help="Path to Camera 2 (Left) video")
    parser.add_argument("--cam3", required=True, help="Path to Camera 3 (Right) video")
    parser.add_argument("--output-dir", default="./synced_cams", help="Output directory for synchronized videos")
    parser.add_argument("--fps", type=float, default=30.0, help="Target constant frame rate (default: 30.0)")

    args = parser.parse_args()
    sync_3_smartphones(args.cam1, args.cam2, args.cam3, args.output_dir, args.fps)
