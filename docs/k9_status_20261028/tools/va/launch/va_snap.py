"""Read-only snapshot for the Launch stage (J1 l_snap.py form): FRZ_K92 file count and digest outside the cache folders
(__pycache__, __tangentcache__, .pytest_cache, .git) and the cache file count, FREEZE.json sha256, frozen/ top entries,
FRZ_K8b FREEZE.json sha256, RVA top entries.  python -B va_snap.py <out.json>   (paths, counts, sha only)"""
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True
FRZ = r'D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833'
FRZ_K8B = r'D:\VISSIM-merge\frozen\sdmpc31_b9734abe_202610141821'
FROZEN = r'D:\VISSIM-merge\frozen'
RVA = r'D:\VISSIM_runs\20261023_sdmpc31_k92'
CACHE = ('__pycache__', '__tangentcache__', '.pytest_cache', '.git')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def main():
    out = sys.argv[1]
    dig = hashlib.sha256()
    n_main = n_cache = 0
    newest_main = 0.0
    freeze_mtime = os.path.getmtime(os.path.join(FRZ, 'FREEZE.json'))
    newer = []
    for root, dirs, files in os.walk(FRZ):
        dirs.sort()
        rel = os.path.relpath(root, FRZ)
        in_cache = any(part in CACHE for part in rel.split(os.sep))
        for fn in sorted(files):
            p = os.path.join(root, fn)
            if in_cache:
                n_cache += 1
                continue
            st = os.stat(p)
            n_main += 1
            r = os.path.relpath(p, FRZ).replace('\\', '/')
            dig.update(('%s|%d|%d\n' % (r, st.st_size, int(st.st_mtime))).encode('utf-8'))
            if st.st_mtime > freeze_mtime + 1 and fn != 'FREEZE.json':
                newer.append(r)
    res = {'frz': FRZ, 'files_outside_cache': n_main, 'digest_outside_cache_name_size_mtime': dig.hexdigest(),
           'cache_files': n_cache, 'files_newer_than_FREEZE_json': newer[:50], 'n_newer': len(newer),
           'freeze_json_sha256': sha(os.path.join(FRZ, 'FREEZE.json')),
           'frz_k8b_freeze_json_sha256': sha(os.path.join(FRZ_K8B, 'FREEZE.json')),
           'frozen_top': sorted(os.listdir(FROZEN)), 'rva_top': sorted(os.listdir(RVA))}
    res['frozen_top_count'] = len(res['frozen_top'])
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print('SNAP files_outside_cache=%d digest=%s cache=%d newer=%d freeze=%s k8b=%s frozen_top=%d rva_top=%s' % (
        n_main, res['digest_outside_cache_name_size_mtime'][:16], n_cache, len(newer), res['freeze_json_sha256'][:16],
        res['frz_k8b_freeze_json_sha256'][:16], res['frozen_top_count'], res['rva_top']))


if __name__ == '__main__':
    main()
