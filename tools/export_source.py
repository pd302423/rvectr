#!/usr/bin/env python3
"""Export reviewed source without original Git history or private assets.

The original repository is never edited. A nonempty destination is refused.
No repository is created, committed or pushed automatically by this exporter.
"""
import argparse
import json
from pathlib import Path
import shutil
from check_publish import source_candidates,excluded_reason,SECRET_PATTERNS,source_icon


def export_source(root,destination):
    root,destination=Path(root).resolve(),Path(destination).expanduser().resolve()
    if destination==root or root in destination.parents:
        raise ValueError('Destination must be outside the original repository')
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Destination is nonempty; refusing to replace existing work')
    selected,excluded=[],[]
    for name in source_candidates(root):
        path=root/name
        if not path.is_file():continue
        reason=excluded_reason(name)
        if path.is_symlink():reason='symlink'
        if path.stat().st_size>10*1024*1024:reason='large binary/artifact'
        if reason:
            excluded.append({'path':name,'reason':reason})
            continue
        if source_icon(path):
            selected.append(name)
            continue
        try: content=path.read_text(encoding='utf-8-sig')
        except UnicodeError as error:
            raise ValueError(f'Non-UTF8 candidate requires review: {name}') from error
        if any(pattern.search(content) for pattern in SECRET_PATTERNS.values()):
            raise ValueError(f'Potential credential in {name}; export stopped without printing its value')
        selected.append(name)
    destination.mkdir(parents=True,exist_ok=True)
    for name in selected:
        source,target=root/name,destination/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if source_icon(source):
            shutil.copy2(source,target)
            continue
        # Normalize declared text source to LF for Linux. Windows wrappers keep CRLF.
        content=source.read_text(encoding='utf-8').replace('\r\n','\n')
        with target.open('w',encoding='utf-8',newline='\r\n' if target.suffix=='.ps1' else '\n') as stream:
            stream.write(content)
        if target.suffix=='.sh' or '.githooks' in target.parts:target.chmod(0o755)
    print(json.dumps({'destination':str(destination),'files':len(selected),
                      'excluded':excluded,'git_history_copied':False},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    export_source(args.root,args.destination)
