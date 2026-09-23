r"""Clone an existing prepared/ folder and repoint it to a new random seed.

Everything except the seed is preserved byte-for-byte. prepared.json and
fixed_profile.json carry SHA-256 pins that fast_nc_run.ps1 validates, so every pin whose
path lies inside the clone is recomputed; pins pointing outside are verified unchanged.
"""
import hashlib, json, re, shutil, sys
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main(src, dst, seed):
    src, dst, seed = Path(src), Path(dst), int(seed)
    if dst.exists(): raise FileExistsError(dst)
    shutil.copytree(src, dst)
    # 1) patch the network seed
    net = dst/'network/baseline.inpx'
    b = net.read_bytes()
    b2, n = re.subn(rb'(<simulation\b[^>]*\brandSeed=")[0-9]+', lambda m: m[1]+str(seed).encode(), b)
    if n != 1: raise ValueError(f'expected one randSeed attribute, found {n}')
    net.write_bytes(b2)
    newhash = sha(net)
    # 2) prepared.json
    pj = dst/'prepared.json'
    d = json.loads(pj.read_text(encoding='utf-8-sig'))
    d['seed'] = seed
    if isinstance(d.get('saved_simulation'), dict): d['saved_simulation']['randSeed'] = str(seed)
    d['network'] = str(net.resolve())
    fixed = outside = 0
    for key in ('snapshot_sha256','inputs'):
        if not isinstance(d.get(key), dict): continue
        out = {}
        for path, h in d[key].items():
            p = Path(path)
            try: rel = p.resolve().relative_to(src.resolve())
            except Exception:
                if p.exists() and sha(p) != h: raise ValueError(f'external pin already stale: {path}')
                out[path] = h; outside += 1; continue
            q = (dst/rel).resolve()
            out[str(q)] = sha(q); fixed += 1
    # rewrite must happen after the loop so json stays consistent
        d[key] = out
    pj.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8')
    # 3) native_simulation.csv — fast_nc_runner.vbs compares this row-by-row against the
    #    loaded network and dies with "Saved simulation differs: RandSeed" if it disagrees.
    csvp = dst/'native_simulation.csv'
    if csvp.exists():
        import re as _re
        t = csvp.read_text(encoding='utf-8-sig')
        t2 = _re.sub(r'(?mi)^(RandSeed,)\s*\d+\s*$', lambda m: m.group(1)+str(seed), t)
        if t2 == t: raise ValueError('native_simulation.csv has no RandSeed row')
        csvp.write_text(t2, encoding='utf-8')
    # 4) fixed_profile.json (if present)
    fp = dst/'fixed_profile.json'
    if fp.exists():
        f = json.loads(fp.read_text(encoding='utf-8-sig'))
        f['seed'] = seed
        if 'network_sha256' in f: f['network_sha256'] = newhash
        fp.write_text(json.dumps(f, indent=2, ensure_ascii=False), encoding='utf-8')
    # 5) prepared.json pins itself? recompute any pin that now points at the files we rewrote
    d = json.loads(pj.read_text(encoding='utf-8-sig'))
    for key in ('snapshot_sha256','inputs'):
        if isinstance(d.get(key), dict):
            for path in list(d[key]):
                p = Path(path)
                if p.exists() and str(dst.resolve()) in str(p.resolve()): d[key][path] = sha(p)
    pj.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'  {dst.name}: seed={seed} network_sha={newhash[:16]} 재계산핀={fixed} 외부핀={outside}')

if __name__ == '__main__':
    main(*sys.argv[1:4])
