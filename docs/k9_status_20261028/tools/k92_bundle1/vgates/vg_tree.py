"""VerifyGates: the k92t tree TK/a27/k92t against the commit K9-2-5 e27ceac8 (own code; git plumbing only).
Every path of `git ls-tree -r e27ceac8` must exist in the tree and every tree file (caches excluded: __pycache__,
*.pyc, .pytest_cache, .numba cache *.nbi/*.nbc) must be a committed path; per file: bytes equal to the blob, or equal
after CRLF -> LF (the archive's text conversion), else different.  Also the judge-blob list OUT29/k925_blobs.json
(19 blobs) and the stage records (k92t_judging_stage.json, stages/prep.json arm sha, tree build record).

    python -B vg_tree.py --dest <json>
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402

GWT8 = r'D:/VISSIM-merge/sim3-n31-k8'
REV = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t')
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
CACHE_DIRS = {'__pycache__', '.pytest_cache'}
CACHE_EXT = ('.pyc', '.nbi', '.nbc')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    ls = subprocess.run(['git', '--no-optional-locks', '-C', GWT8, 'ls-tree', '-r', '-z', REV], capture_output=True).stdout
    blobs = {}
    for ent in ls.split(b'\0'):
        if not ent:
            continue
        meta, path = ent.split(b'\t', 1)
        mode, typ, sha = meta.split()
        if typ == b'blob':
            blobs[path.decode('utf-8')] = sha.decode()
    have = {}
    for base, dirs, names in os.walk(V.lp(TREE)):
        dirs[:] = [d for d in dirs if d not in CACHE_DIRS]
        for n in names:
            if n.endswith(CACHE_EXT):
                continue
            full = os.path.join(base, n)
            have[os.path.relpath(full, V.lp(TREE)).replace('\\', '/')] = full
    common = sorted(set(blobs) & set(have))
    p = subprocess.Popen(['git', '--no-optional-locks', '-C', GWT8, 'cat-file', '--batch'], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE)
    exact = crlf = 0
    other = []
    for rel in common:
        p.stdin.write((blobs[rel] + '\n').encode())
        p.stdin.flush()
        header = p.stdout.readline().split()
        size = int(header[2])
        data = p.stdout.read(size)
        p.stdout.read(1)
        b = open(V.lp(have[rel]), 'rb').read()
        if b == data:
            exact += 1
        elif b.replace(b'\r\n', b'\n') == data:
            crlf += 1
        else:
            other.append(rel)
    p.stdin.close()
    p.wait()
    kb = V.rjson(OK2 / 'a29' / 'k925_blobs.json') or {}
    items = kb.get('blobs') or kb.get('files') or kb
    judge = {rel: (blobs.get(rel) == b) for rel, b in (items.items() if isinstance(items, dict) else [])
             if isinstance(b, str) and len(b) == 40}
    stage = V.rjson(OUTK / 'k92_judging_stage.json') or {}
    prep = V.rjson(OUTK / 'stages' / 'prep.json') or {}
    res = {'schema': 'vgates-tree/v1', 'rev': REV, 'n_blobs': len(blobs), 'n_files': len(have),
           'only_commit': sorted(set(blobs) - set(have))[:20], 'n_only_commit': len(set(blobs) - set(have)),
           'only_tree': sorted(set(have) - set(blobs))[:20], 'n_only_tree': len(set(have) - set(blobs)),
           'exact': exact, 'crlf_only': crlf, 'different': other[:20], 'n_different': len(other),
           'judge_blobs': {'n': len(judge), 'all_match': bool(judge) and all(judge.values()),
                           'k925_blobs_sha256': V.sha_file(OK2 / 'a29' / 'k925_blobs.json')},
           'stage_record': {'k92_head': stage.get('k92_head'), 'started': stage.get('started'),
                            'amendment_sha256': stage.get('amendment_sha256'), 'driver': stage.get('driver_sha256'),
                            'judge': stage.get('judge_sha256'), 'pins': stage.get('pins_sha256'),
                            'token': stage.get('token')},
           'prep_arms': prep.get('arms'), 'prep_anchors': prep.get('anchors'),
           'build_record_sha256': V.sha_file(TREE.parent / 'k92t.build.json')}
    res['ok'] = (not res['n_only_commit'] and not res['n_only_tree'] and not other and res['judge_blobs']['all_match']
                 and res['judge_blobs']['n'] >= 19)
    V.wjson(args.dest, res)
    print('VG_TREE ok=%s blobs=%d files=%d exact=%d crlf=%d diff=%d judge=%s' % (
        res['ok'], len(blobs), len(have), exact, crlf, len(other), res['judge_blobs']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
