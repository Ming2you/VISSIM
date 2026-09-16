"""Build the explicit 2026-09-16 transfer package; never stage or run VISSIM."""
from pathlib import Path
import ast,collections,hashlib,json,os,subprocess,zipfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
B=ROOT/'diagnostics/demand_sweep/user_native_20260914'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def gitpaths(*args):
    return set(filter(None,subprocess.check_output(['git',*args,'-z'],cwd=ROOT).decode('utf-8').split(chr(0))))
def main():
    if (HERE/'evidence_manifest.json').exists():raise FileExistsError('Preserve existing package')
    eligible=set();excluded=[]
    skipped={'.fzp','.db','.knr','.rsr','.pstats','.pyc','.pickle'}
    def walk(base):
        for dp,dirs,files in os.walk(base):
            dirs[:]=[d for d in dirs if d not in ('.plot-deps','.mplconfig','__pycache__')]
            for name in files:
                p=Path(dp)/name;rel=p.relative_to(ROOT).as_posix()
                if p.suffix.lower() in skipped:
                    excluded.append({'path':rel,'bytes':p.stat().st_size,'reason':'Raw trajectory/native result database or transient cache; retained on original workstation'})
                else:eligible.add(rel)
    walk(B)
    walk(ROOT/'diagnostics/rule_baseline_20260914')
    for base in sorted((ROOT/'diagnostics/selected_control_demand').glob('rule100*')):
        if not base.is_dir():continue
        for p in base.iterdir():
            if p.is_file():eligible.add(p.relative_to(ROOT).as_posix())
        native=base/'native_recording'
        if native.exists():
            for p in native.iterdir():
                if p.is_file() and p.suffix.lower() in ('.inpx','.sig','.jpg','.png','.layx','.json'):
                    eligible.add(p.relative_to(ROOT).as_posix())
    tracked=gitpaths('ls-files')
    direct=gitpaths('diff','HEAD','--name-only')
    for name in ['evaluation/controllers/freeway_geometry.py','evaluation/controllers/physical_ramp_boundary.py',
        'diagnostics/fast_fixed_profile.py','diagnostics/fast_fixed_profile_verify.py',
        'diagnostics/test_fast_fixed_profile.py','diagnostics/plant_balanced_ramp_sweep.py',
        'diagnostics/test_rule_detector_provenance.py','tests/test_diagnostic_rule_profile.py',
        'docs/HANDOFF_20260916_geometry_actuator_response.md','AGENTS.md','.gitattributes']:
        if (ROOT/name).is_file():direct.add(name)
    for rel in eligible:
        p=ROOT/rel
        if p.suffix.lower() in ('.py','.ps1','.vbs','.md') or (p.suffix.lower() in ('.png','.pdf') and p.stat().st_size<8*1024*1024):
            direct.add(rel)
    direct.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.suffix in ('.py','.md','.txt'))
    # Retain newly imported local helpers. Already tracked imports are on the branch.
    pending=list(direct);seen=set()
    while pending:
        rel=pending.pop()
        if rel in seen or not rel.endswith('.py'):continue
        seen.add(rel)
        try:tree=ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
        except (UnicodeError,SyntaxError):continue
        for node in ast.walk(tree):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.level==0 and node.module else [])
            for name in names:
                m=Path(*name.split('.'))
                for p in (ROOT/m.with_suffix('.py'),ROOT/m/'__init__.py',(ROOT/rel).parent/m.with_suffix('.py')):
                    if p.is_file():
                        r=p.relative_to(ROOT).as_posix()
                        if r not in tracked and r not in direct:direct.add(r);pending.append(r)
    artifact=sorted(eligible-direct-tracked)
    records=[];objects={}
    for rel in artifact:
        p=ROOT/rel;h=sha(p)
        records.append({'path':rel,'bytes':p.stat().st_size,'sha256':h})
        objects.setdefault(h,p)
    archive=HERE/'evidence.build.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for h,p in sorted(objects.items()):z.write(p,'objects/'+h)
    parts=[]
    with archive.open('rb') as f:
        while True:
            data=f.read(48*1024*1024)
            if not data:break
            name=f'evidence.part{len(parts)+1:03d}'
            (HERE/name).write_bytes(data)
            parts.append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    manifest={'schema':'deduplicated-git-handoff/v1','branch':'codex/control-full-review-20260909',
        'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'scope':'All non-raw evidence in current user-native and rule-baseline diagnostics, frozen outputs, exact network/signal assets; original receipts are immutable historical provenance',
        'files':records,'parts':parts,'unique_objects':len(objects),'uncompressed_bytes':sum(r['bytes'] for r in records),
        'archive_bytes':archive.stat().st_size,
        'excluded_raw':excluded,
        'excluded_scope_note':'Does not sweep unrelated historical diagnostics or raw selected-control run trees. All local files remain untouched.'}
    (HERE/'evidence_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    # This temporary archive is owned by this invocation; persistent checksummed
    # parts are the published copy. Never remove simulation or user files.
    if archive.resolve().parent != HERE.resolve():raise ValueError('Archive target escaped handoff directory')
    archive.unlink()
    direct.update({(HERE/'evidence_manifest.json').relative_to(ROOT).as_posix()})
    direct.update((HERE/r['name']).relative_to(ROOT).as_posix() for r in parts)
    direct.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.suffix in ('.py','.md','.txt'))
    direct.add('diagnostics/handoff_20260916/git_paths.txt')
    direct.add('diagnostics/handoff_20260916/direct_files.json')
    attrs=ROOT/'.gitattributes';marker='# 2026-09-16 handoff byte preservation'
    old=attrs.read_text(encoding='utf-8-sig').split(marker)[0].rstrip();rules=[]
    for rel in sorted(direct):
        p=ROOT/rel;data=p.read_bytes() if p.is_file() else b''
        crlf=b'\r\n' in data and b'\n' not in data.replace(b'\r\n',b'')
        mode='text eol=crlf' if crlf else '-text'
        rules.append('"'+rel+'" '+mode+' whitespace=cr-at-eol')
    attrs.write_text(old+'\n\n'+marker+'\n'+'\n'.join(rules)+'\n',encoding='utf-8')
    (HERE/'git_paths.txt').write_text('\n'.join(sorted(direct))+'\n',encoding='utf-8')
    data=[{'path':r,'bytes':(ROOT/r).stat().st_size,'sha256':sha(ROOT/r)} for r in sorted(direct) if r!='diagnostics/handoff_20260916/direct_files.json']
    (HERE/'direct_files.json').write_text(json.dumps({'files':data},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'direct_files':len(direct),'artifact_files':len(records),'unique_objects':len(objects),
        'archive_mb':manifest['archive_bytes']/1024**2,'parts':len(parts),
        'excluded_raw_gb':sum(r['bytes'] for r in excluded)/1024**3}))
if __name__=='__main__':main()
