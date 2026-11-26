import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest

TOOLS=Path(__file__).resolve().parents[2]/'tools'
sys.path.insert(0,str(TOOLS))
from check_publish import excluded_reason,inspect
from export_source import export_source


def run_git(root,*args):
    subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True)


def test_local_environment_and_models_are_excluded_but_examples_are_source():
    assert excluded_reason('.env.local')
    assert excluded_reason('models/smpl/SMPL_NEUTRAL.pkl')
    assert excluded_reason('outputs/V1.1.1/manifest.json')
    assert excluded_reason('.env.example') is None
    assert excluded_reason('outputs/README.md') is None


def test_removing_an_asset_from_index_does_not_clear_history(tmp_path):
    run_git(tmp_path,'init','-b','test')
    run_git(tmp_path,'config','user.name','Local Test')
    run_git(tmp_path,'config','user.email','local@example.invalid')
    (tmp_path/'old.obj').write_text('v 0 0 0\n')
    run_git(tmp_path,'add','old.obj')
    run_git(tmp_path,'commit','-m','test fixture')
    run_git(tmp_path,'rm','old.obj')
    run_git(tmp_path,'commit','-m','remove fixture')
    report=inspect(tmp_path,include_history=True)
    assert report['working_tree_findings']==[]
    assert any(item['path']=='old.obj' for item in report['history_findings'])
    assert not report['passed']


def test_export_omits_private_data_and_old_git_history(tmp_path):
    original=tmp_path/'original'
    original.mkdir()
    run_git(original,'init','-b','test')
    (original/'main.py').write_text('print(42)\n')
    (original/'.env.local').write_text('PRIVATE_SETTING=local\n')
    (original/'model.pkl').write_bytes(b'not-a-model')
    destination=tmp_path/'source-only'
    export_source(original,destination)
    assert (destination/'main.py').is_file()
    assert not (destination/'.env.local').exists()
    assert not (destination/'model.pkl').exists()
    assert not (destination/'.git').exists()
    with pytest.raises(ValueError):export_source(original,destination)


def test_contributor_scope_includes_staged_and_intermediate_blobs(tmp_path):
    run_git(tmp_path, 'init', '-b', 'main')
    run_git(tmp_path, 'config', 'user.name', 'Local Test')
    run_git(tmp_path, 'config', 'user.email', 'local@example.invalid')
    (tmp_path/'old.mp4').write_bytes(b'old synthetic fixture')
    run_git(tmp_path, 'add', 'old.mp4')
    run_git(tmp_path, 'commit', '-m', 'baseline')
    base = subprocess.check_output(['git', '-C', str(tmp_path), 'rev-parse', 'HEAD'], text=True).strip()
    assert inspect(tmp_path, base=base)['passed']
    (tmp_path/'new.mp4').write_bytes(b'dummy')
    run_git(tmp_path,'add','new.mp4')
    run_git(tmp_path,'commit','-m','new media')
    run_git(tmp_path,'rm','new.mp4')
    run_git(tmp_path,'commit','-m','remove media')
    (tmp_path/'notes').write_text('ghp_' + 'X'*32)
    run_git(tmp_path,'add','notes')
    (tmp_path/'notes').write_text('redacted in working tree')
    result=inspect(tmp_path,base=base)
    assert any(x['scope']=='index' and x['reason']=='GitHub token' for x in result['working_tree_findings'])
    assert {x['path'] for x in result['history_findings']} == {'new.mp4'}


def test_missing_main_base_still_checks_intermediate_commits(tmp_path):
    from check_publish import default_base
    run_git(tmp_path, "init", "-b", "feature")
    run_git(tmp_path, "config", "user.name", "Local Test")
    run_git(tmp_path, "config", "user.email", "local@example.invalid")
    (tmp_path / "capture.mp4").write_bytes(b"synthetic fixture")
    run_git(tmp_path, "add", "capture.mp4")
    run_git(tmp_path, "commit", "-m", "fixture")
    run_git(tmp_path, "rm", "capture.mp4")
    run_git(tmp_path, "commit", "-m", "remove fixture")
    result = inspect(tmp_path, base=default_base(tmp_path))
    assert [row["path"] for row in result["history_findings"]] == ["capture.mp4"]
    assert not result["passed"]
