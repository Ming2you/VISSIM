"""VerifyVB 3 -- re-make the report r2 table lines (sections 3.4-3.7 and 4.2-4.5) from MY recomputation
(out/vvb3_recalc.json, out/vvb3_extra.json and the hook folders' cand.json hook_sec) and look each line up in the
report text.  Written after the report was read (disclosed); presentation check only -- the numbers come from the
pinned recalculation.  Standard library only.

    python -B vvb3_tables.py   -> out/vvb3_tables.json"""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
REPORT = HERE.parent / 'k92_vb' / 'K92_VB_REPORT.md'
VBR = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2')
KEYS = {'VB-41w': 'vb41w', 'VB-31': 'vb31', 'VB-43': 'vb43', 'VB-41': 'vb41'}
ORDER = ['VB-41w', 'VB-31', 'VB-43', 'VB-41']


def f(x, nd=2):
    if x is None:
        return '없음'
    if isinstance(x, bool):
        return '참' if x else '거짓'
    if isinstance(x, float):
        return ('%.' + str(nd) + 'f') % x
    return str(x)


def hook_sec(chain, arm, T):
    d = VBR / 'chain' / ('%s_%s' % (KEYS[chain], arm)) / 'hook' / ('t%06d' % T)
    vals = []
    for p in sorted(d.iterdir()):
        if p.is_dir() and p.name.startswith('c_'):
            c = json.loads((p / 'cand.json').read_text(encoding='utf-8'))
            if isinstance(c.get('hook_sec'), (int, float)):
                vals.append(float(c['hook_sec']))
    return math.fsum(vals)


def main():
    rc = json.loads((OUT / 'vvb3_recalc.json').read_text(encoding='utf-8'))
    ex = json.loads((OUT / 'vvb3_extra.json').read_text(encoding='utf-8'))
    text = REPORT.read_text(encoding='utf-8')
    lines = set(text.splitlines())
    made = []
    # 3.4 / 3.5 rows
    i2 = {(r['chain'], r['arm'], r['T']): r['ok'] for r in rc['VB_I2']['rows']}
    i7 = {(r['chain'], r['arm'], r['T']): r['ok'] for r in rc['VB_I7']['rows']}
    sel = {(r['chain'], r['arm'], r['T']): r for r in rc['selection']['rows']}
    for (ch, arm, T), s in sel.items():
        hs = hook_sec(ch, arm, T)
        made.append(('3.5', '| %s | %s | %s | %s | %s | %s | %s | %s / %s | %s |' % (
            ch, arm, T, f(i2[(ch, arm, T)]), f(i7[(ch, arm, T)]), f(s['sdmpc_active']), s['status'], s['n_candidates'],
            s['n_match'], f(hs, 1))))
        if arm == 'off':
            made.append(('3.4', '| %s | %s | %s | %s | %s | %s / %s | %s |' % (
                ch, T, f(i2[(ch, arm, T)]), f(i7[(ch, arm, T)]), s['status'], s['n_candidates'], s['n_match'],
                f(hs, 1))))
    # 3.6 rows
    for r in rc['hook_names']['rows']:
        lab = ('ZI %s' % r['arm']) if r['chain'] == 'ZI' else ('%s %s T=%d' % (r['chain'], r['arm'], r['T']))
        g = r.get('same_pid_groups') or {}
        made.append(('3.6', '| %s | %d | %d (%d) | %d | %d (%d) | %d |' % (
            lab, r['n_loaded'], r['n_tokens'], r['n_tokens_with_candidates'], r['n_candidates'], len(g),
            sum(len(v) - 1 for v in g.values()), len(r.get('same_pid_time_overlap') or []))))
    # 3.7 rows
    for name in ORDER:
        for arm in ('off', 'b1'):
            w = ex['walls']['%s/%s' % (name, arm)]
            made.append(('3.7', '| %s | %s | %d | %s | %s | %s |' % (name, arm, w['n'], f(w['sum_h'], 2), f(w['min'], 1),
                                                                    f(w['max'], 1))))
    # 4.2-4.5 rows
    rows = rc['VB_M_rows']
    for name in ORDER:
        rs = sorted([r for r in rows if r['chain'] == name], key=lambda r: (r['T'], {'B1': 0, 'OFF': 1, 'REC': 2}[r['side']]))
        for r in rs:
            last = r.get('select_status') if r['side'] != 'REC' else 'REC: recorder not run (J1 record)'
            made.append(('4.x', '| %s | %s | %s | %s | %s | %s | %s | %s/%s | %s | %s | %s | %s | %s | %s (%s) | %s | %s | '
                                '%s/%s | %s | %s | %s | %s |' % (
                r['T'], r['side'], f(r['p2'], 2), f(r['p3'], 2), f(r['p4'], 2), f(r['floor'], 4), f(r['seed_binding'], 1),
                f(r['groups_carried'], 0), f(r['groups_updated'], 0), f(r['chain_T450'], 2), f(r['chain_max_450'], 2),
                f(r['w_bound_ratio'], 3), f(r['e_out_over_220'], 3), f(r['outw'], 2), f(r['feed4'], 2),
                f(r['feed4_ratio'], 3), f(r['omega'], 2), f(r['phantom_end'], 2), f(r['warm_gt_held']),
                f(r['selected_gt_held']), r.get('selection_status') or '없음',
                f(r.get('csv_same_as_rec')) if r['side'] != 'REC' else '–',
                f(r['wall_run_sec'] if r['side'] != 'REC' else r.get('decision_wall_sec'), 0), last or '–')))
        for c in [c for c in rc['VB_M_chains'] if c['chain'] == name]:
            made.append(('4.x chain', '| %s | %s | %s (%s) | %s | %s | %s | %s / %s | %s / %s | %s | %s | %s |' % (
                c['side'], c['n'], c['n_p3_le_24_5'], f(c['first_T_p3_le_24_5']), c['n_deltas'], c['sign_changes'],
                f(c['mean_abs_dp3'], 2), c['n_k92_w'], c['n_k92_hb'], c['n_warm_gt_held'], c['n_selected_gt_held'],
                f(c.get('first_T_csv_differs')) if c['side'] != 'REC' else '–', c['selection_status_counts'],
                c.get('n_select_selected') if c['side'] != 'REC' else '–')))
    missing = [[s, ln] for s, ln in made if ln not in lines]
    out = {'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'report_sha256': hashlib.sha256(REPORT.read_bytes()).hexdigest(), 'n_lines_made': len(made),
           'n_found': len(made) - len(missing), 'missing': missing,
           'by_section': {s: sum(1 for x, _ in made if x == s) for s in sorted({x for x, _ in made})}}
    (OUT / 'vvb3_tables.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print('VVB3_TABLES made=%d found=%d missing=%d' % (len(made), out['n_found'], len(missing)), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
