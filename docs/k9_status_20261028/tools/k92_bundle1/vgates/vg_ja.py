"""VerifyGates: J-a and the J wall-clock pairs recomputed from raw outputs with own code (no harness import).

J-a jobs (21; amendment 24 section 5.2 row J-a: "같은 잡 summary 숫자 잎 같음" vs V4/sa/jobs/k91t):
  every numeric leaf (int / float, not bool) of both summary.json; one-sided numeric leaves listed; a differing or
  one-sided numeric leaf is "timing" only when its last key (trailing [i] removed) is in L_T (amendment 21, 55 names)
  or ends with wall_sec / _sec / elapsed; SAME iff every differing / one-sided numeric leaf is timing and new ok true.
  (stricter than the harness G5 rule, which drops every key containing wall/sec/time/rss/elapsed.)
J-a decisions (2: full 002700 SAF / BASE hooks; amendment 29 section 6.1-3, amendment 21 section 6): own
  implementation of N (amendment 21 6.1 + amendment 27 K92-N), deep diff (dict key / list index / list length),
  HARD H1-H5, allowed V (7 paths) + R3 (R3-01..06, 08 regexes as declared) + F1/F2/F3 (L_T), D1-D5 excluded except
  the narrowed R3-03 (new = file sha of the sibling path), R3-08 CAO (new = new-tree CAO sha) and A_K92 RS (new =
  new-tree RS sha, old = old-tree RS sha, old in the five known values).  PASS = HARD same + unclassified 0.
J wall (amendment 24 section 5.2 note, amendment 26 G-K5 form): pairs = the 11 SAF H3 OBS labels, A = OUTK/ja
  (SAF-K91), B = OUTK/jb (SAF-K92b1); clean = vissim_counts pre/post 0 on both and exit 0 and ok true both;
  ratio = summary wall_sec B / A; PASS iff median(clean) <= 1.05 / 1.033718118959995; IQR inclusive reported.
Outputs verdicts, counts, generalized paths, sha.  No objective value is printed.

    python -B vg_ja.py --dest <json>
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402
from vg_cmp import L_T  # noqa: E402

OUTK = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/k92t')
V4 = Path(r'D:/VISSIM-merge/k8_gates_out_v4')
NEW_TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t')
OLD_TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k91t')
GRID9 = (900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950)
JOBS = (['TL3_%d_SAF_OBS_H3' % T for T in GRID9]
        + [lab % arm for arm in ('SAF', 'BASE') for lab in
           ('TL3_900_s43_%s_OBS_H3', 'TL3_900_s47_%s_OBS_H3', 'TL3_2700_%s_OBS_H42', 'TL3_4950_%s_OBS_H27',
            'TL3_900_%s_OBS_H3_C11', 'TL3_900_%s_OBS_H3_TAN_ad')])
FULL = ('002700_SAF_hooks', '002700_BASE_hooks')
PAIRS = ['TL3_%d_SAF_OBS_H3' % T for T in GRID9] + ['TL3_900_s43_SAF_OBS_H3', 'TL3_900_s47_SAF_OBS_H3']
LIMIT = 1.05 / 1.033718118959995
RS_REL = 'evaluation/controllers/runtime_setup.py'
CAO_REL = 'evaluation/controllers/control_area_objective.py'
RS_KNOWN = ('8a5aec79', 'ea79be3a', '0ba3fa61', '38c7a580', '472d7f9c')

# ---------------------------------------------------------------- N
N_RULES = [
    (re.compile(r'd:/vissim-merge/frozen/sdmpc31_[0-9a-f]{8}_[0-9]{12}'), '<root>'),
    (re.compile(r'd:/vissim-merge/sim3-n31-k8'), '<root>'),
    (re.compile(r'd:/vissim-merge/k8_gate_trees/(?:k92b1/(?:(?:a25|a26decl|a27)/)?(?!(?:a25|a26decl|a27)'
                r'(?![a-z0-9_]))|k92attrib/)[a-z0-9_]+(?=/|$)'), '<root>'),
    (re.compile(r'd:/vissim-merge/k8_gate_trees/(?:s31fail/tree74(?:_base|_f1)?|[a-z0-9_]+)'), '<root>'),
    (re.compile(r'd:/vissim_runs/20261001_v3c3/reports/k8/(?:offline_gates|offline_gates_k8h)/(?:[a-z0-9_]+/)*?'
                r't[0-9]{6}(?:_[a-z0-9]+)*'), '<bundle>'),
    (re.compile(r'd:/vissim_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+'), '<run>'),
    (re.compile(r'd:/vissim_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s[0-9]+'), '<run>'),
]
N_NAMES = re.compile(r'sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+|sdmpc31_v3c3_nc_s[0-9]+')


def N(s):
    s = s.lower().replace('\\\\', '/').replace('\\', '/')
    for rx, rep in N_RULES:
        s = rx.sub(rep, s)
    return N_NAMES.sub('<name>', s)


class Collision(Exception):
    pass


def ntree(x):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            nk = N(str(k))
            if nk in out:
                raise Collision(nk)
            out[nk] = ntree(v)
        return out
    if isinstance(x, list):
        return [ntree(v) for v in x]
    if isinstance(x, str):
        return N(x)
    return x


def deep_diff(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((path + '/' + k, 'one-sided'))
            else:
                deep_diff(a[k], b[k], path + '/' + k, out)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'length'))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            deep_diff(x, y, '%s[%d]' % (path, i), out)
        return
    if type(a) is not type(b):
        out.append((path, 'type'))
    elif a != a and b != b:
        return
    elif a != b:
        out.append((path, 'value'))


def get(doc, path):
    cur = doc
    for tok in re.findall(r'/([^/\[]+)|\[(\d+)\]', path):
        k, i = tok
        if k:
            if not isinstance(cur, dict) or k not in cur:
                return None
            cur = cur[k]
        else:
            if not isinstance(cur, list) or int(i) >= len(cur):
                return None
            cur = cur[int(i)]
    return cur


V_PATHS = {'/metadata/decision_wall_sec', '/metadata/prediction_wall_sec', '/prediction/wall_sec',
           '/run_provenance/inputs/state_json/path', '/run_provenance/inputs/state_json/sha256',
           '/metadata/run_provenance/inputs/state_json/path', '/metadata/run_provenance/inputs/state_json/sha256'}
SUB = r'(?:[/\[].*)?'
R3 = {
    'R3-01': r'/(?:metadata/)?run_provenance/(?:workspace_git_commit|execution_fingerprint_sha256)',
    'R3-02': r'/(?:metadata/)?run_provenance/imported_modules' + SUB,
    'R3-03': r'/(?:metadata/)?run_provenance/inputs/[^/]+/sha256',
    'R3-04': r'/(?:metadata/)?run_provenance/(?:workspace_root|numsim_repo_root)',
    'R3-05': r'/(?:metadata/)?run_provenance/inputs/(?:adapter_py|calibration_json|control_mapping_json|'
             r'detector_mapping_json|fixed_signal_schedule_py|intersection_adjacency_json|link_assignment_json|'
             r'main_vbs_runner|numsim_default_yaml|parameters_json|parameters_py|storage_capacity_json|'
             r'strict_signal_program_py|tuning_json|watchdog_wrapper)/path',
    'R3-06': r'/metadata/(?:detector_mapping_resolved_path|native_phase_share_map_path)',
    'R3-08': r'/metadata/joint_leader_selection/tangent_derivatives\[\d+\]/transformed_source_sha256' + SUB,
}
R3C = {k: re.compile(v) for k, v in R3.items()}
HEX = re.compile(r'^[0-9a-f]{16,128}$')
ISO = re.compile(r'^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}')   # N lowercases strings
F2 = re.compile(r'(?i)(sha256|sha1|sha|token|fingerprint|digest|hash)$')
LT = set(L_T)


def gen(path):
    return re.sub(r'\[\d+\]', '[*]', path)


def last(path):
    k = path.rsplit('/', 1)[-1]
    while k.endswith(']') and '[' in k:
        k = k[:k.rindex('[')]
    return k


def is_d(path):
    g, l = gen(path), last(path)
    if l.endswith('action_token'):
        return 'D1'
    if l.endswith('evidence_sha256') or l in ('territory_sha256', 'policy_sha256', 'receipt_sha256',
                                              'lane_plant_manifest_sha256', 'numsim_src_sha256') \
            or g.endswith('/physical_ramp_recorded_csv/sha256'):
        return 'D2'
    if g.startswith('/metadata/') and not g.startswith('/metadata/run_provenance') \
            and '/joint_leader_selection/' not in g and l.endswith('sha256'):
        return 'D2b'
    if re.match(r'^/(metadata/)?run_provenance/(imported_modules/[^/]+/sha256|signal_program_sha256/.+|'
                r'numsim_git_commit|numsim_snapshot_commit|run_id)$', g):
        return 'D3'
    m = re.match(r'^/(metadata/)?run_provenance/inputs/([^/]+)/sha256$', g)
    if m and m.group(2) not in ('tuning_json', 'main_vbs_runner', 'watchdog_wrapper', 'state_json'):
        return 'D4'
    m = re.match(r'^/metadata/joint_leader_selection/tangent_derivatives\[\*\]/transformed_source_sha256/(.+)$', g)
    if m and m.group(1) != '<root>/' + CAO_REL:
        return 'D5'
    return None


HARD_PREFIX = ('/n_p_star', '/n_uf_star',   # N lowercases dict keys (amendment 21 section 6.1)
               '/ramp_metering', '/vsl', '/green_times', '/offsets',
               '/inflow_outflow_allocation', '/metadata/joint_leader_selection/selected_objective',
               '/metadata/joint_leader_selection/held_objective', '/metadata/joint_leader_selection/warm_start_objective',
               '/metadata/joint_leader_selection/selection_status', '/metadata/joint_leader_selection/converged',
               '/metadata/joint_leader_selection/feasible', '/metadata/sdmpc_state', '/metadata/sdmpc_active',
               '/metadata/far_measured_seeded', '/prediction', '/prediction_error')
HARD_RX = re.compile(r'^/metadata/(far_rate_est_[^/\[]*|head_[^/\[]*)')


def in_hard(path):
    for p in HARD_PREFIX:
        if path == p or path.startswith(p + '/') or path.startswith(p + '['):
            return True
    return bool(HARD_RX.match(path))


def progress_last(p):
    rows = []
    if not Path(p).is_file():
        return None
    for ln in open(V.lp(p), 'rb').read().decode('utf-8', 'replace').splitlines():
        try:
            rows.append(json.loads(ln))
        except ValueError:
            continue
    keep = {}
    for r in rows:
        for k in ('objective', 'held_objective'):
            if isinstance(r, dict) and k in r:
                keep[k] = repr(r[k])
    return keep


def decision(name, T=2700):
    od = V4 / 'sa' / 'full' / 'k91t' / name
    nd = OUTK / 'ja' / 'sa' / 'full' / 'k92t' / name
    s6 = '%06d' % T
    row = {'json_sha256': {}, 'counts': {}, 'unclassified': [], 'hard_diff': []}
    jo, jn = od / ('action_%s.json' % s6), nd / ('action_%s.json' % s6)
    co, cn = od / ('action_%s.csv' % s6), nd / ('action_%s.csv' % s6)
    if not all(p.is_file() for p in (jo, jn, co, cn)):
        row['verdict'] = 'INCOMPLETE'
        return row
    row['json_sha256'] = {'old': V.sha_file(jo), 'new': V.sha_file(jn)}
    row['H1_csv_equal'] = V.sha_file(co) == V.sha_file(cn)
    po, pn = progress_last(od / ('action_%s.joint.progress.jsonl' % s6)), \
        progress_last(nd / ('action_%s.joint.progress.jsonl' % s6))
    row['H3_progress_equal'] = po == pn
    raw_o, raw_n = V.rjson(jo), V.rjson(jn)
    try:
        A, B = ntree(raw_o), ntree(raw_n)
    except Collision as exc:
        row['verdict'] = 'INCOMPLETE'
        row['why'] = 'N collision %s' % exc
        return row
    diffs = []
    deep_diff(A, B, '', diffs)
    rs_new, rs_old = V.sha_file(NEW_TREE / RS_REL), V.sha_file(OLD_TREE / RS_REL)
    cao_new = V.sha_file(NEW_TREE / CAO_REL)
    row['rs'] = {'new_tree': rs_new[:16], 'old_tree': rs_old[:16], 'old_known': rs_old[:8] in RS_KNOWN}
    counts = {}
    checks = []
    for path, kind in diffs:
        cls = None
        a, b = get(A, path), get(B, path)
        d = is_d(path)
        g, l = gen(path), last(path)
        if path in V_PATHS:
            cls = 'V'
        elif kind == 'value' and g == '/metadata/joint_leader_selection/tangent_derivatives[*]/transformed_source_sha256/<root>/' + RS_REL:
            ok = isinstance(a, str) and isinstance(b, str) and b == rs_new and a == rs_old and rs_old[:8] in RS_KNOWN
            checks.append({'path': g, 'rule': 'A_K92', 'ok': ok})
            cls = 'A_K92' if ok else None
        elif kind == 'value' and g == '/metadata/joint_leader_selection/tangent_derivatives[*]/transformed_source_sha256/<root>/' + CAO_REL:
            ok = isinstance(b, str) and b == cao_new
            checks.append({'path': g, 'rule': 'R3-08 CAO', 'ok': ok})
            cls = 'R3-08' if ok else None
        elif kind == 'value' and re.match(r'^/(metadata/)?run_provenance/inputs/(tuning_json|main_vbs_runner|'
                                          r'watchdog_wrapper)/sha256$', g):
            sib = get(raw_n, path.rsplit('/', 1)[0] + '/path')
            ok = isinstance(sib, str) and Path(sib).is_file() and V.sha_file(sib) == b
            checks.append({'path': g, 'rule': 'R3-03', 'ok': ok})
            cls = 'R3-03' if ok else None
        elif d is None:
            for rid, rx in R3C.items():
                if rx.fullmatch(path):
                    cls = rid
                    break
            if cls is None and kind == 'value':
                if isinstance(a, str) and isinstance(b, str) and HEX.match(a) and HEX.match(b):
                    cls = 'F1'
                elif F2.search(l) and ((isinstance(a, str) and isinstance(b, str)) or (a is None and b is None)):
                    cls = 'F2'
                elif l in LT and not (l == 'seconds' and path.rsplit('/', 2)[-2] == 'final_check_reserve') and (
                        (V.is_num(a) and V.is_num(b)) or (isinstance(a, str) and isinstance(b, str)
                                                          and ISO.match(a) and ISO.match(b))
                        or (a is None and b is None)):
                    cls = 'F3'
        if in_hard(path) and cls not in ('V', 'F3'):
            row['hard_diff'].append(g)
            continue
        if cls is None:
            row['unclassified'].append([g, kind, d])
        else:
            counts[cls] = counts.get(cls, 0) + 1
    row['counts'] = counts
    row['checks'] = checks
    row['n_diff'] = len(diffs)
    hard_same = row['H1_csv_equal'] and row['H3_progress_equal'] and not row['hard_diff']
    row['hard'] = 'SAME' if hard_same else 'DIFF'
    row['verdict'] = 'FAIL' if not hard_same else ('PASS' if not row['unclassified'] else 'HOLD')
    ro, rn = V.rjson(od / 'run.json') or {}, V.rjson(nd / 'run.json') or {}
    row['run_json_equal'] = {k: V.canon(ro.get(k)) == V.canon(rn.get(k)) for k in ('objective', 'held_objective',
                                                                                    'exit', 'csv_sha256')}
    return row


TIMING_RX = re.compile(r'(wall_sec|_sec|elapsed)$')


def job(lab):
    old = V.rjson(V4 / 'sa' / 'jobs' / 'k91t' / lab / 'summary.json')
    new = V.rjson(OUTK / 'ja' / 'sa' / 'jobs' / 'k92t' / lab / 'summary.json')
    if old is None or new is None:
        return {'verdict': 'INCOMPLETE', 'present': [old is not None, new is not None]}
    lo, ln = V.leaves(old), V.leaves(new)
    no = {k for k, v in lo.items() if V.is_num(v)}
    nn = {k for k, v in ln.items() if V.is_num(v)}
    common = no & nn
    differ = sorted(k for k in common if not (repr(lo[k]) == repr(ln[k]) and type(lo[k]) is type(ln[k])))
    one = sorted(no ^ nn)

    def timing(k):
        lk = last(k)
        return lk in LT or bool(TIMING_RX.search(lk))
    bad = [k for k in differ + one if not timing(k)]
    sdiff = sorted(k for k in set(lo) & set(ln) if isinstance(lo[k], str) and lo[k] != ln[k])
    return {'numeric_common': len(common), 'numeric_differ': len(differ), 'numeric_one_sided': len(one),
            'timing_only': [gen(k) for k in differ + one][:10], 'non_timing_diff': [gen(k) for k in bad][:20],
            'n_non_timing_diff': len(bad), 'string_differ': len(sdiff),
            'string_differ_paths': sorted({gen(k) for k in sdiff})[:20], 'ok_new': new.get('ok'),
            'verdict': 'SAME' if not bad and new.get('ok') is True else 'DIFF'}


def jwall():
    rows = []
    for lab in PAIRS:
        a, b = OUTK / 'ja' / 'sa' / 'jobs' / 'k92t' / lab, OUTK / 'jb' / 'sa' / 'jobs' / 'k92t' / lab
        sa_, sb = V.rjson(a / 'summary.json') or {}, V.rjson(b / 'summary.json') or {}
        va, vb = V.rjson(a / 'vissim_counts.json') or {}, V.rjson(b / 'vissim_counts.json') or {}
        counts = [va.get('vissim_count_pre'), va.get('vissim_count_post'), vb.get('vissim_count_pre'),
                  vb.get('vissim_count_post')]
        clean = (all(x == 0 for x in counts) and va.get('exit') == 0 and vb.get('exit') == 0
                 and sa_.get('ok') is True and sb.get('ok') is True)
        wa, wb = sa_.get('wall_sec'), sb.get('wall_sec')
        rows.append({'label': lab, 'wall_A': wa, 'wall_B': wb, 'clean': clean, 'counts': counts,
                     'A_before_B': va.get('end') is not None and vb.get('start') is not None and va['end'] <= vb['start'],
                     'gap_sec': (vb['start'] - va['end']) if (va.get('end') and vb.get('start')) else None,
                     'ratio': wb / wa if (wa and wb) else None})
    r = [x['ratio'] for x in rows if x['clean'] and x['ratio'] is not None]
    med = statistics.median(r) if r else None
    q = statistics.quantiles(r, n=4, method='inclusive') if len(r) > 1 else None
    return {'n_pairs': len(rows), 'n_clean': len(r), 'median': med, 'limit': LIMIT,
            'iqr_inclusive': (q[2] - q[0]) if q else None, 'min': min(r) if r else None, 'max': max(r) if r else None,
            'verdict': ('INCOMPLETE' if not r else ('PASS' if med <= LIMIT else 'FAIL')), 'rows': rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    rows = {lab: job(lab) for lab in JOBS}
    for name in FULL:
        rows[name] = decision(name)
    ok = all(r['verdict'] in ('SAME', 'PASS') for r in rows.values())
    inc = any(r['verdict'] == 'INCOMPLETE' for r in rows.values())
    res = {'schema': 'vgates-ja/v1', 'n_items': len(rows), 'verdict': 'INCOMPLETE' if inc else ('PASS' if ok else 'FAIL'),
           'failed': sorted(k for k, r in rows.items() if r['verdict'] not in ('SAME', 'PASS')), 'rows': rows,
           'jwall': jwall()}
    V.wjson(args.dest, res)
    print('VG_JA %s n=%d failed=%s jwall=%s median=%s clean=%s' % (res['verdict'], len(rows), res['failed'],
                                                                   res['jwall']['verdict'], res['jwall']['median'],
                                                                   res['jwall']['n_clean']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
