"""Curate this dated handoff only; does not stage files or operate VISSIM."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
D = ROOT / 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'

def git_paths(*args):
    return set(filter(None, subprocess.check_output(['git', *args, '-z'], cwd=ROOT).decode('utf-8').split('\0')))

def main():
    selected = git_paths('diff', 'HEAD', '--name-only')
    required = json.loads((HERE / 'required_runtime_paths.json').read_text(encoding='utf-8-sig'))
    selected.update(r['path'] for r in required['files'])
    tracked = git_paths('ls-tree', '-r', '--name-only', 'HEAD')
    def add(p):
        if p.is_file():
            selected.add(p.relative_to(ROOT).as_posix())
    # Preserve diagnostics, without installing abandoned replacement modules.
    for p in (ROOT / 'diagnostics').iterdir():
        if p.suffix in ('.py', '.ps1', '.vbs', '.md'):
            if any(s in p.stem for s in ('proposal', 'candidate', '_patch')):
                continue
            add(p)
    for base in [D, ROOT/'diagnostics/com_execution_equivalence', ROOT/'reports/20260911_decision_runtime',
                 ROOT/'reports/20260911_cooldown_80_90', ROOT/'reports/20260911_fd_fw070_080_090',
                 ROOT/'reports/20260911_fd_mfd_fw070_urban050',
                 ROOT/'diagnostics/fixed_beta300v3_network_arms_flat_v1']:
        if base.exists():
            for p in base.iterdir():
                if p.suffix.lower() in ('.py','.ps1','.vbs','.json','.csv','.md','.txt','.png','.svg','.pdf'):
                    if p.is_file() and p.stat().st_size <= 12*1024*1024:
                        add(p)
    for name in ['fidelity_bounded_recorded900_v1','fidelity_bounded_recorded900_v2',
                 'fidelity_cl2400_2850_v1','fidelity_nc2400_2850_v1','fidelity_nc9000_s13_full_v1',
                 'fidelity_recorded3150_missed_target_v1','fidelity_recorded6300_context_v1',
                 'fidelity_recorded6300_scope_fix_v1','guard6300_scope_regression_fixed_v1',
                 'guard6300_scope_regression_v1']:
        base=D/name
        if base.exists():
            for p in base.iterdir():
                if p.suffix in ('.json','.csv','.md','.txt') and p.is_file() and p.stat().st_size <= 12*1024*1024:
                    add(p)
    for name in ['meter_open_service_bound_review_v1.md','meter_plateau_scope_review_v1.md']:
        add(D.parent/name)
    add(ROOT/'diagnostics/shared_owner_copy_optimization_v1/baseline_functions.zip')
    for case in ('fw070_urban030','fw070_urban040'):
        base=ROOT/'diagnostics/demand_sweep'/case
        add(base/'input_override.csv')
        for name in ('prepared.json','demand.csv'):
            add(base/'prepared'/name)
    for p in HERE.rglob('*'):
        if p.suffix in ('.py','.json','.csv','.md') and p.name not in ('transfer_manifest.json','plan_check.json'):
            add(p)
    add(ROOT/'docs/HANDOFF_20260913_controller_runtime.md')
    # Local Python import closure also retains explicitly imported old test fixtures.
    pending=[s for s in selected if s.endswith('.py')]; seen=set()
    while pending:
        rel=pending.pop()
        if rel in seen:
            continue
        seen.add(rel)
        try:
            tree=ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
        except (UnicodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            names=[]
            if isinstance(node, ast.Import):
                names=[a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level==0 and node.module:
                names=[node.module]+[node.module+'.'+a.name for a in node.names if a.name!='*']
            for name in names:
                module=Path(*name.split('.'))
                for p in (ROOT/module.with_suffix('.py'), ROOT/module/'__init__.py'):
                    if p.is_file() and p.relative_to(ROOT).as_posix() not in selected:
                        add(p); pending.append(p.relative_to(ROOT).as_posix())
    selected.discard('diagnostics/handoff_20260913/transfer_manifest.json')
    missing=[s for s in selected if not (ROOT/s).is_file()]
    assert not missing, missing
    assert not any((ROOT/s).stat().st_size >= 100*1024*1024 for s in selected)
    assert not any(s.endswith(('.fzp','.pickle','.pstats','.pyc')) or '/node_modules/' in s or '/.plot-deps/' in s for s in selected)
    # Source hash declarations must survive Windows checkout byte-for-byte.
    attrs=ROOT/'.gitattributes'
    marker='# 2026-09-13 handoff byte-preserved sources and evidence'
    old=attrs.read_text(encoding='utf-8-sig').split(marker)[0].rstrip()
    preserve=sorted(selected | {'diagnostics/handoff_20260913/transfer_manifest.json'})
    rules=[]
    for s in preserve:
        p=ROOT/s
        data=p.read_bytes() if p.is_file() else b''
        try:
            data.decode('utf-8-sig')
            crlf=bool(b'\r\n' in data and b'\n' not in data.replace(b'\r\n',b''))
        except UnicodeError:
            crlf=False
        # Preserve checkout bytes while keeping existing normalized Git blobs.
        mode='text eol=crlf' if crlf else '-text'
        rules.append('"'+s+'" '+mode+' '+('-whitespace' if s.endswith('.svg') else 'whitespace=cr-at-eol'))
    attrs.write_text(old+'\n\n'+marker+'\n'+'\n'.join(rules)+'\n',encoding='utf-8')
    records=[]
    for s in sorted(selected):
        p=ROOT/s
        records.append({'path':s,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'previously_tracked':s in tracked})
    manifest={'schema':'curated-git-handoff/v1','branch':'codex/control-full-review-20260909',
              'scope':'Explicit code, selected runtime inputs and small historical evidence; no complete native run transfer.',
              'self_exclusion':'This manifest is staged but excludes its own hash to avoid a circular digest.',
              'runtime_manifest':'diagnostics/handoff_20260913/required_runtime_paths.json',
              'files':records,'count':len(records),'bytes':sum(r['bytes'] for r in records)}
    (HERE/'transfer_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    selected.add('diagnostics/handoff_20260913/transfer_manifest.json')
    (HERE/'stage_paths.nul').write_bytes(b'\0'.join(s.encode('utf-8') for s in sorted(selected))+b'\0')
    forced=[s for s in sorted(selected) if s.startswith('evaluation/runs/')]
    assert len(forced)==1 and forced[0].endswith('/action_000001.csv')
    (HERE/'stage_paths_forced.nul').write_bytes(b'\0'.join(s.encode('utf-8') for s in forced)+b'\0')
    (HERE/'stage_paths_regular.nul').write_bytes(b'\0'.join(s.encode('utf-8') for s in sorted(selected) if s not in forced)+b'\0')
    print(json.dumps({'files':len(selected),'bytes':manifest['bytes'],'new':sum(not r['previously_tracked'] for r in records),
                     'largest':sorted(records,key=lambda r:r['bytes'],reverse=True)[:8]},ensure_ascii=False))

if __name__=='__main__':
    main()
