"""PRE_VP_R3 X5: move the stopped P1 job (v3c3-s31 T=1,800) to *_interrupted_* names (one-off, not a run tool).
Folder -> GT/out/interrupted/plant_P/<name>_interrupted_r2stop_<KST stamp> (outside plant_P: vp_analyze.py:170-171 reads
every folder in plant_P); its .done / .out.txt / .check.txt in VP/logs/plantP -> <tag>_interrupted_r2stop_<stamp>.<ext>.
Refuses when our own LOCK is held or a target exists.  Writes review_r3/move_interrupted_r3.json (no full paths).

    python -B r3_move_interrupted.py"""
import datetime
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import vp_common as C  # noqa: E402

TAG = 'P_v3c3-s31_T001800'
KEY = ['probe.json', 'jobcheck.json', 'job_summary.json', 'job.log', 'bundle_record.json']


def files(root):
    out = {}
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root).replace(os.sep, '/')] = os.path.getsize(p)
    return out


def main():
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    src = C.OUT / 'plant_P' / 'v3c3-s31_T001800'
    dst_parent = C.OUT / 'interrupted' / 'plant_P'
    dst = dst_parent / ('v3c3-s31_T001800_interrupted_r2stop_%s' % stamp)
    logdir = C.VP / 'logs' / 'plantP'
    if not src.is_dir() or dst.exists():
        raise SystemExit('source missing or target exists')
    if C.LOCK.exists():
        holder = json.loads(C.LOCK.read_text(encoding='utf-8'))
        if holder.get('owner') == 'vsl_plant':
            raise SystemExit('our own LOCK is held: refuse to move')
    before = {k: C.sha256_file(src / k) for k in KEY}
    fb = files(src)
    logs_before = {s: (C.sha256_file(logdir / (TAG + s)) if (logdir / (TAG + s)).is_file() else None)
                   for s in ('.done', '.out.txt', '.check.txt')}
    dst_parent.mkdir(parents=True, exist_ok=True)
    os.rename(src, dst)
    moved_logs = {}
    for s in ('.done', '.out.txt', '.check.txt'):
        a = logdir / (TAG + s)
        b = logdir / ('%s_interrupted_r2stop_%s%s' % (TAG, stamp, s))
        if a.is_file():
            if b.exists():
                raise SystemExit('log target exists')
            os.rename(a, b)
            moved_logs[s] = {'to': b.name, 'sha256': C.sha256_file(b), 'same_as_before': C.sha256_file(b) == logs_before[s]}
    after = {k: C.sha256_file(dst / k) for k in KEY}
    fa = files(dst)
    rec = {'schema': 'vp-r3-move/1', 'kst': C.kst(), 'basis': 'PRE_VP_R3 X5 (D-K9-108, PRE_VP_FIXED section 8)',
           'job': TAG, 'folder_from': 'GT/out/plant_P/v3c3-s31_T001800',
           'folder_to': 'GT/out/interrupted/plant_P/' + dst.name,
           'files_n_before': len(fb), 'files_n_after': len(fa), 'bytes_before': sum(fb.values()),
           'bytes_after': sum(fa.values()), 'same_file_list': fb == fa, 'key_sha256_before': before,
           'key_sha256_after': after, 'key_same': before == after, 'logs_moved': moved_logs,
           'src_exists_after': src.exists(), 'done_left_for_queue': (logdir / (TAG + '.done')).exists(),
           'plant_P_folders_after': sorted(p.name for p in (C.OUT / 'plant_P').iterdir() if p.is_dir())}
    C.write_json(C.VP / 'review_r3' / 'move_interrupted_r3.json', rec)
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
