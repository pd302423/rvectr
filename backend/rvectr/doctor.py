"""Environment checks distinguish GPU visibility from a successful CUDA operation."""
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from .paths import RuntimePaths


def native_tool(name):
    if platform.system()=='Linux':
        local=Path.home()/'.local'/'bin'/name
        if local.is_file() and os.access(local,os.X_OK):return str(local)
    found=shutil.which(name)
    if platform.system()=='Linux' and found and (found.lower().endswith('.exe') or found.startswith('/mnt/c/')):
        return None
    return found


def inspect_environment(require_cuda=False):
    paths=RuntimePaths.discover()
    result={'platform':platform.platform(),'python':sys.version,'executable':sys.executable,
            'paths':{key:str(value) for key,value in vars(paths).items()},
            'tools':{name:native_tool(name) for name in ['ffmpeg','ffprobe','git','node','npm']},
            'models':{'SMPL_NEUTRAL.pkl':(paths.models/'smpl'/'SMPL_NEUTRAL.pkl').is_file() or
                                           (paths.models/'SMPL_NEUTRAL.pkl').is_file()},
            'packages':{},'cuda':{'available':False,'operation_verified':False}}
    for name in ['numpy','opencv-contrib-python-headless','smplx','torch','onnxruntime','onnxruntime-gpu','rtmlib']:
        try: result['packages'][name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: result['packages'][name]=None
    try:
        import torch
        available=torch.cuda.is_available()
        result['cuda'].update(available=available,torch_cuda_version=torch.version.cuda)
        if available:
            tensor=torch.randn(64,64,device='cuda')
            value=(tensor@tensor).mean().item()
            torch.cuda.synchronize()
            result['cuda'].update(operation_verified=True,device=torch.cuda.get_device_name(0),result=value)
    except Exception as error:
        result['cuda']['error']=str(error)
    result['ready_for_diagnostics']=all(result['tools'][name] for name in ['ffmpeg','ffprobe'])
    result['passed']=result['ready_for_diagnostics'] and (not require_cuda or result['cuda']['operation_verified'])
    result['accuracy_validated']=False
    return result
