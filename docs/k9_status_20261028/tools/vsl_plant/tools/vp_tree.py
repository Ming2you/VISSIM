"""Scratch code tree for the plant probes = byte copy of FRZ_K92 (V-A frozen tree, head c20aff1d).

    python -B vp_tree.py build      (heavy IO; caller holds the shared LOCK)
    python -B vp_tree.py verify     (re-hash every FREEZE.json file in the copy)

The frozen tree is only read (robocopy source).  The copy GT/code_va is where the adapter and the SDMPC workers run,
so the tangent marshal cache (__tangentcache__) and __pycache__ land in the copy, never in FRZ_K92.  Check: every
FREEZE.json `files` entry exists in the copy with the same sha256; FREEZE.json itself has the pinned sha256.
Writes GT/code_va and GT/code_va.tree.json."""
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402

LOG = C.make_logger(C.VP / 'logs' / 'vp_tree.log')


def verify():
    freeze = C.FRZ_VA / 'FREEZE.json'
    fsha = C.sha256_file(freeze)
    if fsha != C.FRZ_VA_FREEZE_SHA:
        raise SystemExit('FREEZE.json sha differs: ' + fsha)
    files = C.read_json(freeze)['files']
    bad, missing = [], []
    for rel, sha in files.items():
        p = C.CODE / rel
        if not p.is_file():
            missing.append(rel)
            continue
        if C.sha256_file(p) != sha:
            bad.append(rel)
    rec = {'schema': 'vp-tree/1', 'checked_kst': C.kst(), 'source': str(C.FRZ_VA), 'copy': str(C.CODE),
           'freeze_sha256': fsha, 'files_expected': len(files), 'missing': missing[:50], 'missing_n': len(missing),
           'differs': bad[:50], 'differs_n': len(bad), 'ok': not missing and not bad}
    C.write_json(str(C.CODE) + '.tree.json', rec)
    LOG('TREE_VERIFY ok=%s expected=%d missing=%d differs=%d' % (rec['ok'], len(files), len(missing), len(bad)))
    return rec


def build():
    C.require_space(LOG)
    if C.CODE.exists() and any(C.CODE.iterdir()):
        raise SystemExit('code copy already exists (verify only): ' + str(C.CODE))
    C.CODE.mkdir(parents=True, exist_ok=True)
    argv = ['robocopy.exe', str(C.FRZ_VA), str(C.CODE), '/E', '/XD', '__pycache__', '__tangentcache__',
            '.pytest_cache', '.git', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1']
    LOG('ROBOCOPY start %s -> %s' % (C.FRZ_VA, C.CODE))
    rc = subprocess.run(argv, capture_output=True, text=True, creationflags=C.BELOW_NORMAL).returncode
    LOG('ROBOCOPY exit=%d' % rc)
    if rc >= 8:
        raise SystemExit('robocopy failed %d' % rc)
    return verify()


if __name__ == '__main__':
    rec = build() if sys.argv[1:] == ['build'] else verify()
    print(json.dumps({k: rec[k] for k in ('ok', 'files_expected', 'missing_n', 'differs_n')}))
    sys.exit(0 if rec['ok'] else 2)
