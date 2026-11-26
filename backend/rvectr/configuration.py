"""Validate calibration identity and capture-mode compatibility explicitly."""
import json
from pathlib import Path
from .calibration import validate_camera


def load_capture_config(path):
    config=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict):
        raise ValueError("The capture configuration must be a JSON object")
    cameras = config.get("cameras", [])
    if not isinstance(cameras, list) or not all(isinstance(camera, dict) for camera in cameras):
        raise ValueError("cameras must be an array of camera objects")
    if len(cameras)<2:
        raise ValueError('A multiview capture configuration needs at least two cameras')
    names=[camera.get('id') for camera in cameras]
    if any(not isinstance(name,str) or not name or not name.replace('_','').replace('-','').isalnum() for name in names):
        raise ValueError('Camera IDs must be nonempty alphanumeric names with optional _ or -')
    if len(set(names))!=len(names) or any(not camera.get('video') for camera in cameras):
        raise ValueError('Camera IDs must be unique and each camera must name a video')
    return config


def load_camera_calibration(path, camera_id, image_size):
    record=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if record.get('camera_id')!=camera_id:
        raise ValueError('Calibration camera ID does not match the capture configuration')
    if record.get('status')!='passed' or record.get('recording_mode_verified') is not True:
        raise ValueError('Calibration must pass quality checks and explicitly match the recording mode')
    validate_camera(record,image_size=image_size)
    if record.get('units')!='m' or not record.get('board_frame_id'):
        raise ValueError('Metric calibration needs metres and an identified shared physical frame')
    return record
