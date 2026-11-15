"""Portable locations. Camera calibration is data, not an operating-system setting."""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path, PureWindowsPath


def expand_path(value, base):
    expanded=os.path.expandvars(os.path.expanduser(str(value)))
    if '$' in expanded:
        raise ValueError(f'Unresolved environment variable in path: {value}')
    if os.name!='nt' and PureWindowsPath(expanded).drive:
        raise ValueError('Use a Linux path in WSL, such as /mnt/c/...; do not pass a Windows drive path')
    path=Path(expanded)
    return (path if path.is_absolute() else Path(base)/path).resolve()


@dataclass(frozen=True)
class RuntimePaths:
    project: Path
    data: Path
    models: Path
    calibration: Path
    outputs: Path

    @classmethod
    def discover(cls, project=None, load_local=True):
        project=Path(project or Path(__file__).resolve().parents[2]).resolve()
        if load_local:
            from dotenv import load_dotenv
            load_dotenv(project/'.env.local',override=False)
        home=Path.home()
        data=expand_path(os.environ.get('RVECTR_DATA_ROOT',home/'Videos'/'rvectr'),project)
        shared=expand_path(os.environ.get('XDG_DATA_HOME',home/'.local'/'share'),home)
        return cls(project,data,
                   expand_path(os.environ.get('RVECTR_MODELS_DIR',shared/'rvectr'/'models'),project),
                   expand_path(os.environ.get('RVECTR_CALIBRATION_DIR',data/'calibration'),project),
                   expand_path(os.environ.get('RVECTR_OUTPUT_ROOT',project/'outputs'),project))

    def video(self, value):
        return expand_path(value,self.data)

    def calibration_file(self,value):
        return expand_path(value,self.calibration)
