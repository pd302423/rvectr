#!/usr/bin/env python3
"""Check source files and optionally reachable Git history; never print secrets."""
from __future__ import annotations
import argparse
import json
import os
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
    command=['git','-C',str(root),*args]
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


def names(data):
    return {os.fsdecode(p) for p in data.split(b'\0') if p}


def default_base(root):
    for ref in ('refs/remotes/upstream/main', 'refs/remotes/origin/main', 'refs/heads/main'):
        if subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', '--quiet', ref],
                          stdout=subprocess.DEVNULL).returncode == 0:
            return git(root, 'merge-base', ref, 'HEAD').decode().strip()
    return None


def check_bytes(name, content, mode='100644'):
    reason = excluded_reason(name)
    if mode == '120000':
        reason = 'symlink requires explicit target/content review'
    if reason:
        return [{'path': name, 'reason': reason}]
    if len(content) > 10 * 1024 * 1024:
        return [{'path': name, 'reason': 'file exceeds the source-only size limit'}]
    if Path(name).suffix.lower() == '.ico' and content[:4] in (b'\0\0\1\0', b'\0\0\2\0'):
        return []
    try:
        text = content.decode('utf-8')
    except UnicodeError:
        return [{'path': name, 'reason': 'unreviewed binary/non-UTF8 content'}]
    return [{'path': name, 'reason': label, 'line': text.count('\n', 0, match.start()) + 1}
            for label, pattern in SECRET_PATTERNS.items() for match in pattern.finditer(text)]


def scan_git_changes(root, changes, seen, scope):
    findings = []
    fields = iter(changes.rstrip(b'\0').split(b'\0')) if changes else ()
    for header in fields:
        name = os.fsdecode(next(fields))
        _, mode, _, blob, _ = header.decode('ascii').split()
        if (name, blob, mode) in seen or mode == '160000':
            continue
        seen.add((name, blob, mode))
        if not excluded_reason(name) and int(git(root, 'cat-file', '-s', blob)) > 10*1024*1024:
            findings.append({'path': name, 'reason': 'file exceeds the source-only size limit',
                             'scope': scope, 'blob': blob})
            continue
        content = b'' if excluded_reason(name) else git(root, 'cat-file', 'blob', blob)
        findings.extend(dict(item, scope=scope, blob=blob) for item in check_bytes(name, content, mode))
    return findings


def inspect(root, include_history=False, base=None, tip='HEAD', commits_only=False):
    root = Path(root).resolve()
    options = ('--raw', '-z', '--no-abbrev', '--no-renames', '--diff-filter=AMT')
    seen = set()
    working = []
    scanned = 0
    files = set(source_candidates(root))
    if base and not include_history:
        files = (names(git(root, 'diff', '--name-only', '-z', '--no-renames', base))
                 | names(git(root, 'ls-files', '-z', '--others', '--exclude-standard')))
    if not commits_only:
        # A staged blob can differ from the working file a contributor sees.
        working.extend(scan_git_changes(root, git(root, 'diff', '--cached', *options), seen, 'index'))
        for name in sorted(files):
            path = root/name
            if not path.is_symlink() and not path.is_file():
                continue
            scanned += 1
            if path.is_symlink():
                items = check_bytes(name, b'', '120000')
            elif path.stat().st_size > 10*1024*1024:
                items = [{'path': name, 'reason': 'file exceeds the source-only size limit'}]
            else:
                items = check_bytes(name, b'' if excluded_reason(name) else path.read_bytes())
            working.extend(dict(item, scope='working_tree') for item in items)
    history = []
    revs = ['--all'] if include_history else [tip, '^' + base] if base else []
    if not revs and subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', '--quiet', tip],
                                   stdout=subprocess.DEVNULL).returncode == 0:
        # With no common main ref all commits leading to the tip may be outgoing.
        revs = [tip]
    if revs:
        for line in git(root, 'rev-list', '--parents', *revs).decode().splitlines():
            commit, *parents = line.split()
            before = parents[:1]
            delta = git(root, 'diff-tree', '--root', '--no-commit-id', '-r', *options, *before, commit)
            history.extend(dict(item, commit=commit) for item in scan_git_changes(root, delta, seen, 'commit'))
    return {'passed': not working and not history, 'source_files_scanned': scanned,
            'working_tree_findings': working, 'history_findings': history,
            'history_scanned': include_history, 'comparison_base': base,
            'scope': 'All reachable history and current files' if include_history else 'Contributor changes'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--history',action='store_true')
    parser.add_argument('--base', help='comparison base for introduced material (merge base of main by default)')
    parser.add_argument('--tip', default='HEAD', help='commit to check for a push')
    parser.add_argument('--commits-only', action='store_true', help='inspect outgoing commits only')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    base = args.base if args.base else default_base(args.root)
    report=inspect(args.root,args.history,base, args.tip, args.commits_only)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['history_findings','working_tree_findings']},indent=2))
    print(f'Working-tree findings: {len(report["working_tree_findings"])}; history findings: {len(report["history_findings"])}')
    for item in (report['working_tree_findings'] + report['history_findings'])[:20]:
        print(f'{item["path"]}: {item["reason"]}')
    return 0 if report['passed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
