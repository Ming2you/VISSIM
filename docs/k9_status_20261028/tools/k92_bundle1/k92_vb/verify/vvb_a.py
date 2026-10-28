"""VerifyVB 2026-10-22, part A + C (independent; stdlib only).

Recomputes, from the RR record files only, the facts that VB_PRECHECK_STOP.md (e9a09758...) states in
section 2.2 (record leaves that carry the previous action file's location or byte sha, classified by the
amendment-21 section 6 TEXT -- own code, nothing imported from GWT8, the V-B dev probes or the harness) and
section 4 (RR record flags at the V-B chain times), plus the VB-I1 decision counts of amendment 24 :547.

BLIND: writes/prints paths (normalized), rule names, counts, booleans and sha256 only.  No objective, prediction,
observed or capacity value is printed or written.  Reads RR (J1 record runs, not blind) only; writes only
--out (one JSON file).

    python -B vvb_a.py --out <file.json>
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

sys.dont_write_bytecode = True
RR = 'D:/VISSIM_runs/20261004_sdmpc31_k8'
OK2 = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1'
# amendment 24 :526-531 (chains) and :547 (VB-I1 = OFF chains: T = 3,000 and 3,150 of VB-31/43/41, all 8 of VB-41w)
CHAINS = {'VB-31': 'sdmpc31_v3c3_k8j1r_s31', 'VB-43': 'sdmpc31_v3c3_k8j1_s43', 'VB-41': 'sdmpc31_v3c3_k8j1_s41',
          'VB-41w': 'sdmpc31_v3c3_k8j1_s41'}
WINDOW = list(range(3000, 4501, 150))
WARM = [1, 150, 300, 450, 600, 750, 900, 1050]
CHAIN_T = {'VB-31': WINDOW, 'VB-43': WINDOW, 'VB-41': WINDOW, 'VB-41w': WARM}
OFF_T = {'VB-31': [3000, 3150], 'VB-43': [3000, 3150], 'VB-41': [3000, 3150], 'VB-41w': WARM}

# ---- amendment 21 section 6.1 N (text), with the amendment 27 section 2.1 K9-2 tree-root rule (text) ----
N_RULES = [
    (r'd:/vissim-merge/frozen/sdmpc31_[0-9a-f]{8}_[0-9]{12}', '<root>'),
    (r'd:/vissim-merge/sim3-n31-k8', '<root>'),
    (r'd:/vissim-merge/k8_gate_trees/k92b1/(?:(?:a25|a26decl|a27)/)?[a-z0-9_]+(?=/|$)', '<root>'),
    (r'd:/vissim-merge/k8_gate_trees/k92attrib/[a-z0-9_]+(?=/|$)', '<root>'),
    (r'd:/vissim-merge/k8_gate_trees/(?:s31fail/tree74(?:_base|_f1)?|[a-z0-9_]+)', '<root>'),
    (r'd:/vissim_runs/20261001_v3c3/reports/k8/(?:offline_gates|offline_gates_k8h)/(?:[a-z0-9_]+/)*?t[0-9]{6}(?:_[a-z0-9]+)*',
     '<bundle>'),
    (r'd:/vissim_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+', '<run>'),
    (r'd:/vissim_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s[0-9]+', '<run>'),
]
N_NAMES = [(r'sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+', '<name>'), (r'sdmpc31_v3c3_nc_s[0-9]+', '<name>')]


def n_text(s):
    """amendment 21 section 6.1: lower case, backslashes to '/', the FIRST matching rule only, then run names."""
    s = s.lower().replace('\\\\', '/').replace('\\', '/')
    for rx, rep in N_RULES:
        if re.search(rx, s):
            s = re.sub(rx, rep, s)
            break
    for rx, rep in N_NAMES:
        s = re.sub(rx, rep, s)
    return s


# ---- amendment 21 section 6.2 HARD (text) ----
CONTROL7 = ('n_p_star', 'n_uf_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
H3K = ('selected_objective', 'held_objective', 'warm_start_objective', 'selection_status', 'converged', 'feasible')
V7 = {'/metadata/decision_wall_sec', '/metadata/prediction_wall_sec', '/prediction/wall_sec',
      '/run_provenance/inputs/state_json/path', '/run_provenance/inputs/state_json/sha256',
      '/metadata/run_provenance/inputs/state_json/path', '/metadata/run_provenance/inputs/state_json/sha256'}


def under(g, top):
    return g == top or g.startswith(top + '/') or g.startswith(top + '[')


def hard_group(g):
    if any(under(g, '/' + f) for f in CONTROL7):
        return 'H2'
    if any(under(g, '/metadata/joint_leader_selection/' + k) for k in H3K):
        return 'H3'
    if under(g, '/metadata/sdmpc_state'):
        return 'H4'
    if (under(g, '/metadata/sdmpc_active') or under(g, '/metadata/far_measured_seeded')
            or g.startswith('/metadata/far_rate_est_') or g.startswith('/metadata/head_')
            or under(g, '/prediction') or under(g, '/prediction_error')):
        return 'H5'
    return None


# ---- amendment 21 section 6.3a D (text) ----
def last(g):
    return re.sub(r'\[[^\]]*\]$', '', g.rsplit('/', 1)[-1])


def d_rule(g):
    l = last(g)
    if l.endswith('action_token'):
        return 'D1'
    if (l.endswith('evidence_sha256') or l in ('territory_sha256', 'policy_sha256', 'receipt_sha256',
                                               'lane_plant_manifest_sha256', 'numsim_src_sha256')
            or g.endswith('/physical_ramp_recorded_csv/sha256')):
        return 'D2'
    if (g.startswith('/metadata/') and not g.startswith('/metadata/run_provenance')
            and '/joint_leader_selection/' not in g and l.endswith('sha256')):
        return 'D2b'
    if re.match(r'^/(metadata/)?run_provenance/(imported_modules/[^/]+/sha256|signal_program_sha256/.+|'
                r'numsim_git_commit|numsim_snapshot_commit|run_id)$', g):
        return 'D3'
    m = re.match(r'^/(metadata/)?run_provenance/inputs/([^/]+)/sha256$', g)
    if m and m.group(2) not in ('tuning_json', 'main_vbs_runner', 'watchdog_wrapper', 'state_json'):
        return 'D4'
    m = re.match(r'^/metadata/joint_leader_selection/tangent_derivatives\[\*\]/transformed_source_sha256/(.+)$', g)
    if m and m.group(1) != '<root>/evaluation/controllers/control_area_objective.py':
        return 'D5'
    return None


R3_TEXT = [  # amendment 21 section 6.4: A_K8 R3-01..06, 08 (path patterns as listed in the amendment-22 R3 table)
    ('R3-01', r'/(?:metadata/)?run_provenance/(?:workspace_git_commit|execution_fingerprint_sha256)'),
    ('R3-02', r'/(?:metadata/)?run_provenance/imported_modules(?:[/\[].*)?'),
    ('R3-03', r'/(?:metadata/)?run_provenance/inputs/[^/]+/sha256'),
    ('R3-04', r'/(?:metadata/)?run_provenance/(?:workspace_root|numsim_repo_root)'),
    ('R3-05', r'/(?:metadata/)?run_provenance/inputs/[^/]+/path'),
    ('R3-06', r'/metadata/(?:detector_mapping_resolved_path|native_phase_share_map_path)'),
    ('R3-08', r'/metadata/joint_leader_selection/tangent_derivatives\[\*\]/transformed_source_sha256(?:[/\[].*)?'),
]


def nonhard_class(g, kind):
    """outcome of a differing non-HARD leaf under amendment 21 section 6.4 (allowed = V u R3 u F, minus D).
    kind: 'path' (a path string on both sides), 'hex' (a 64-hex sha on both sides), 'key' (a dict key)."""
    d = d_rule(g)
    if d:
        return 'unclassified(%s)' % d
    if g in V7:
        return 'allowed(V)'
    for rid, rx in R3_TEXT:
        if re.fullmatch(rx, g):
            return 'allowed?(%s; conditions apply)' % rid
    if kind == 'key':
        return 'unclassified(presence)'
    if kind == 'hex':
        return 'allowed(F1)'
    if re.search(r'(?i)(sha256|sha1|sha|token|fingerprint|digest|hash)$', last(g)):
        return 'allowed(F2)'
    return 'unclassified(not allowed)'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def gen(p):
    return re.sub(r'\[\d+\]', '[*]', p)


def walk(x, p, out):
    if isinstance(x, dict):
        for k, v in x.items():
            out.append(('key', p + '/' + n_text(k), k))
            walk(v, p + '/' + n_text(k), out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            walk(v, p + '[%d]' % i, out)
    elif isinstance(x, str):
        out.append(('str', p, x))


def dec_dir(run):
    return '%s/%s/decisions_%s' % (RR, run, run)


def part_a():
    res = {'decisions': [], 'counts': {}}
    off = [(c, t) for c in OFF_T for t in OFF_T[c]]
    first = [(c, OFF_T[c][0]) for c in OFF_T]
    chained = [(c, t) for c, t in off if (c, t) not in first]
    res['counts'] = {'off_decisions': len(off), 'chain_first': first, 'chained': chained,
                     'n_chained': len(chained), 'b1_decisions': sum(len(CHAIN_T[c]) for c in CHAIN_T),
                     'vb_i4_total': sum(len(CHAIN_T[c]) for c in CHAIN_T) + len(off)}
    for c, t in chained:
        ts = OFF_T[c]
        p = ts[ts.index(t) - 1]
        d = dec_dir(CHAINS[c])
        prev_files = {}
        for f in sorted(glob.glob('%s/action_%06d.*' % (d, p))):
            prev_files[os.path.basename(f)[len('action_%06d' % p):]] = sha(f)
        by_sha = {}
        for suf, h in prev_files.items():
            by_sha.setdefault(h, []).append(suf)
        doc = json.load(open('%s/action_%06d.json' % (d, t), encoding='utf-8-sig'))
        items = []
        walk(doc, '', items)
        tag = 'action_%06d' % p
        hits = []
        other_dir_strings = 0
        for kind, path, s in items:
            sl = s.lower()
            if tag in sl:
                m = re.search(re.escape(tag) + r'(\.[a-z_.]+)?', sl)
                hits.append({'path': gen(path), 'via': 'key' if kind == 'key' else 'path',
                             'file': m.group(1) if m and m.group(1) else '',
                             'n_value': n_text(s) if kind == 'str' else None})
            elif kind == 'str' and sl in by_sha:
                hits.append({'path': gen(path), 'via': 'sha', 'file': '|'.join(by_sha[sl])})
            elif kind == 'str' and 'decisions_' in sl:
                other_dir_strings += 1
        rows = []
        for h in hits:
            g = h['path']
            hg = hard_group(g)
            if h['via'] in ('path', 'key'):
                differs = 'yes: location (chain file is under OK2/vb; N(OK2 path) keeps OK2 text)'
            elif h['file'] == '.csv':
                differs = 'no if the chain CSV of the previous decision = record CSV bytes (VB-I1 H1)'
            elif h['file'] in ('.json', '.json.applied'):
                differs = 'yes: bytes (%s)' % ('receipt line 2 = chain CSV path' if h['file'].endswith('applied')
                                                 else 'state path V leaf + wall-clock leaves')
            else:
                differs = 'depends on bytes of %s' % h['file']
            kindc = 'key' if h['via'] == 'key' else ('hex' if h['via'] == 'sha' else 'path')
            outcome = ('HARD ' + hg) if hg else nonhard_class(g, kindc)
            rows.append(dict(h, hard=hg, outcome=outcome, differs=differs))
        must = [r for r in rows if r['differs'].startswith('yes')]
        res['decisions'].append({
            'chain': c, 'T': t, 'prev_T': p, 'prev_files': prev_files, 'n_leaves': len(rows), 'rows': rows,
            'n_must_differ': len(must), 'n_must_differ_hard': sum(1 for r in must if r['hard']),
            'must_differ_hard_paths': sorted({r['path'] for r in must if r['hard']}),
            'n_must_differ_nonhard': sum(1 for r in must if not r['hard']),
            'nonhard_outcomes': sorted({r['outcome'] for r in must if not r['hard']}),
            'other_decision_dir_strings': other_dir_strings})
    # location under N: the record previous action vs any OK2/vb location (amendment 24 :522 write scope)
    rec = '%s/action_%06d.json' % (dec_dir(CHAINS['VB-41']), 3000)
    okp = OK2 + '/vb/VB-41_off/decisions/action_003000.json'
    res['n_location'] = {'record': n_text(rec), 'ok2_vb': n_text(okp), 'equal_after_N': n_text(rec) == n_text(okp)}
    return res


def receipt_facts():
    """the record receipts of the previous decisions of the SDMPC <- SDMPC chained decisions (format facts only)."""
    out = []
    for c, p in (('VB-31', 3000), ('VB-43', 3000), ('VB-41', 3000), ('VB-41w', 900)):
        d = dec_dir(CHAINS[c])
        ack = '%s/action_%06d.json.applied' % (d, p)
        csvp = '%s/action_%06d.csv' % (d, p)
        lines = open(ack, 'rb').read().decode('utf-16').splitlines()
        out.append({'chain': c, 'prev_T': p, 'n_lines': len(lines),
                    'line1_is_prev_T': len(lines) > 0 and float(lines[0]) == float(p),
                    'line2_N': n_text(lines[1]) if len(lines) > 1 else None,
                    'line2_is_record_csv': len(lines) > 1 and os.path.normcase(os.path.abspath(lines[1]))
                    == os.path.normcase(os.path.abspath(csvp)),
                    'line3_is_csv_size': len(lines) > 2 and int(lines[2]) == os.path.getsize(csvp),
                    'receipt_sha256': sha(ack)})
    return out


def part_c():
    rows = []
    holds = {}
    for c, run in CHAINS.items():
        d = dec_dir(run)
        holds[run] = sorted(os.path.basename(f) for f in os.listdir(d) if 'hold' in f.lower())
        for t in CHAIN_T[c]:
            doc = json.load(open('%s/action_%06d.json' % (d, t), encoding='utf-8-sig'))
            md = doc.get('metadata') or {}
            rows.append({'chain': c, 'run': run, 'T': t,
                         'controller_status': md.get('controller_status'),
                         'sdmpc_active': md.get('sdmpc_active', '<absent>'),
                         'prior_discarded': md.get('head_observation_prior_discarded', '<absent>'),
                         'snapshot_is_T': md.get('head_observation_snapshot_sec') == t,
                         'floor_173_p4_keys': sum(1 for k in md if k.startswith('head_discharge_floor_173_p4_')),
                         'exception_keys': sorted(k for k in md if 'exception' in k.lower()),
                         'top_status': doc.get('status', '<absent>') if isinstance(doc.get('status', ''), str)
                         else '<non-string>'})
    summ = {}
    for c in CHAINS:
        rs = [r for r in rows if r['chain'] == c]
        summ[c] = {'n': len(rs),
                   'controller_status': sorted({str(r['controller_status']) for r in rs}),
                   'prior_discarded': sorted({str(r['prior_discarded']) for r in rs}),
                   'snapshot_is_T_all': all(r['snapshot_is_T'] for r in rs),
                   'floor_keys': sorted({r['floor_173_p4_keys'] for r in rs}),
                   'exception_keys': sorted({k for r in rs for k in r['exception_keys']}),
                   'sdmpc_active_by_T': {r['T']: str(r['sdmpc_active']) for r in rs}}
    return {'rows': rows, 'summary': summ, 'hold_files': holds, 'n_decisions': len(rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if os.path.exists(a.out):
        sys.exit('output exists (never reused): ' + a.out)
    out = {'schema': 'vvb-a/v1', 'tool_sha256': sha(os.path.abspath(__file__)), 'A': part_a(),
           'receipts': receipt_facts(), 'C': part_c()}
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, sort_keys=True, default=str)
    for d in out['A']['decisions']:
        print('A %s T=%d<-%d leaves=%d must=%d hard=%d nonhard=%d hard_paths=%s' % (
            d['chain'], d['T'], d['prev_T'], d['n_leaves'], d['n_must_differ'], d['n_must_differ_hard'],
            d['n_must_differ_nonhard'], d['must_differ_hard_paths']), flush=True)
    print('COUNTS', json.dumps(out['A']['counts']), flush=True)
    print('N_LOCATION', json.dumps(out['A']['n_location']), flush=True)
    for r in out['receipts']:
        print('RECEIPT', json.dumps({k: v for k, v in r.items() if k != 'line2_N'}), flush=True)
    for c, s in out['C']['summary'].items():
        print('C', c, json.dumps({k: v for k, v in s.items() if k != 'sdmpc_active_by_T'}), flush=True)
    print('HOLD_FILES', json.dumps(out['C']['hold_files']), flush=True)
    print('VVB_A_DONE', flush=True)


if __name__ == '__main__':
    main()
