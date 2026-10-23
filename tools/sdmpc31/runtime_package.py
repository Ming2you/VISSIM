"""Explicit runtime inputs and immutable shared objects; never copy a whole worktree.

prepare --source W --config relative/config.json [--include relative/path] --out inputs.json
freeze --source W --inputs inputs.json --frozen FRZ --store E:/VISSIM_shared
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import xml.etree.ElementTree as ET

CODE = {'.py', '.ps1', '.vbs'}
DATA = {'.json', '.csv', '.sig', '.inpx', '.npz', '.npy', '.pkl', '.pickle', '.yaml', '.yml', '.txt'}
SKIP = {'.git', '.deps', '.review-deps', '__pycache__', '.pytest_cache', '__tangentcache__', '_archive'}
OUTPUT_DIRS = {'runs', 'results', 'decisions', 'requests', 'evaluations', 'observations'}
CANONICAL = 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/'
SHARED_LINK_LIMIT = 900  # Leave headroom below NTFS's 1024 links per file.

def lp(p):
    text = os.path.abspath(p)
    return text if os.name != 'nt' or text.startswith('\\\\?\\') else '\\\\?\\' + text

def digest(p):
    h = hashlib.sha256()
    with open(lp(p), 'rb') as f:
        while b := f.read(4 * 1024 * 1024): h.update(b)
    return h.hexdigest()

def read(p):
    with open(lp(p), encoding='utf-8-sig') as f: return json.load(f)

def save(p, data):
    Path(lp(Path(p).parent)).mkdir(parents=True, exist_ok=True)
    with open(lp(p), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

def no_reparse(p):
    for candidate in [Path(p).absolute(), *Path(p).absolute().parents]:
        if os.path.exists(lp(candidate)) and getattr(os.stat(lp(candidate),follow_symlinks=False),'st_file_attributes',0)&0x400:
            raise ValueError('Reparse storage path refused: '+str(candidate))

def safe_input(root, rel):
    q = Path(rel)
    if q.is_absolute() or '..' in q.parts:
        raise ValueError('Input must be source-relative: ' + str(rel))
    p = root / q
    for parent in [p, *p.parents]:
        if parent == root.parent: break
        if os.path.exists(lp(parent)) and getattr(os.stat(lp(parent), follow_symlinks=False), 'st_file_attributes', 0) & 0x400:
            raise ValueError('Reparse input refused: ' + str(p))
    return p

def files(root):
    for folder, dirs, names in os.walk(lp(root)):
        dirs[:] = sorted(d for d in dirs if d.lower() not in SKIP
                         and not getattr(os.stat(os.path.join(folder,d),follow_symlinks=False),'st_file_attributes',0)&0x400)
        for name in sorted(names):
            p = Path(folder, name)
            yield Path(os.path.relpath(p,lp(root))).as_posix(), p

def prepare(source, configs, includes, output):
    root = Path(source).resolve()
    selected = {}
    def add(rel, reason):
        p = safe_input(root,rel)
        if not os.path.isfile(lp(p)): raise FileNotFoundError(str(p))
        selected[Path(rel).as_posix()] = reason
    for rel, p in files(root):
        lower=rel.lower(); parts=set(Path(lower).parts); size=os.stat(lp(p)).st_size
        if parts & OUTPUT_DIRS: continue
        if p.suffix.lower() in CODE: add(rel,'source_code')
        elif lower.startswith(('evaluation/','vendor/','src/','plant/','config/','configs/')) and size<2_000_000 and p.suffix.lower() in DATA:
            add(rel,'runtime_data')
        elif lower.startswith(CANONICAL) and p.suffix.lower() in DATA:
            add(rel,'canonical_inputs')
    for rel in includes:
        p=safe_input(root,rel)
        if os.path.isdir(lp(p)):
            for sub,_ in files(p): add((Path(rel)/sub).as_posix(),'explicit_input_directory')
        else: add(rel,'explicit_input')
    queue=list(configs); seen=set(); external={}
    while queue:
        rel=Path(queue.pop()).as_posix()
        if rel in seen: continue
        add(rel,'config_dependency'); seen.add(rel)
        if Path(rel).suffix.lower()!='.json': continue
        def walk(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    # Hash maps pin local command/source paths in their keys.
                    if isinstance(key,str): walk(key)
                    walk(item)
            elif isinstance(value,list):
                for item in value: walk(item)
            elif isinstance(value,str) and len(value)<4096:
                text=value.replace('\\','/')
                candidates=[]
                if Path(text).is_absolute():
                    try: candidates.append(Path(text).relative_to(root).as_posix())
                    except ValueError:
                        if os.path.isfile(lp(text)):
                            external[text]={'sha256':digest(text),'bytes':os.stat(lp(text)).st_size}
                else: candidates=[text,(Path(rel).parent/text).as_posix()]
                for item in candidates:
                    try:
                        item=(root/item).resolve().relative_to(root).as_posix()
                        p=safe_input(root,item)
                    except (ValueError,OSError): continue
                    if os.path.isfile(lp(p)):
                        add(item,'config_dependency'); queue.append(item); break
        walk(read(root/rel))
    if not configs: raise ValueError('At least one actual configuration or protocol is required.')
    missing_backgrounds=[]
    for rel in list(selected):
        if Path(rel).suffix.lower()!='.inpx': continue
        for element in ET.parse(lp(root/rel)).iter():
            if element.tag not in {'backgroundImage','signalController'}: continue
            for value in element.attrib.values():
                if Path(value).suffix.lower() not in {'.sig','.jpg','.jpeg','.png','.bmp'}: continue
                filename=value.removeprefix('#data#').replace('\\','/')
                candidates=[root/Path(rel).parent/filename,root/'network'/filename]
                matched=False
                for candidate in candidates:
                    try: relative=candidate.resolve().relative_to(root).as_posix()
                    except ValueError: continue
                    if os.path.isfile(lp(candidate)):
                        add(relative,'network_asset');matched=True;break
                if not matched and element.tag=='backgroundImage':
                    missing_backgrounds.append({'network':rel,'original_reference':value})
    table={rel:digest(root/rel) for rel in sorted(selected)}
    result={'schema':'vissim-runtime-inputs/v1','source':str(root),'configs':configs,'files':table,
            'selection':selected,'external_inputs':external,'preexisting_unresolved_backgrounds':missing_backgrounds,
            'bytes':sum(os.stat(lp(root/r)).st_size for r in table),
            'policy':'Only code, bounded runtime data and explicit dependencies. Historical outputs and handoff evidence are not copied implicitly.'}
    save(output,result)
    return result

def git_state(root):
    def git(*args):
        return subprocess.run(['git','-c','safe.directory='+str(root),'-C',str(root),*args],check=True,capture_output=True).stdout
    porcelain=git('status','--porcelain=v1','--untracked-files=all','-z')
    return dict(head=git('rev-parse','--verify','HEAD^{commit}').decode().strip(),
                branch=git('rev-parse','--abbrev-ref','HEAD').decode().strip(),
                status_sha256=hashlib.sha256(porcelain).hexdigest(),
                status_entries=len([s for s in porcelain.split(b'\0') if s]),
                status_command='git status --porcelain=v1 --untracked-files=all -z')

def put_object(source, object_path, expected):
    base=Path(object_path);obj=base;src=Path(source);shard=0
    while True:
        no_reparse(obj)
        if not os.path.exists(lp(obj)) or os.stat(lp(obj)).st_nlink < SHARED_LINK_LIMIT:
            break
        shard+=1
        obj=base.parent/'shards'/f'{shard:03d}'/base.name
    Path(lp(obj.parent)).mkdir(parents=True,exist_ok=True)
    if not os.path.exists(lp(obj)):
        temp=Path(str(obj)+'.partial')
        if os.path.exists(lp(temp)): raise FileExistsError('Preserve interrupted object: '+str(temp))
        shutil.copyfile(lp(src),lp(temp))
        if digest(temp)!=expected: raise ValueError('Source changed during object copy: '+str(src))
        os.replace(lp(temp),lp(obj))
    elif digest(obj)!=expected: raise ValueError('Corrupt shared object: '+str(obj))
    os.chmod(lp(obj),stat.S_IREAD)
    return obj

def freeze(source, inputs, frozen, store):
    for p in (source,frozen,store):no_reparse(p)
    root=Path(source).resolve(); frz=Path(frozen).resolve(); store=Path(store).resolve()
    if frz.drive.lower()!=store.drive.lower(): raise ValueError('Shared store and launch tree must be on the same volume.')
    if frz==root or root in frz.parents: raise ValueError('Launch tree must be outside the source worktree.')
    if os.path.exists(lp(frz)): raise FileExistsError('Launch tree already exists; preserve it.')
    spec=read(inputs)
    if spec.get('schema')!='vissim-runtime-inputs/v1' or Path(spec['source']).resolve()!=root:
        raise ValueError('Input specification belongs to another source.')
    before=git_state(root)
    for path,pin in spec['external_inputs'].items():
        if digest(path)!=pin['sha256']: raise ValueError('External pinned input changed: '+path)
    for rel,pin in spec['files'].items():
        if not re.fullmatch('[0-9a-f]{64}',pin) or digest(safe_input(root,rel))!=pin:
            raise ValueError('Input changed after selection: '+rel)
    Path(lp(frz)).mkdir(parents=True)
    for rel,pin in spec['files'].items():
        src=safe_input(root,rel); dst=frz/rel
        obj=put_object(src,store/'objects'/'sha256'/pin[:2]/pin,pin)
        Path(lp(dst.parent)).mkdir(parents=True,exist_ok=True)
        os.link(lp(obj),lp(dst))
        if not os.path.samefile(lp(obj),lp(dst)): raise RuntimeError('Shared input link mismatch')
    save(frz/'RUNTIME_INPUTS.json',spec)
    table=dict(spec['files']); table['RUNTIME_INPUTS.json']=digest(frz/'RUNTIME_INPUTS.json')
    for rel,pin in spec['files'].items():
        if digest(root/rel)!=pin: raise ValueError('Source changed during freeze: '+rel)
    if git_state(root)!=before: raise ValueError('Git state changed during freeze.')
    document={'schema':'sdmpc31-freeze/v1','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source':str(root),'frozen':str(frz),'git':before,'files':table,
              'file_count':len(table),'total_bytes':sum(os.stat(lp(frz/r)).st_size for r in table),
              'tree_sha256':hashlib.sha256(json.dumps(table,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
              'storage':{'schema':'vissim-shared-runtime/v1','object_store':str(store),'input_manifest_sha256':digest(inputs),
                         'mutable_results':'Use a separate ResultsRoot. Do not modify shared launch inputs.'}}
    save(frz/'FREEZE.json',document)
    return document

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare'); p.add_argument('--source',required=True);p.add_argument('--config',action='append',required=True)
    p.add_argument('--include',action='append',default=[]);p.add_argument('--out',required=True)
    p=sub.add_parser('freeze');p.add_argument('--source',required=True);p.add_argument('--inputs',required=True)
    p.add_argument('--frozen',required=True);p.add_argument('--store',required=True)
    args=parser.parse_args()
    if args.command=='prepare':
        r=prepare(args.source,args.config,args.include,args.out)
        print(json.dumps({'files':len(r['files']),'bytes':r['bytes'],'external_inputs':len(r['external_inputs'])}))
    else:
        r=freeze(args.source,args.inputs,args.frozen,args.store)
        print('FREEZE_DONE files='+str(r['file_count'])+' bytes='+str(r['total_bytes']))
        print('FRZ='+r['frozen'])

if __name__=='__main__': main()
