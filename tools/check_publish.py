#!/usr/bin/env python3
"""Check source files and optionally reachable Git history; never print secrets."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess

ASSET_SUFFIXES={'.pkl','.pickle','.npz','.npy','.onnx','.pt','.pth','.ckpt','.safetensors',
                '.task','.obj','.glb','.gltf','.blend','.blend1','.fbx','.ply','.stl',
                '.mp4','.mov','.avi','.webm','.wav','.mp3','.m4a','.aac','.flac',
                '.zip','.7z','.tar','.gz','.zst','.pdf','.png','.jpg','.jpeg'}
PRIVATE_DIRS={'node_modules','.next','__pycache__','.pytest_cache','outputs','models',
              'calibration','.local-state','.publish','exports','videos','videos2'}
GENERATED={'backend/squat_kinematics.json','backend/running_kinematics.json','backend/squat_dataset.json'}
SECRET_PATTERNS={
    'AWS access key':re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'GitHub token':re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    'private key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'OpenAI-style key':re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b'),
}

def source_icon(path):
    if path.suffix.lower()!='.ico':return False
    with path.open('rb') as stream:return stream.read(4) in {b'\x00\x00\x01\x00',b'\x00\x00\x02\x00'}


def git(root,*args):
    command=['git','--git-dir',str(root/'.git'),'--work-tree',str(root),*args]
    result=subprocess.run(command,capture_output=True,check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace').strip())
    return result.stdout


def source_candidates(root):
    return sorted({p.decode('utf-8') for p in git(root,'ls-files','-z','--cached','--others','--exclude-standard').split(b'\0') if p})


def excluded_reason(name):
    if name in {'outputs/README.md','models/README.md'}:return None
    path=Path(name)
    if any(p in PRIVATE_DIRS or p.startswith('.venv') for p in path.parts):
        return 'private assets, output or regenerable environment'
    if path.name.startswith('.env') and path.name!='.env.example':
        return 'local environment file'
    if path.suffix.lower() in ASSET_SUFFIXES or name in GENERATED:
        return 'model, media, generated measurement or binary artifact'
    if path.name in {'credentials','auth.json','id_rsa','id_ed25519'}:
        return 'credential material'
    return None


def inspect(root,include_history=False):
    root=Path(root).resolve()
    findings=[]
    scanned=0
    for name in source_candidates(root):
        path=root/name
        if not path.is_file():
            continue  # Gitlinks are source dependency references, not local model files.
        reason=excluded_reason(name)
        if path.is_symlink(): reason='symlink requires explicit target/content review'
        if path.stat().st_size>10*1024*1024: reason='file exceeds the source-only size limit'
        if reason:
            findings.append({'scope':'working_tree','path':name,'reason':reason})
            continue
        scanned+=1
        if source_icon(path):continue
        try: content=path.read_text(encoding='utf-8')
        except (UnicodeError,OSError):
            findings.append({'scope':'working_tree','path':name,'reason':'unreviewed binary/non-UTF8 content'})
            continue
        for label,pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(content):
                findings.append({'scope':'working_tree','path':name,
                                 'line':content.count('\n',0,match.start())+1,'reason':label})
    history=[]
    if include_history:
        for line in git(root,'rev-list','--objects','--all').decode('utf-8').splitlines():
            _,separator,name=line.partition(' ')
            if separator and (reason:=excluded_reason(name)):
                history.append({'path':name,'reason':reason})
    return {'passed':not findings and not history,'source_files_scanned':scanned,
            'working_tree_findings':findings,'history_findings':history,
            'history_scanned':include_history,
            'scope':'Technical publication guard; does not certify ownership or license compatibility'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--history',action='store_true')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    report=inspect(args.root,args.history)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['history_findings','working_tree_findings']},indent=2))
    print(f'Working-tree findings: {len(report["working_tree_findings"])}; history findings: {len(report["history_findings"])}')
    for item in report['working_tree_findings'][:20]:
        print(f'{item["path"]}: {item["reason"]}')
    return 0 if report['passed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
