"""VerifyGates 2 — J-a recomputed (amendment 30 section 5.4, D-K9-57 4).  A NEW file: not vg_ja.py / vg_ja2.py, no
byte copy of them, no import of them, of the harness, of the k92t drivers or judges (only vg3lib, written from the
amendment texts).  Pinned in KB/LOG.md before its first run on V4 k91t or OUTK data; run once.

Items (amendment 24 :325 J-a row; the per-family state choice of the base judge, disclosed there):
  21 jobs  TL3_<T>_SAF_OBS_H3 (T in GRID9) and, per arm SAF / BASE, TL3_900_s43_<arm>_OBS_H3, TL3_900_s47_<arm>_OBS_H3,
           TL3_2700_<arm>_OBS_H42, TL3_4950_<arm>_OBS_H27, TL3_900_<arm>_OBS_H3_C11, TL3_900_<arm>_OBS_H3_TAN_ad.
           old = V4/sa/jobs/k91t/<label>/summary.json, new = OUTK/ja/sa/jobs/k92t/<label>/summary.json.
           SAME iff both present, new ok is True, every numeric leaf (K9-1 G5 rule: int / float, bool excluded; a
           leaf whose lower-case path holds a timing word or a G5 exclusion word is left out) present on both sides
           and bit-equal (NaN = NaN).  String / hash / path leaves reported only.
  2 decisions  002700_SAF_hooks, 002700_BASE_hooks: old = V4/sa/full/k91t/<name>, new = OUTK/ja/sa/full/k92t/<name>,
           amendment 21 section 6 four outcomes with N (amendment 27 / 29 K9-2 root rule), HARD H1-H5, allowed
           V u R3 u F - D, A_K92 four conditions with old_root = k8_gate_trees/k91t, new_root = the k92t tree,
           key-off (no A_K92-M / H5 allowance).  PASS only.  R-CR: for every L file whose k91t form is C or A the
           k92t tree has the same form (forms from the b9734abe blobs: C = blob bytes, A = LF -> CRLF).
  J-a PASS iff all 23 items SAME / PASS.  Then each item verdict is compared with OUTK/judge/ja.json (S-K45 on any
  difference).  Output OUTV/ja.json (blind: verdicts, counts, generalized paths, sha)."""
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

JOBS = (['TL3_%d_SAF_OBS_H3' % T for T in V.GRID9]
        + [lab % arm for arm in ('SAF', 'BASE') for lab in
           ('TL3_900_s43_%s_OBS_H3', 'TL3_900_s47_%s_OBS_H3', 'TL3_2700_%s_OBS_H42', 'TL3_4950_%s_OBS_H27',
            'TL3_900_%s_OBS_H3_C11', 'TL3_900_%s_OBS_H3_TAN_ad')])
FULL = ('002700_SAF_hooks', '002700_BASE_hooks')
L_FILES = ('diagnostics/test_k8_s1_admission_owner.py', 'diagnostics/test_k8_s3_has_transfer.py',
           'evaluation/controllers/lane_offramp_runtime.py', 'evaluation/controllers/meter_spill.py',
           'evaluation/controllers/offramp_split_forecast.py', 'evaluation/controllers/stopline_approach.py',
           'scripts/decision_hold.py', 'scripts/tests/test_decision_hold.py',
           'scripts/tests/test_k8_decision_hold_vbs.py', 'scripts/tests/test_k8_s6_decision_capture_vbs.py')
GWT8 = r'D:/VISSIM-merge/sim3-n31-k8'
K8 = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'


def cr_forms():
    """Amendment 27 section 2.2: forms of the 10 L files in k91t and the k92t tree; the pair rule."""
    rows, bad = {}, []
    for rel in L_FILES:
        blob = subprocess.run(['git', '--no-optional-locks', '-C', GWT8, 'show', '%s:%s' % (K8, rel)],
                              capture_output=True).stdout
        c_sha = V.sha_bytes(blob)
        a_sha = V.sha_bytes(blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        form = {}
        for name, root in (('k91t', V.K91T_TREE), ('k92t', V.TREE)):
            p = Path(root) / rel
            if not p.is_file():
                form[name] = '-'
                continue
            s = V.sha_file(p)
            form[name] = 'C' if s == c_sha else ('A' if s == a_sha else 'X')
        rows[rel] = dict(form, cr_in_blob=blob.count(b'\r'), blob_bytes=len(blob))
        if form['k91t'] in ('C', 'A') and form['k92t'] != form['k91t']:
            bad.append(rel)
    s91 = ''.join(rows[r]['k91t'] for r in L_FILES)
    s92 = ''.join(rows[r]['k92t'] for r in L_FILES)
    return {'k91t': s91, 'k92t': s92, 'rows': rows, 'mismatch': bad,
            'ok': any(rows[r]['k91t'] in ('C', 'A') for r in L_FILES) and not bad}


def job_item(lab):
    old = V.rjson(V.V4 / 'sa' / 'jobs' / 'k91t' / lab / 'summary.json')
    new = V.rjson(V.OUTK / 'ja' / 'sa' / 'jobs' / V.LABEL / lab / 'summary.json')
    if not isinstance(old, dict) or not isinstance(new, dict):
        return {'verdict': 'INCOMPLETE', 'present': [isinstance(old, dict), isinstance(new, dict)]}
    c = V.g5_compare(old, new)
    same = c['numeric_differ'] == 0 and c['numeric_one_sided'] == 0 and new.get('ok') is True and c['depth_cut'] == 0
    c['ok'] = [old.get('ok'), new.get('ok')]
    c['verdict'] = 'SAME' if same else 'DIFF'
    return c


def main():
    out = {'schema': 'vg3-ja/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)),
           'lib_sha256': V.sha_file(Path(V.__file__)), 'old_root': str(V.K91T_TREE), 'new_root': str(V.TREE)}
    out['cr'] = cr_forms()
    rows = {}
    for lab in JOBS:
        rows[lab] = job_item(lab)
    for name in FULL:
        od = V.V4 / 'sa' / 'full' / 'k91t' / name
        nd = V.OUTK / 'ja' / 'sa' / 'full' / V.LABEL / name
        r = V.decision_compare(od, nd, 2700, V.TREE, V.K91T_TREE)
        want_root = 'd:/vissim-merge/k8_gate_trees/k92b1/a27/k92t'
        r['own_root_only'] = all(x == want_root for x in r.get('own_k92_roots_new', []))
        if r.get('verdict') == 'PASS' and not out['cr']['ok']:
            r['verdict'] = 'INCOMPLETE'
            r['why'] = 'R-CR pair false'
        rows[name] = r
    vs = [r['verdict'] for r in rows.values()]
    if 'INCOMPLETE' in vs or len(rows) != 23:
        verdict = 'INCOMPLETE'
    elif all(v in ('SAME', 'PASS') for v in vs):
        verdict = 'PASS'
    else:
        verdict = 'FAIL'
    out.update(rows=rows, verdict=verdict, n_items=len(rows),
               not_same=sorted(k for k, r in rows.items() if r['verdict'] not in ('SAME', 'PASS')))
    # agreement with the recorded judge (amendment 30 section 5.4-4)
    rec = V.rjson(V.OUTK / 'judge' / 'ja.json') or {}
    rrows = rec.get('rows') or {}
    agree = {}
    for k, r in rows.items():
        rr = rrows.get(k) or {}
        a = {'verdict': [rr.get('verdict'), r['verdict']]}
        a['same'] = rr.get('verdict') == r['verdict']
        if k in FULL:
            a['hard'] = [rr.get('hard_verdict'), 'SAME' if r.get('hard_same') else 'DIFFERENT']
            a['unclassified'] = [rr.get('unclassified_n'), r.get('unclassified_n')]
            a['same'] = a['same'] and a['hard'][0] == a['hard'][1] and a['unclassified'][0] == a['unclassified'][1]
        agree[k] = a
    out['recorded'] = {'file': str(V.OUTK / 'judge' / 'ja.json'), 'sha256': V.sha_file(V.OUTK / 'judge' / 'ja.json'),
                       'verdict': rec.get('verdict'), 'n_items': rec.get('n_items')}
    out['agreement'] = agree
    out['agree_all'] = (all(a['same'] for a in agree.values()) and rec.get('verdict') == verdict
                        and rec.get('n_items') == len(rows) and set(rrows) == set(rows))
    V.wjson(V.OUTV / 'ja.json', out)
    print('VG3_JA verdict=%s items=%d not_same=%s agree_recorded=%s cr=%s/%s' % (
        verdict, len(rows), out['not_same'], out['agree_all'], out['cr']['k91t'], out['cr']['k92t']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
