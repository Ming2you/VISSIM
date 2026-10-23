"""Export a compact, pinned runtime using the existing solo355 packaging policy.

No source deletion, native execution, freezer, optimizer, or prediction.
The canonical freezer still hashes the entire exported package.
"""
import hashlib, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SOURCE = Path('E:/VISSIM_workspaces/vsl349_causal_20261011')
DEST = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
CONFIG = 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
REL = 'diagnostics/sdmpc_n31_20260924/integration_20260926'
def lp(p):
    value=str(Path(p).resolve())
    return Path(value if value.startswith('\\\\?\\') else '\\\\?\\'+value)
read = lambda p: json.loads(lp(p).read_bytes())
def sha(path):
    h=hashlib.sha256()
    with lp(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    assert read(HERE/'full_selection_verification.json')['status']=='search_full_path_and_exact_selected_model_verified'
    resume='--resume-verified-copy' in sys.argv
    assert (not DEST.exists()) or (resume and not (DEST/'IMPORT_PROVENANCE.json').exists() and not (DEST/'.git').exists()), 'Preserve completed or claimed package'
    sys.path.insert(0,str(SOURCE/'diagnostics/sdmpc_n31_20260924/tools'))
    import freeze_manifest
    files=freeze_manifest.walk_files(SOURCE)
    chosen={}
    def add(name,reason):
        name=name.replace('\\','/')
        if name in files and name not in chosen:chosen[name]=reason
    for name,path in files.items():
        p=Path(name);lower=name.lower();size=os.path.getsize(path)
        if lower.startswith(('.review-','.git')):continue
        if p.suffix.lower() in {'.py','.ps1','.vbs'}:add(name,'source')
        elif lower.startswith(('evaluation/','vendor/','src/','plant/','config/','configs/')) and '/runs/' not in lower and size<2_000_000 and p.suffix.lower() in {'.json','.csv','.sig','.inpx','.npz','.npy','.pkl','.pickle','.yaml','.yml','.txt'}:
            add(name,'runtime_assets')
        elif size<250_000 and p.suffix.lower() in {'.json','.csv','.sig','.inpx'} and not any(s in lower for s in ('/decisions','/requests','/commands','/action_','/state_','/observation','/trace','/results','/evaluations','/unused','/step_','/bootstrap')):
            add(name,'small_input_assets')
        if name.startswith(REL+'/selected/'):add(name,'canonical_selected_inputs')
    for name in ('AGENTS.md','CLAUDE.md',CONFIG):add(name,'instructions_or_verified_config')
    seen=set();todo=[CONFIG]
    while todo:
        name=todo.pop()
        if name in seen:continue
        seen.add(name)
        if Path(name).suffix!='.json':continue
        def walk(v):
            if isinstance(v,dict):
                for x in v.values():walk(x)
            elif isinstance(v,list):
                for x in v:walk(x)
            elif isinstance(v,str):
                for candidate in (v.replace('\\','/'),(Path(name).parent/v).as_posix()):
                    if candidate in files:add(candidate,'config_dependency');todo.append(candidate);break
        walk(read(files[name]))
    total=sum(os.path.getsize(files[n]) for n in chosen)
    estimate=dict(source=str(SOURCE),destination=str(DEST),files=len(chosen),bytes=total,
        free_bytes=shutil.disk_usage('D:/').free,existing_policy=str(HERE.parent/'prepare_solo355_package.py'))
    print(json.dumps(estimate),flush=True)
    if '--install' not in sys.argv:return
    assert total<2_000_000_000 and estimate['free_bytes']>2*total+15_000_000_000
    before=freeze_manifest.git_state(SOURCE)
    DEST.mkdir(parents=True,exist_ok=resume)
    pins={}
    for name in sorted(chosen):
        src=Path(files[name]);dst=DEST/name;lp(dst.parent).mkdir(parents=True,exist_ok=True)
        digest=sha(src)
        if lp(dst).exists():
            assert resume and sha(dst)==digest,('Preserve changed partial export',name)
        else:shutil.copyfile(lp(src),lp(dst))
        assert sha(dst)==digest and sha(src)==digest,name
        pins[name]=digest
    assert freeze_manifest.git_state(SOURCE)==before,'Source Git state changed while exporting'
    for name,digest in pins.items():assert sha(files[name])==digest,name
    receipt=dict(schema='standalone-native-runtime-package/v1',source=str(SOURCE),upstream_git=before,
        imported_files=pins,selection=chosen,bytes=total,packaging_script_sha256=sha(__file__),
        policy='Existing solo355 compact export, applied to current development source. Canonical preflight and whole-package freeze remain mandatory.',
        historical_outputs_omitted=True,native_runs=0,source_unchanged=True)
    save(DEST/'IMPORT_PROVENANCE.json',receipt)
    for args in [('init',),('add','--','IMPORT_PROVENANCE.json'),('-c','user.name=Codex','-c','user.email=codex@local.invalid','commit','-m','Record adopted355 VSL experiment runtime import')]:
        subprocess.run(['git','-c','core.longpaths=true','-C',str(DEST),*args],check=True,capture_output=True)
    save(HERE/'native_package_receipt.json',dict(**estimate,status='exported_pending_preflight',
        provenance_sha256=sha(DEST/'IMPORT_PROVENANCE.json'),native_runs=0,freeze_count=0))
    print('PACKAGE_READY',DEST,flush=True)

if __name__=='__main__':main()
