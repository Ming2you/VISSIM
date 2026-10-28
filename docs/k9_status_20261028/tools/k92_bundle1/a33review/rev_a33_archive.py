"""ReviewDeclare A33: review-time listings of the archive (amendment 33 section 5), names / sizes / mtimes only (no file
content is opened).  Uses the pinned amendment-33 driver's archive_listing() for TK/vb_e27ceac8 + build record and the
same code form for OK2/vb (vbr_listing below), and the driver's archive_bytes().
    python -B rev_a33_archive.py   -> out/rev_a33_archive.json"""
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KV2 = HERE.parent / 'k92_vb2'
DRIVER_SHA = '87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


if sha(KV2 / 'vb_chain.py') != DRIVER_SHA:
    raise SystemExit('driver differs')
spec = importlib.util.spec_from_file_location('vb_chain_rev_arch', str(KV2 / 'vb_chain.py'))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


def vbr_listing():
    """Same code form as the driver's archive_listing(), root OK2/vb, no extra row."""
    rows = []
    root = D.L.lp(D.OLD_VBR)
    for base, dirs, names in os.walk(root):
        dirs.sort()
        rel_base = os.path.relpath(base, root).replace(chr(92), '/')
        for n in sorted(names):
            st = os.stat(os.path.join(base, n))
            rows.append([rel_base + '/' + n, st.st_size, round(st.st_mtime, 6)])
    return {'files': len(rows), 'sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
            'bytes': sum(r[1] for r in rows), 'newest_mtime': max(r[2] for r in rows)}


res = {'when': time.strftime('%Y-%m-%dT%H:%M:%S'), 'driver_sha256': DRIVER_SHA,
       'archive_tree_TK_vb_e27ceac8_plus_build': D.archive_listing(), 'old_vbr_OK2_vb': vbr_listing(),
       'archive_bytes': D.archive_bytes(),
       'vbr_exists': D.VBR.exists(), 'vbt_exists': D.VBT.exists()}
out = HERE / 'out' / 'rev_a33_archive.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(res, indent=1, sort_keys=True) + '\n', encoding='utf-8')
print('REV33ARCH tree=%s vbr=%s bytes_ok=%s sha=%s' % (res['archive_tree_TK_vb_e27ceac8_plus_build']['sha256'][:16],
      res['old_vbr_OK2_vb']['sha256'][:16], res['archive_bytes']['ok'], sha(out)))
