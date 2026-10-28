"""VerifyGates 2 — comparison of the two rerun jobs (OK2/vg3t) with the k92t originals (OUTK).  Rule fixed before the
rerun and before reading the originals (amendment 30 section 10-7):
  files    job folder: summary.json, k92_record.json, k91_record.json (when present on either side), k92_series.npz;
           capture folder: capture.json (+ template.pickle sha reported).
  strings  lower case, '\\' -> '/', 'reports/k8/k92_b1/vg3t' -> 'reports/k8/k92_b1/k92t' before comparing.
  classes  every leaf (dict '/k', list '[i]'; numbers with their type, bool, None, strings):
           timing = the lower-case path holds wall / sec / time / rss / elapsed / when / started / finished / created /
                    pid / monotonic / date, or its last component is an amendment-21 L_T name;
           hash   = both values hex strings of 16-128 characters;
           other  = every other difference, and every one-sided leaf outside timing.
  npz      keys / t_end / stage / model / edges / stage_names equal (model NaN = NaN).
  result   REPRO_SAME per job iff 'other' = 0 in every file and the npz arrays are equal; else REPRO_DIFF (reported).
Output OUTV/rerun_cmp.json (paths, counts; no value)."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

VG = V.OK2 / 'vg3t'
JOBS = (('J', 'jb', 'TL3_2250_SAF_OBS_H3', 'TL3/002250/SAF'),
        ('F', 'f_b1', 'TL3_3300_s43_SAF_OBS_H3', 'TL3/003300_s43/SAF'))
TIMING = ('wall', 'sec', 'time', 'rss', 'elapsed', 'when', 'started', 'finished', 'created', 'pid', 'monotonic',
          'date')


def norm(s):
    return s.lower().replace('\\', '/').replace('reports/k8/k92_b1/vg3t', 'reports/k8/k92_b1/k92t')


def leaves(x, p='', out=None):
    out = {} if out is None else out
    if isinstance(x, dict):
        if not x:
            out[p + '/{}'] = '{}'
        for k, v in x.items():
            leaves(v, '%s/%s' % (p, norm(str(k))), out)
    elif isinstance(x, list):
        if not x:
            out[p + '[]'] = '[]'
        for i, v in enumerate(x):
            leaves(v, '%s[%d]' % (p, i), out)
    elif isinstance(x, str):
        out[p] = norm(x)
    else:
        out[p] = x
    return out


def timing(p):
    q = p.lower()
    return any(w in q for w in TIMING) or V.last_comp(p) in V.L_T


def cmp_json(a, b):
    la, lb = leaves(a), leaves(b)
    res = {'timing': 0, 'hash': 0, 'other': 0, 'other_paths': [], 'one_sided_timing': 0}
    for k in sorted(set(la) | set(lb)):
        if k not in la or k not in lb:
            if timing(k):
                res['one_sided_timing'] += 1
            else:
                res['other'] += 1
                res['other_paths'].append(V.gen(k) + ' (one side)')
            continue
        x, y = la[k], lb[k]
        if type(x) is type(y) and (x == y or (isinstance(x, float) and x != x and y != y)):
            continue
        if timing(k):
            res['timing'] += 1
        elif isinstance(x, str) and isinstance(y, str) and V.HEX_RE.match(x) and V.HEX_RE.match(y):
            res['hash'] += 1
        else:
            res['other'] += 1
            res['other_paths'].append(V.gen(k))
    res['other_paths'] = sorted(set(res['other_paths']))[:40]
    return res


def cmp_npz(pa, pb):
    import numpy as np
    if not pa.is_file() or not pb.is_file():
        return {'present': [pa.is_file(), pb.is_file()], 'equal': pa.is_file() == pb.is_file() == False}  # noqa: E712
    za, zb = np.load(V.lp(pa), allow_pickle=True), np.load(V.lp(pb), allow_pickle=True)
    out = {}
    for k in sorted(set(za.files) | set(zb.files)):
        if k not in za.files or k not in zb.files:
            out[k] = False
            continue
        a, b = za[k], zb[k]
        if a.dtype.kind == 'f' and b.dtype.kind == 'f':
            out[k] = a.shape == b.shape and bool(np.array_equal(a, b, equal_nan=True))
        else:
            out[k] = a.shape == b.shape and [str(x) for x in a.ravel()] == [str(x) for x in b.ravel()]
    return {'arrays': out, 'equal': all(out.values())}


def main():
    out = {'schema': 'vg3-rerun-cmp/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)), 'jobs': {}}
    for tag, root, lab, cap in JOBS:
        jn, jo = VG / root / 'sa' / 'jobs' / V.LABEL / lab, V.OUTK / root / 'sa' / 'jobs' / V.LABEL / lab
        cn, co = VG / root / 'sa' / 'cap' / V.LABEL / cap, V.OUTK / root / 'sa' / 'cap' / V.LABEL / cap
        files = {}
        for name, a, b in (('summary.json', jo, jn), ('k92_record.json', jo, jn), ('k91_record.json', jo, jn),
                           ('capture.json', co, cn)):
            da, db = V.rjson(a / name), V.rjson(b / name)
            if da is None and db is None and name == 'k91_record.json':
                continue
            if not isinstance(da, dict) or not isinstance(db, dict):
                files[name] = {'present': [isinstance(da, dict), isinstance(db, dict)], 'other': 1}
                continue
            files[name] = cmp_json(da, db)
        npz = cmp_npz(jo / 'k92_series.npz', jn / 'k92_series.npz')
        tpl = [V.sha_file(p) if p.is_file() else None for p in (co / 'template.pickle', cn / 'template.pickle')]
        ok_new = (V.rjson(jn / 'summary.json') or {}).get('ok')
        same = all(f.get('other', 0) == 0 for f in files.values()) and npz.get('equal') is True and ok_new is True
        out['jobs'][tag] = {'label': lab, 'root': root, 'files': files, 'npz': npz,
                            'template_sha_equal': tpl[0] is not None and tpl[0] == tpl[1], 'new_ok': ok_new,
                            'result': 'REPRO_SAME' if same else 'REPRO_DIFF'}
    steps = [x for x in (VG / 'steps.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()] if (
        VG / 'steps.jsonl').is_file() else []
    out['steps'] = len(steps)
    V.wjson(V.OUTV / 'rerun_cmp.json', out)
    print('VG3_RCMP %s' % {k: v['result'] for k, v in out['jobs'].items()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
