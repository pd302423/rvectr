#!/usr/bin/env python3
"""Versioned capture diagnostics. Reconstruction integration remains unfinished.

Never promotes uncalibrated videos into metric 3D or claims validation.
"""
import argparse
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import sys
import traceback

from rvectr.media import probe
from rvectr.paths import RuntimePaths
from rvectr.configuration import load_capture_config, load_camera_calibration
from rvectr.records import allocate_run, sha256, utc_now, write_json
from rvectr.sync import estimate_audio_offset
from rvectr.media import decode_audio


COMMANDS = ('calibrate-intrinsics', 'calibrate-extrinsics', 'sync', 'run', 'check-points', 'frames')


def main():
    if len(sys.argv)>1 and sys.argv[1] in COMMANDS:
        from rvectr.commands import dispatch
        return dispatch(sys.argv[1], sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='doctor':
        from rvectr.doctor import inspect_environment
        doctor_parser=argparse.ArgumentParser(description='Check the runtime; camera accuracy is evaluated separately')
        doctor_parser.add_argument('--require-cuda',action='store_true')
        doctor_parser.add_argument('--report',type=Path)
        doctor_args=doctor_parser.parse_args(sys.argv[2:])
        result=inspect_environment(require_cuda=doctor_args.require_cuda)
        if doctor_args.report:write_json(doctor_args.report,result)
        print(json.dumps(result,indent=2))
        return 0 if result['passed'] else 1
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog='Two-camera squat pipeline commands (see docs/TWO_CAMERA_PIPELINE.md):\n  '
                                            + '\n  '.join(f'rvectr {c} --help' for c in COMMANDS)
                                            + '\n  rvectr doctor')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--diagnose-only', action='store_true',
                        help='Required until the reconstruction stages are integrated and tested')
    parser.add_argument('--output-root', type=Path)
    args = parser.parse_args()
    if not args.diagnose_only:
        parser.error('Reconstruction integration is unfinished. Use --diagnose-only; no metric result will be invented.')
    paths=RuntimePaths.discover()
    project=paths.project
    config=load_capture_config(args.config)
    data_root=paths.data
    run=allocate_run(args.output_root or paths.outputs)
    manifest = {'schema_version':1, 'run_id':run.name, 'created_utc':utc_now(),
                'status':'running', 'mode':'diagnostics', 'accuracy_validated':False,
                'project_root':str(project), 'data_root':str(data_root), 'config':config,
                'python':sys.version, 'platform':platform.platform(), 'inputs':[],
                'source_sha256':{str(p.relative_to(project)):sha256(p)
                                 for p in sorted((project/'backend'/'rvectr').glob('*.py'))}}
    write_json(run/'manifest.json', manifest)
    try:
        metadata, audio = [], []
        for camera in config['cameras']:
            path = paths.video(camera['video'])
            print(f'Inspecting {camera["id"]}: {path}', flush=True)
            info = probe(path)
            write_json(run/'inputs'/f'{camera["id"]}_metadata.json', info)
            manifest['inputs'].append({'camera':camera['id'], 'path':str(path),
                                       'size_bytes':path.stat().st_size, 'sha256':sha256(path)})
            metadata.append(info)
            # Decode the embedded tracks so their stream start timestamps are known.
            if info['audio'] is not None:
                samples, sr = decode_audio(path)
                audio.append((samples, sr, float(info['audio'].get('start_time',0))))
            else:
                audio.append(None)
        sync = []
        if audio and audio[0] is not None:
            for index in range(1,len(audio)):
                if audio[index] is None:
                    sync.append({'camera':config['cameras'][index]['id'], 'status':'unresolved', 'reason':'No embedded audio'})
                else:
                    a,b=audio[0],audio[index]
                    sync.append({'camera':config['cameras'][index]['id'],
                                 **estimate_audio_offset(a[0],b[0],a[1],a[2],b[2])})
        else:
            sync=[{'status':'unresolved','reason':'Reference camera has no embedded audio'}]
        write_json(run/'sync'/'audio_candidates.json',sync)
        calibration=[]
        for camera,info in zip(config['cameras'],metadata):
            location=camera.get('calibration')
            try:
                if not location:
                    raise ValueError('No calibration file supplied')
                record=load_camera_calibration(paths.calibration_file(location),camera['id'],info['image_size'])
                calibration.append({'camera':camera['id'],'status':'passed','record':record})
            except (ValueError,OSError) as error:
                calibration.append({'camera':camera['id'],'status':'unavailable','reason':str(error)})
        write_json(run/'calibration'/'status.json',calibration)
        calibrated=all(item['status']=='passed' for item in calibration)
        if calibrated and len({item['record']['board_frame_id'] for item in calibration})!=1:
            calibrated=False
        report={'run_id':run.name, 'status':'blocked_integration' if calibrated else 'blocked_calibration', 'metric_3d_available':False,
                'smpl_fitting_performed':False, 'pose_inference_performed':False,
                'reason':('Reconstruction integration is unfinished.' if calibrated else
                          'No independently calibrated cameras for these recording modes; reconstruction integration is unfinished.'),
                'recordings':[{'camera':c['id'],'image_size':m['image_size'],
                               'median_fps':m['median_fps'],'duration_s':m['duration_s'],
                               'frame_count':m['frame_count']} for c,m in zip(config['cameras'],metadata)],
                'synchronization':sync,'calibration':calibration,
                'required_before_reconstruction':['Per-camera intrinsics and distortion for the actual recording mode',
                                                  'Extrinsics in a common identified physical coordinate frame',
                                                  'Exposure alignment checks and residual timing uncertainty',
                                                  'Integrate and validate detector, reconstruction, fitting and viewer'],
                'reference_accuracy':{'measured':False,'reason':'No independent reference measurements supplied'}}
        write_json(run/'report.json',report)
        manifest.update(status=report['status'],completed_utc=utc_now())
        write_json(run/'manifest.json',manifest)
        print(f'Saved {run}: {report["status"]}',flush=True)
        return 0
    except Exception as error:
        manifest.update(status='failed',completed_utc=utc_now(),error=str(error))
        write_json(run/'manifest.json',manifest)
        (run/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise


if __name__=='__main__':
    raise SystemExit(main())
