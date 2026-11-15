import json
import os
import sys
from pathlib import Path
import numpy as np
import pytest
from rvectr.paths import RuntimePaths,expand_path
from rvectr.configuration import load_capture_config,load_camera_calibration


def test_local_paths_do_not_change_relative_capture_config(tmp_path,monkeypatch):
    monkeypatch.setenv('RVECTR_DATA_ROOT',str(tmp_path/'private data'))
    monkeypatch.setenv('RVECTR_MODELS_DIR',str(tmp_path/'licensed models'))
    monkeypatch.setenv('RVECTR_OUTPUT_ROOT','outputs')
    paths=RuntimePaths.discover(tmp_path,load_local=False)
    assert paths.video('v1/cam.mp4')==tmp_path/'private data'/'v1'/'cam.mp4'
    assert paths.models==tmp_path/'licensed models'
    assert paths.outputs==tmp_path/'outputs'


def test_cross_platform_windows_path_is_not_silently_reinterpreted(tmp_path):
    if os.name=='nt':pytest.skip('Linux-only path boundary')
    with pytest.raises(ValueError):expand_path(r'C:\Videos\rvectr',tmp_path)


def test_camera_ids_cannot_escape_output_directories(tmp_path):
    config=tmp_path/'config.json'
    config.write_text(json.dumps({'cameras':[{'id':'../escape','video':'a.mp4'},{'id':'cam2','video':'b.mp4'}]}))
    with pytest.raises(ValueError):load_capture_config(config)


def test_mode_and_resolution_must_match_before_reusing_calibration(tmp_path):
    record={'camera_id':'cam1','status':'passed','recording_mode_verified':False,
            'image_size':[1080,1920],'K':[[1000,0,540],[0,1000,960],[0,0,1]],
            'distortion':[0]*5,'R':np.eye(3).tolist(),'t':[0,0,3],
            'units':'m','board_frame_id':'identified-board-origin'}
    path=tmp_path/'cam1.json'
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):load_camera_calibration(path,'cam1',[1080,1920])
    record['recording_mode_verified']=True
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):load_camera_calibration(path,'cam1',[2160,3840])
    assert load_camera_calibration(path,'cam1',[1080,1920])['camera_id']=='cam1'
