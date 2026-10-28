"""ReviewDeclare A31: byte manifest of the J-b capture root CAP = OK2/k92t/jb/sa/cap/k92t (read by the 4c captured
test in both jb_unit and the amendment-31 base run), made BEFORE any amendment-31 data, so that the independent
verification (amendment 31 section 4.3 V4) can show the base run left CAP unchanged.  Metadata and byte sha256 only;
no file content is parsed or printed.  Output: RV31/out/cap_manifest.json ({rel path: [size, sha256]}, counts, the
sha256 of the canonical listing).  stdout: counts only.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'cap_manifest.json'
CAP = r'D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1\k92t\jb\sa\cap\k92t'


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    t0 = time.time()
    root = '\\\\?\\' + CAP
    files = {}
    for base, dirs, names in os.walk(root):
        dirs.sort()
        for n in sorted(names):
            full = os.path.join(base, n)
            rel = os.path.relpath(full, root).replace('\\', '/')
            files[rel] = [os.path.getsize(full), sha_file(full)]
    listing = '\n'.join('%s\t%d\t%s' % (k, v[0], v[1]) for k, v in sorted(files.items())) + '\n'
    rec = {'schema': 'rv31-cap-manifest/v1', 'cap': CAP, 'when': time.strftime('%Y-%m-%dT%H:%M:%S'),
           'n_files': len(files), 'n_bytes': sum(v[0] for v in files.values()),
           'listing_sha256': hashlib.sha256(listing.encode('utf-8')).hexdigest(),
           'listing_rule': "sorted '<rel path>\\t<size>\\t<sha256>\\n' lines, utf-8", 'files': files,
           'sec': round(time.time() - t0, 1)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(OUT) + '.tmp')
    tmp.write_text(json.dumps(rec, indent=0, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, OUT)
    print('RV31_CAPMAN n_files=%d n_bytes=%d listing_sha256=%s sec=%s' % (
        rec['n_files'], rec['n_bytes'], rec['listing_sha256'], rec['sec']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
