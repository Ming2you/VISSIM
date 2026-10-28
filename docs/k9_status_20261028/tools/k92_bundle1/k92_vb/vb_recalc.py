"""K9-2 V-B independent recalculation, VB-I5 (K8_PREDECLARATION_AMENDMENT_32 section 4.6; amendment 24 section 14.1).
Scratch tool, never committed.  Imports the standard library and numpy only: never the V-B driver, the AD32 tools
(vb_lib32, vb_select, the hook), KI, the harness (sa_*, k92_*) or any VBT / GWT8 module.  The rules are written again
here from the text of amendments 24 section 14.1 and 32 sections 2.4, 2.5, 3.4, 3.6; the closed leaf list is not used.

    python -B vb_recalc.py run --vbr <OK2/vb> --dest <file>     recompute and compare with the driver's judge files
    python -B vb_recalc.py selftest                             synthetic self-test, no child process

What is recomputed from the raw files (decision JSON / CSV, run records, hook folders, record folders, arm files,
K92_VALUES.json, the RR record decisions for the REC side):
  (1) the record selection of every decision (section 3.4) -> compared with rec/t<T>/k92_select.json (status,
      candidate count, match count, chosen folder) and the copied record bytes (sha = the chosen candidate's record);
  (2) VB-I2, VB-I3, VB-I4, VB-I6, VB-I7 -> compared with judge/vb_i.json;
  (3) the VB-M1..M9 tables -> compared with judge/vb_m.json (every field of every row).
Equal = numbers within relative 1e-12 of max(1, |a|, |b|), anything else exactly.  Output: {'equal', 'n_compared',
'n_diff', 'diffs'[:200]}.  Exit 0 when it ran (equal or not), 2 on a usage error."""
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
RR = Path(r'D:/VISSIM_runs/20261004_sdmpc31_k8')
TK_VBT = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/vb_e27ceac8')
KB = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1')
VALUES = KB / 'k92_probe_a25' / 'K92_VALUES.json'
NDIR = 'diagnostics/sdmpc_n31_20260924'
S = 1045.1612903225805
LOW_P3 = 24.5
FLIP_MIN = 0.5
REL = 1e-12
ADAPTER_NAME = 'vissim_stackelberg_adapter.py'
SEL_STATES = ('selected', 'no_candidate', 'no_match', 'match_conflict')
CHAIN_KEYS = ('movement:SC109_W_SC108_to_E', 'movement:SC109_W_SC108_to_N_SC16', 'storage:SC108_to_SC109')
WARM = (1, 150, 300, 450, 600, 750, 900, 1050)
WIN = tuple(range(3000, 4501, 150))
SPEC = [  # chain, folder key, run, times, OFF times, OFF tuning (where, rel, sha), B1 tuning
    ('VB-41w', 'vb41w', 'sdmpc31_v3c3_k8j1_s41', WARM, WARM),
    ('VB-31', 'vb31', 'sdmpc31_v3c3_k8j1r_s31', WIN, (3000, 3150)),
    ('VB-43', 'vb43', 'sdmpc31_v3c3_k8j1_s43', WIN, (3000, 3150)),
    ('VB-41', 'vb41', 'sdmpc31_v3c3_k8j1_s41', WIN, (3000, 3150))]
ARM_FILES = {  # name: (base, arm, arm sha)
    'CFG-B1': ('VBT:' + NDIR + '/config_n31_v2.json', 'VBT:' + NDIR + '/config_n31_v2_k92b1.json',
               'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'),
    'SAF-B1': ('VBT:' + NDIR + '/config_n31_v2_stopline_observed_full_k91.json',
               'VBR:arms/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json',
               '65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28')}


def fsha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def jload(p, default=None):
    try:
        with open(p, encoding='utf-8-sig') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def isnum(x):
    return type(x) in (int, float)


def fl(x):
    return float(x) if isnum(x) else None


def t6(T):
    return '%06d' % int(T)


# ================================================================================================ selection (3.4)
def written_sig(doc):
    def fmap(d):
        if not isinstance(d, dict):
            return None
        return {str(k): (float(v) if isnum(v) else ('<non-number>', repr(v))) for k, v in d.items()}
    diag = doc.get('diagnostics') if isinstance(doc.get('diagnostics'), dict) else {}
    seq = diag.get('sdmpc_prediction_sequence')
    fut = None
    if isinstance(seq, dict) and isinstance(seq.get('future'), list):
        fut = [fmap(b.get('green_times')) if isinstance(b, dict) else None for b in seq['future']]
    return fmap(doc.get('green_times')), fmap(doc.get('offsets')), fut


def same_map(a, b):
    return a is not None and b is not None and sorted(a) == sorted(b) and all(a[k] == b[k] for k in a)


def sig_match(cand_sig, w):
    if not isinstance(cand_sig, dict):
        return False
    g, o, fut = w
    if not same_map(cand_sig.get('green_times'), g) or not same_map(cand_sig.get('offsets'), o):
        return False
    cf = cand_sig.get('future_green_times')
    if cf is None or fut is None:
        return cf is None and fut is None
    if len(cf) != len(fut):
        return False
    for x, y in zip(cf, fut):
        if x is None or y is None:
            if x is not None or y is not None:
                return False
        elif not same_map(x, y):
            return False
    return True


def near9(a, b):
    if type(a) is bool or type(b) is bool:
        return a is b
    if isnum(a) and isnum(b):
        a, b = float(a), float(b)
        if a != a or b != b:
            return a != a and b != b
        return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return sorted(a) == sorted(b) and all(near9(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(near9(x, y) for x, y in zip(a, b))
    return a == b


def reselect(hook_dir, action_doc, T):
    hook_dir = Path(hook_dir)
    errs, loaded, cands = [], [], []
    if hook_dir.is_dir():
        errs += sorted(p.name for p in hook_dir.glob('hook_error_*.txt'))
        errs += sorted(p.name for p in hook_dir.glob('hook_setup_error_*.txt'))
        for p in sorted(hook_dir.glob('loaded_*.json')):
            j = jload(p)
            if j is None:
                errs.append(p.name)
                continue
            loaded.append((j.get('argv0'), j.get('recorder_ok')))
        if any(ok is not True for _a, ok in loaded):
            errs.append('recorder_ok')
        for d in sorted(hook_dir.glob('c_*')):
            if not d.is_dir():
                continue
            if not (d / 'cand.json').is_file() or not (d / 'k92_record.json').is_file():
                errs.append(d.name)
                continue
            m = jload(d / 'cand.json') or {}
            nrr = m.get('n_residence_rows')
            m2 = m.get('first_row_start_sec') == float(T) and m.get('dt_sec') == 150.0 and type(nrr) is int and nrr > 0
            cands.append({'folder': d.name, 'match': sig_match(m.get('signature'), written_sig(action_doc)) and m2,
                          'key': (bool(m.get('is_ad')), m.get('time_ns') or 0, m.get('pid') or 0, m.get('seq') or 0)})
    out = {'n_candidates': len(cands), 'n_match': sum(1 for c in cands if c['match']), 'chosen': None}
    hits = sorted((c for c in cands if c['match']), key=lambda c: c['key'])
    if errs:
        out['status'] = 'hook_error'
    elif not [a for a, _ok in loaded if a == ADAPTER_NAME]:
        out['status'] = 'no_hook'
    elif not cands:
        out['status'] = 'no_candidate'
    elif not hits:
        out['status'] = 'no_match'
    else:
        recs = [jload(hook_dir / c['folder'] / 'k92_record.json') or {} for c in hits]
        if all(near9(r.get('blocks'), recs[0].get('blocks')) and near9(r.get('horizon'), recs[0].get('horizon'))
               for r in recs[1:]):
            out['status'] = 'selected'
            out['chosen'] = hits[0]['folder']
            out['chosen_record_sha256'] = fsha(hook_dir / hits[0]['folder'] / 'k92_record.json')
        else:
            out['status'] = 'match_conflict'
    return out


# ================================================================================================ VB-I
def i2_of(doc, names, T, rc, dfc, warm_exception=None):
    md = (doc or {}).get('metadata') if isinstance((doc or {}).get('metadata'), dict) else {}
    chk = {}
    chk['exit0'] = rc == 0
    chk['no_hold_file'] = all('hold' not in n.lower() for n in names)
    chk['no_error_file'] = all(not n.endswith('.error.txt') for n in names)
    chk['no_decision_failed'] = dfc == 0
    chk['controller_status_ok'] = md.get('controller_status') == 'ok'
    chk['no_exception_key'] = all('exception' not in k.lower() for k in md)
    snap = md.get('head_observation_snapshot_sec')
    chk['snapshot_is_T'] = isnum(snap) and float(snap) == float(T)
    pd = md.get('head_observation_prior_discarded')
    if warm_exception is None:
        chk['prior_discarded_0'] = isnum(pd) and float(pd) == 0.0
    else:
        key, t1 = warm_exception
        t1md = (t1 or {}).get('metadata') or {}
        chk['prior_discarded_exception'] = (isnum(pd) and float(pd) == 1.0 and isnum(md.get(key))
                                            and float(md[key]) == S and isnum(t1md.get(key)) and float(t1md[key]) == S)
    return {'ok': all(chk.values()) and doc is not None, 'checks': chk, 'output_present': doc is not None}


def i7_of(hook_dir, rec_dir):
    hook_dir = Path(hook_dir)
    lo = [jload(p) or {} for p in sorted(hook_dir.glob('loaded_*.json'))] if hook_dir.is_dir() else []
    n_ad = sum(1 for j in lo if j.get('argv0') == ADAPTER_NAME)
    errs = (list(hook_dir.glob('hook_error_*.txt')) + list(hook_dir.glob('hook_setup_error_*.txt'))) \
        if hook_dir.is_dir() else []
    cds = [d for d in hook_dir.glob('c_*') if d.is_dir()] if hook_dir.is_dir() else []
    bad = [d for d in cds if not ((d / 'cand.json').is_file() and (d / 'k92_record.json').is_file())]
    st = (jload(Path(rec_dir) / 'k92_select.json') or {}).get('status')
    chk = {'c1_loaded': len(lo) > 0 and n_ad == 1 and all(j.get('recorder_ok') is True for j in lo),
           'c2_no_hook_error': len(errs) == 0, 'c3_candidates_complete': len(bad) == 0,
           'c4_select_status': st in SEL_STATES}
    return {'ok': all(chk.values()), 'checks': chk, 'n_loaded': len(lo), 'n_adapter_loaded': n_ad,
            'n_candidates': len(cds), 'status': st}


def tree_json_diff(a, b, p=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in a and k in b:
                out += tree_json_diff(a[k], b[k], p + '/' + k)
            else:
                out.append(p + '/' + k)
    elif type(a) is not type(b) or a != b:
        out.append(p)
    return out


def i3_of(vbr):
    res = {}
    for name, (base, arm, want) in ARM_FILES.items():
        def path(spec):
            where, rel = spec.split(':', 1)
            return (TK_VBT if where == 'VBT' else Path(vbr)) / rel
        bp, ap = path(base), path(arm)
        if not ap.is_file():
            res[name] = {'ok': False}
            continue
        A, B = jload(bp), jload(ap)
        diff = sorted(tree_json_diff(A, B))
        u = (B or {}).get('urban') or {}
        ev_ok = {}
        for k, node in (('w', u.get('sc109w_through_saturation')), ('hb', (u.get('capacity') or {}).get('head_floor_seed'))):
            rel = (node or {}).get('evidence')
            f = TK_VBT / rel if isinstance(rel, str) else None
            ev_ok[k] = f is not None and f.is_file() and fsha(f) == (node or {}).get('evidence_sha256')
        two = diff == ['/urban/capacity/head_floor_seed', '/urban/sc109w_through_saturation']
        res[name] = {'two_paths': two, 'file_sha_ok': fsha(ap) == want, 'evidence_ok': ev_ok,
                     'ok': two and fsha(ap) == want and all(ev_ok.values())}
    return res


# ================================================================================================ VB-M
def doc_fields(doc, fkey):
    md = doc.get('metadata') if isinstance(doc.get('metadata'), dict) else {}
    j = md.get('joint_leader_selection') if isinstance(md.get('joint_leader_selection'), dict) else {}
    gt = doc.get('green_times') if isinstance(doc.get('green_times'), dict) else {}
    ws, ho, so = fl(j.get('warm_start_objective')), fl(j.get('held_objective')), fl(j.get('selected_objective'))
    return {'p2': fl(gt.get('SC109_p2')), 'p3': fl(gt.get('SC109_p3')), 'p4': fl(gt.get('SC109_p4')),
            'floor': fl(md.get(fkey)), 'floor_keys_n': len([k for k in md if k.startswith('head_discharge_floor_173_p4_')]),
            'seed_binding': fl(md.get('k92_hb_seed_binding')),
            'groups_carried': fl(md.get('head_observation_groups_carried')),
            'groups_updated': fl(md.get('head_observation_groups_updated')),
            'k92_w': 'k92_w' in md, 'k92_hb': 'k92_hb' in md,
            'selection_status': j.get('selection_status') if j else None, 'omega': so,
            'warm_gt_held': None if ws is None or ho is None else ws > ho,
            'selected_gt_held': None if so is None or ho is None else so > ho,
            'decision_wall_sec': fl(md.get('decision_wall_sec'))}


def rec_fields(rec_dir, T):
    import numpy as np
    rec_dir = Path(rec_dir)
    sel = jload(rec_dir / 'k92_select.json') or {}
    names = ('chain_T450', 'chain_blocks', 'chain_max_450', 'w_bound_ratio', 'e_out_over_220', 'outw', 'feed4',
             'feed4_ratio', 'phantom_end')
    if sel.get('status') != 'selected':
        out = dict.fromkeys(names)
        out.update(none_reason='record:%s' % sel.get('status'), n_states=None)
        return out
    r = jload(rec_dir / 'k92_record.json') or {}
    h = r.get('horizon') or {}
    bl = (r.get('blocks') or [])[:3]
    mx = None
    z_path = rec_dir / 'k92_series.npz'
    if z_path.is_file():
        with np.load(z_path, allow_pickle=True) as z:
            keys = list(map(str, z['keys'].tolist()))
            if all(k in keys for k in CHAIN_KEYS):
                cols = [keys.index(k) for k in CHAIN_KEYS]
                te = z['t_end'].astype(float)
                sub = z['model'][:, cols].astype(float)
                rows = [i for i in range(te.shape[0]) if T < te[i] <= T + 450.0 and np.all(np.isfinite(sub[i]))]
                if rows:
                    mx = max(math.fsum(float(x) for x in sub[i]) for i in rows)
    b, d = h.get('w_capacity_bound_steps'), h.get('w_steps_with_departures')
    ow, f4 = fl(h.get('outw_veh_h_450')), fl(h.get('feed4_veh_h_450'))
    ch = sel.get('chosen') or {}
    cj = jload(Path(sel.get('hook_dir') or '') / str(ch.get('folder')) / 'cand.json') or {}
    return {'chain_T450': fl(h.get('m1_chain_T450')), 'chain_blocks': [fl(x.get('chain_sum')) for x in bl],
            'chain_max_450': mx, 'w_bound_ratio': float(b) / float(d) if isnum(b) and isnum(d) and d != 0 else None,
            'e_out_over_220': fl(h.get('e_out_max_over_220')), 'outw': ow, 'feed4': f4,
            'feed4_ratio': f4 / ow if ow is not None and f4 is not None and ow > 0 else None,
            'phantom_end': fl(h.get('phantom_end_450')), 'none_reason': None, 'n_states': cj.get('n_states')}


def m_rows(vbr, fkeys):
    rows = []
    rec_sha = {}
    for chain, key, run, times, off_times in SPEC:
        dec_rr = RR / run / ('decisions_' + run)
        for side in ('REC', 'OFF', 'B1'):
            for T in (off_times if side == 'OFF' else times):
                if side == 'REC':
                    jp, cp, wall = dec_rr / ('action_%s.json' % t6(T)), dec_rr / ('action_%s.csv' % t6(T)), None
                else:
                    base = Path(vbr) / 'chain' / ('%s_%s' % (key, side.lower()))
                    jp, cp = base / 'dec' / ('action_%s.json' % t6(T)), base / 'dec' / ('action_%s.csv' % t6(T))
                    wall = fl((jload(base / 'dec' / ('run_t%s.json' % t6(T))) or {}).get('wall_sec'))
                doc = jload(jp) or {}
                r = dict(chain=chain, side=side, T=T)
                r.update(doc_fields(doc, fkeys[run]))
                doc = None
                r['csv_sha256'] = fsha(cp)
                r['wall_run_sec'] = wall
                if side == 'REC':
                    rec_sha[(chain, T)] = r['csv_sha256']
                    r.update(dict.fromkeys(('chain_T450', 'chain_blocks', 'chain_max_450', 'w_bound_ratio',
                                            'e_out_over_220', 'outw', 'feed4', 'feed4_ratio', 'phantom_end')),
                             none_reason='REC: recorder not run (J1 record)', n_states=None)
                else:
                    rd = Path(vbr) / 'chain' / ('%s_%s' % (key, side.lower())) / 'rec' / ('t' + t6(T))
                    r.update(rec_fields(rd, T))
                    r['select_status'] = (jload(rd / 'k92_select.json') or {}).get('status')
                rows.append(r)
    for r in rows:
        if r['side'] != 'REC':
            r['csv_same_as_rec'] = r['csv_sha256'] == rec_sha[(r['chain'], r['T'])]
        if r['side'] == 'B1' and r['chain'] == 'VB-41w':
            base = [x for x in rows if x['side'] == 'REC' and x['chain'] == 'VB-41w' and x['T'] == r['T']][0]['floor']
            r['floor_eq_max_rec_seed'] = r['floor'] is not None and r['floor'] == (S if base is None else max(base, S))
    return rows


def m_chains(rows):
    out = []
    for chain, _k, _r, _t, _o in SPEC:
        for side in ('REC', 'OFF', 'B1'):
            rs = sorted([r for r in rows if r['chain'] == chain and r['side'] == side], key=lambda r: r['T'])
            seq = [(r['T'], r['p3']) for r in rs]
            ds = [b[1] - a[1] for a, b in zip(seq, seq[1:])
                  if a[1] is not None and b[1] is not None and (b[0] - a[0]) == (149 if a[0] == 1 else 150)]
            sig = [1 if d > 0 else -1 for d in ds if abs(d) >= FLIP_MIN]
            flips = len([1 for i in range(1, len(sig)) if sig[i] != sig[i - 1]])
            low = [T for T, v in seq if v is not None and v <= LOW_P3]
            counts = {}
            for r in rs:
                counts[str(r['selection_status'])] = counts.get(str(r['selection_status']), 0) + 1
            diff_T = [r['T'] for r in rs if side != 'REC' and not r['csv_same_as_rec']]
            out.append({'chain': chain, 'side': side, 'n': len(rs), 'n_p3_le_24_5': len(low),
                        'first_T_p3_le_24_5': low[0] if low else None, 'n_deltas': len(ds), 'sign_changes': flips,
                        'mean_abs_dp3': math.fsum(map(abs, ds)) / len(ds) if ds else None,
                        'n_k92_w': len([r for r in rs if r['k92_w']]), 'n_k92_hb': len([r for r in rs if r['k92_hb']]),
                        'selection_status_counts': counts,
                        'n_warm_gt_held': len([r for r in rs if r['warm_gt_held'] is True]),
                        'n_selected_gt_held': len([r for r in rs if r['selected_gt_held'] is True]),
                        'first_T_csv_differs': (diff_T[0] if diff_T else None) if side != 'REC' else None,
                        'n_select_selected': len([r for r in rs if r.get('select_status') == 'selected'])})
    return out


# ================================================================================================ compare
def same(a, b):
    if type(a) is bool or type(b) is bool:
        return a is b
    if isnum(a) and isnum(b):
        a, b = float(a), float(b)
        if a != a or b != b:
            return a != a and b != b
        return abs(a - b) <= REL * max(1.0, abs(a), abs(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return sorted(a) == sorted(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


class Cmp:
    def __init__(self):
        self.n = 0
        self.diffs = []

    def eq(self, where, mine, theirs):
        self.n += 1
        if not same(mine, theirs):
            self.diffs.append({'where': where, 'recalc': mine, 'driver': theirs})


def run(vbr, dest=None):
    vbr = Path(vbr)
    values = jload(VALUES) or {}
    fkeys = values['p0_2']['f_expected_floor_keys']
    vb_i = jload(vbr / 'judge' / 'vb_i.json') or {}
    vb_m = jload(vbr / 'judge' / 'vb_m.json') or {}
    C = Cmp()
    drows = {(r['chain'], r['arm'], r['T']): r for r in vb_i.get('rows') or []}
    d4 = {(r['chain'], r['arm'], r['T']): r for r in vb_i.get('VB_I4') or []}
    plan = [(c, k, r, a, T) for a in ('off', 'b1') for c, k, r, times, off in SPEC for T in (off if a == 'off' else times)]
    C.eq('plan_n', len(plan), 55)
    t1 = {}
    i6_docs = {}
    for chain, key, run_name, arm, T in plan:
        base = vbr / 'chain' / ('%s_%s' % (key, arm))
        jp = base / 'dec' / ('action_%s.json' % t6(T))
        doc = jload(jp)
        hook, rec = base / 'hook' / ('t' + t6(T)), base / 'rec' / ('t' + t6(T))
        tag = '%s/%s/T%s' % (chain, arm, t6(T))
        # (1) selection
        sel = reselect(hook, doc or {}, T)
        dsel = jload(rec / 'k92_select.json') or {}
        C.eq(tag + '/select/status', sel['status'], dsel.get('status'))
        C.eq(tag + '/select/n_candidates', sel['n_candidates'], dsel.get('n_candidates'))
        C.eq(tag + '/select/n_match', sel['n_match'], dsel.get('n_match'))
        C.eq(tag + '/select/chosen', sel['chosen'], (dsel.get('chosen') or {}).get('folder'))
        if sel['status'] == 'selected':
            C.eq(tag + '/select/record_sha', sel['chosen_record_sha256'], fsha(rec / 'k92_record.json')
                 if (rec / 'k92_record.json').is_file() else None)
            C.eq(tag + '/select/record_sha_in_select', sel['chosen_record_sha256'],
                 (dsel.get('chosen') or {}).get('record_sha256'))
        # (2) VB-I4 / VB-I2 / VB-I7
        pres = jp.is_file() and (base / 'dec' / ('action_%s.csv' % t6(T))).is_file()
        C.eq(tag + '/VB_I4', pres, bool((d4.get((chain, arm, T)) or {}).get('json')) and
             bool((d4.get((chain, arm, T)) or {}).get('csv')))
        names = sorted(p.name for p in (base / 'dec').iterdir() if p.is_file() and t6(T) in p.name) \
            if (base / 'dec').is_dir() else []
        rr = jload(base / 'dec' / ('run_t%s.json' % t6(T))) or {}
        dfc = 0
        for ext in ('.stdout.txt', '.stderr.txt'):
            p = base / 'dec' / ('action_%s%s' % (t6(T), ext))
            if p.is_file():
                dfc += sum(1 for line in p.read_text(encoding='utf-8', errors='replace').splitlines()
                           if 'DECISION_FAILED' in line)
        warm = None
        if chain == 'VB-41w' and arm == 'b1':
            if T == 1:
                t1[key] = doc
            if T == 150:
                warm = (fkeys[run_name], t1.get(key))
        i2 = i2_of(doc, names, T, rr.get('exit'), dfc, warm)
        dr = drows.get((chain, arm, T)) or {}
        C.eq(tag + '/VB_I2/ok', i2['ok'], (dr.get('VB_I2') or {}).get('ok'))
        C.eq(tag + '/VB_I2/checks', i2['checks'], (dr.get('VB_I2') or {}).get('checks'))
        i7 = i7_of(hook, rec)
        C.eq(tag + '/VB_I7/ok', i7['ok'], (dr.get('VB_I7') or {}).get('ok'))
        C.eq(tag + '/VB_I7/checks', i7['checks'], (dr.get('VB_I7') or {}).get('checks'))
        for k in ('n_loaded', 'n_adapter_loaded', 'n_candidates', 'status'):
            C.eq(tag + '/VB_I7/' + k, i7[k], (dr.get('VB_I7') or {}).get(k))
        if arm == 'b1':
            md = (doc or {}).get('metadata') or {}
            ks = sorted(k for k in md if k.startswith('head_discharge_floor_173_p4_'))
            i6_docs.setdefault(chain, []).append((T, ks, fl(md.get(ks[0])) if len(ks) == 1 else None,
                                                  fkeys[run_name]))
        doc = None
    # VB-I6
    for chain, rows6 in i6_docs.items():
        vals = [v for _T, _ks, v, _f in rows6]
        okk = all(len(ks) == 1 and ks[0] == f and v is not None for _T, ks, v, f in rows6)
        nd = all(a is not None and b is not None and b >= a for a, b in zip(vals, vals[1:]))
        ok6 = okk and nd
        d6 = (vb_i.get('VB_I6') or {}).get(chain) or {}
        if chain == 'VB-41w':
            byT = {T: v for T, _ks, v, _f in rows6}
            w = byT.get(150) is not None and byT.get(1) == S and byT.get(150) == S
            ok6 = ok6 and w
            C.eq(chain + '/VB_I6/t150_eq_t1_eq_seed', w, d6.get('t150_eq_t1_eq_seed'))
        C.eq(chain + '/VB_I6/ok', ok6, d6.get('ok'))
        C.eq(chain + '/VB_I6/non_decreasing', nd, d6.get('non_decreasing'))
        C.eq(chain + '/VB_I6/values', vals, [r.get('value') for r in d6.get('rows') or []])
    # VB-I3
    i3 = i3_of(vbr)
    for name, v in i3.items():
        dv = (vb_i.get('VB_I3') or {}).get(name) or {}
        C.eq('VB_I3/%s/ok' % name, v['ok'], dv.get('ok'))
        C.eq('VB_I3/%s/two_paths' % name, v.get('two_paths'), dv.get('two_paths'))
        C.eq('VB_I3/%s/file_sha_ok' % name, v.get('file_sha_ok'), dv.get('file_sha_ok'))
        C.eq('VB_I3/%s/evidence' % name, v.get('evidence_ok'),
             {k: x.get('file_sha_ok') for k, x in (dv.get('evidence') or {}).items()})
    all_i = {'VB_I2': all(((drows.get((c, a, T)) or {}).get('VB_I2') or {}).get('ok') for c, _k, _r, a, T in plan)}
    C.eq('VB_I2_ok', all_i['VB_I2'], vb_i.get('VB_I2_ok'))
    # (3) VB-M
    rows = m_rows(vbr, fkeys)
    dm = {(r['chain'], r['side'], r['T']): r for r in vb_m.get('rows') or []}
    C.eq('M/n_rows', len(rows), len(vb_m.get('rows') or []))
    for r in rows:
        d = dm.get((r['chain'], r['side'], r['T'])) or {}
        C.eq('M/%s/%s/T%s/keys' % (r['chain'], r['side'], t6(r['T'])), sorted(r), sorted(d))
        for k, v in r.items():
            C.eq('M/%s/%s/T%s/%s' % (r['chain'], r['side'], t6(r['T']), k), v, d.get(k))
    chains = m_chains(rows)
    dc = {(r['chain'], r['side']): r for r in vb_m.get('chains') or []}
    C.eq('MC/n', len(chains), len(vb_m.get('chains') or []))
    for r in chains:
        d = dc.get((r['chain'], r['side'])) or {}
        C.eq('MC/%s/%s/keys' % (r['chain'], r['side']), sorted(r), sorted(d))
        for k, v in r.items():
            C.eq('MC/%s/%s/%s' % (r['chain'], r['side'], k), v, d.get(k))
    res = {'schema': 'k92vb-recalc/v1', 'tool_sha256': fsha(__file__), 'vbr': str(vbr), 'equal': not C.diffs,
           'n_compared': C.n, 'n_diff': len(C.diffs), 'diffs': C.diffs[:200],
           'inputs': {'vb_i_sha256': fsha(vbr / 'judge' / 'vb_i.json') if (vbr / 'judge' / 'vb_i.json').is_file() else None,
                      'vb_m_sha256': fsha(vbr / 'judge' / 'vb_m.json') if (vbr / 'judge' / 'vb_m.json').is_file() else None,
                      'k92_values_sha256': fsha(VALUES)}}
    if dest is not None:
        dest = Path(dest)
        if dest.exists():
            raise SystemExit('output exists (never reused): %s' % dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + '\n', encoding='utf-8')
    return res


# ================================================================================================ self-test (4.6)
def selftest():
    """Synthetic VBR: chains VB-41w (T=1, 150, 300) and VB-31 (T=3000, 3150, 3300) only, one arm (B1) and REC.  The
    hand expectations below are written from the rules, not from this module's output."""
    import numpy as np
    here = Path(__file__).resolve().parent
    root = here / 'selftest' / 'syn_recalc'
    if root.exists():
        shutil.rmtree(root)
    rrs = root / 'rr'
    vbr = root / 'vbr'
    g = {1: 30.0, 150: 24.0, 300: 26.0, 3000: 25.0, 3150: 24.5, 3300: 30.0}
    off = {3000: 0.0, 3150: 1.0, 3300: 2.0}

    def act(T, p3, floor=None, fkey='head_discharge_floor_173_p4_301ceabb95f116fa', fut=True, rec=False):
        md = {'controller_status': 'ok', 'head_observation_prior_discarded': 0.0,
              'head_observation_snapshot_sec': float(T), 'head_observation_groups_carried': 2.0,
              'head_observation_groups_updated': 1.0, 'decision_wall_sec': 10.0 + T / 1000.0}
        if floor is not None:
            md[fkey] = floor
            md['k92_hb_seed_binding'] = 1.0
        if not rec:
            md['k92_w'] = {'x': 1}
            md['k92_hb'] = {'x': 1}
        if T >= 900:
            md['sdmpc_active'] = True
            md['joint_leader_selection'] = {'selection_status': 'best_observed_feasible_sdmpc',
                                            'selected_objective': 100.0 + T / 1000.0, 'held_objective': 101.0,
                                            'warm_start_objective': 102.0 if T == 3150 else 99.0}
        d = {'green_times': {'SC109_p2': 20.0, 'SC109_p3': p3, 'SC109_p4': 15.0}, 'offsets': {'SC109': off.get(T, 0.0)},
             'metadata': md}
        if fut and T >= 900:
            d['diagnostics'] = {'sdmpc_prediction_sequence': {'future': [{'green_times': {'SC109_p3': p3 + 1}}]}}
        return d

    def put(p, obj):
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(obj, bytes):
            p.write_bytes(obj)
        else:
            p.write_text(json.dumps(obj), encoding='utf-8')
    spec = [('VB-41w', 'vb41w', 'sdmpc31_v3c3_k8j1_s41', (1, 150, 300)),
            ('VB-31', 'vb31', 'sdmpc31_v3c3_k8j1r_s31', (3000, 3150, 3300))]
    fkeys = {'sdmpc31_v3c3_k8j1_s41': 'head_discharge_floor_173_p4_301ceabb95f116fa',
             'sdmpc31_v3c3_k8j1r_s31': 'head_discharge_floor_173_p4_1170360c34e5b57b'}
    for chain, key, run_name, times in spec:
        for T in times:
            dd = rrs / run_name / ('decisions_' + run_name)
            put(dd / ('action_%s.json' % t6(T)), act(T, g[T] + (0.0 if T != 3300 else 1.0), rec=True))
            put(dd / ('action_%s.csv' % t6(T)), b'rec,%d\r\n' % T)
            base = vbr / 'chain' / ('%s_b1' % key)
            fl_ = S if chain == 'VB-41w' else 1100.0 + (T - 3000) / 150.0
            doc = act(T, g[T], floor=fl_, fkey=fkeys[run_name])
            if chain == 'VB-41w' and T == 150:
                doc['metadata']['head_observation_prior_discarded'] = 1.0
            put(base / 'dec' / ('action_%s.json' % t6(T)), doc)
            put(base / 'dec' / ('action_%s.csv' % t6(T)), b'rec,%d\r\n' % T if T != 3300 else b'b1,3300\r\n')
            put(base / 'dec' / ('run_t%s.json' % t6(T)), {'exit': 0, 'wall_sec': 50.0 + T / 100.0})
            put(base / 'dec' / ('action_%s.stdout.txt' % t6(T)), b'ok\n')
            hook = base / 'hook' / ('t' + t6(T))
            put(hook / 'loaded_10.json', {'argv0': ADAPTER_NAME, 'recorder_ok': True})
            rec_dir = base / 'rec' / ('t' + t6(T))
            if T >= 900:
                put(hook / 'loaded_11.json', {'argv0': 'sdmpc_tangent_worker.py', 'recorder_ok': True})
                for seq, (ad, shift) in enumerate(((True, 0.0), (False, 0.0), (False, 5.0)), start=1):
                    c = hook / ('c_11_%04d' % seq)
                    p3 = g[T] + shift
                    put(c / 'cand.json', {'seq': seq, 'pid': 11, 'is_ad': ad, 'time_ns': 1000 + seq,
                                          'first_row_start_sec': float(T), 'dt_sec': 150.0, 'n_residence_rows': 9,
                                          'n_states': 3, 'signature': {
                                              'green_times': {'SC109_p2': 20.0, 'SC109_p3': p3, 'SC109_p4': 15.0},
                                              'offsets': {'SC109': off[T]},
                                              'future_green_times': [{'SC109_p3': p3 + 1}]}})
                    hz = {'m1_chain_T450': 12.0 + seq, 'outw_veh_h_450': 4.0, 'feed4_veh_h_450': 1.0,
                          'e_out_max_over_220': 0.5, 'phantom_end_450': 3.0, 'w_capacity_bound_steps': 2,
                          'w_steps_with_departures': 8}
                    if seq <= 2:
                        hz['m1_chain_T450'] = 12.0
                    put(c / 'k92_record.json', {'blocks': [{'chain_sum': 1.0}, {'chain_sum': 2.0}, {'chain_sum': 3.0}],
                                                'horizon': hz})
                    t_end = np.array([T + 50.0 * i for i in range(1, 10)] + [T + 500.0])
                    model = np.ones((10, 3)) * np.arange(1, 11)[:, None]
                    model[2, 1] = np.nan
                    np.savez_compressed(c / 'k92_series.npz', keys=np.array(list(CHAIN_KEYS), dtype=object),
                                        t_end=t_end, model=model)
                rec_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(hook / 'c_11_0002' / 'k92_record.json', rec_dir / 'k92_record.json')
                shutil.copy2(hook / 'c_11_0002' / 'k92_series.npz', rec_dir / 'k92_series.npz')
                put(rec_dir / 'k92_select.json', {'status': 'selected', 'n_candidates': 3, 'n_match': 2,
                                                  'hook_dir': str(hook), 'chosen': {
                                                      'folder': 'c_11_0002',
                                                      'record_sha256': fsha(rec_dir / 'k92_record.json')}})
            else:
                put(rec_dir / 'k92_select.json', {'status': 'no_candidate', 'n_candidates': 0, 'n_match': 0,
                                                  'hook_dir': str(hook), 'chosen': None})
    checks = {}
    # (1) selection by hand: the two matching candidates (AD seq 1, non-AD seq 2) carry the same record -> selected,
    # non-AD first -> c_11_0002; seq 3 has p3 + 5 -> no match
    b31 = vbr / 'chain' / 'vb31_b1'
    d3000 = jload(b31 / 'dec' / 'action_003000.json')
    s1 = reselect(b31 / 'hook' / 't003000', d3000, 3000)
    checks['sel_selected_nonad'] = s1['status'] == 'selected' and s1['chosen'] == 'c_11_0002' and s1['n_match'] == 2
    checks['sel_no_candidate'] = reselect(vbr / 'chain' / 'vb41w_b1' / 'hook' / 't000001',
                                          jload(vbr / 'chain' / 'vb41w_b1' / 'dec' / 'action_000001.json'), 1)[
        'status'] == 'no_candidate'
    # (3) M rows by hand (REC paths patched to the synthetic RR folder)
    global RR, SPEC
    real_rr, real_spec = RR, SPEC
    RR = rrs
    SPEC = [(c, k, r, t, ()) for c, k, r, t in spec]
    try:
        rows = m_rows(vbr, fkeys)
    except Exception as exc:  # noqa: BLE001
        rows = []
        checks['m_rows_error'] = repr(exc)
    finally:
        RR, SPEC = real_rr, real_spec
    B = {(r['chain'], r['T']): r for r in rows if r['side'] == 'B1'}
    checks['rows_built'] = len(B) == 6 and len([r for r in rows if r['side'] == 'REC']) == 6
    if B:
        r3000 = B[('VB-31', 3000)]
        # chain max: rows with t_end in (3000, 3450] and all keys finite: t_end 3050..3450 = rows 0..8, row 2 has NaN
        # -> sums 3*(i+1) for i in {0,1,3..8} -> max 27.0
        checks['m5_chain_max'] = r3000['chain_max_450'] == 27.0
        checks['m5_chain_T450'] = r3000['chain_T450'] == 12.0 and r3000['chain_blocks'] == [1.0, 2.0, 3.0]
        checks['m5_ratio'] = r3000['w_bound_ratio'] == 0.25 and r3000['e_out_over_220'] == 0.5
        checks['m6'] = r3000['outw'] == 4.0 and r3000['feed4'] == 1.0 and r3000['feed4_ratio'] == 0.25 and \
            r3000['omega'] == 103.0
        checks['m7'] = r3000['warm_gt_held'] is False and r3000['selected_gt_held'] is True and \
            B[('VB-31', 3150)]['warm_gt_held'] is True
        checks['m1'] = (B[('VB-31', 3150)]['p3'], B[('VB-41w', 150)]['p3']) == (24.5, 24.0)
        checks['m9_csv'] = B[('VB-31', 3000)]['csv_same_as_rec'] is True and B[('VB-31', 3300)]['csv_same_as_rec'] is False
        checks['m4_warm'] = B[('VB-41w', 1)]['floor'] == S and B[('VB-41w', 300)]['floor_eq_max_rec_seed'] is True
        checks['none_no_candidate'] = B[('VB-41w', 1)]['none_reason'] == 'record:no_candidate'
        ch = {(c['chain'], c['side']): c for c in m_chains(rows)}
        c31 = ch[('VB-31', 'B1')]
        # p3 25.0, 24.5, 30.0: deltas -0.5, +5.5 -> both |d| >= 0.5 -> one flip; mean |d| = 3.0; p3 <= 24.5 at 3150
        checks['m2_m3'] = (c31['n_p3_le_24_5'], c31['first_T_p3_le_24_5'], c31['sign_changes'], c31['mean_abs_dp3'],
                           c31['first_T_csv_differs']) == (1, 3150, 1, 3.0, 3300)
        cw = ch[('VB-41w', 'B1')]
        # 30.0 -> 24.0 -> 26.0 (T 1 -> 150 counts as consecutive): deltas -6, +2 -> one flip; 150 is <= 24.5
        checks['m3_warm'] = (cw['n_deltas'], cw['sign_changes'], cw['n_p3_le_24_5'], cw['first_T_p3_le_24_5']) == \
            (2, 1, 1, 150)
        # mutations are caught by the comparison: one decision JSON value (B1 VB-31 T=3000 p3) changed on disk, the
        # rows recomputed and compared field by field with the rows before -> exactly that one field differs
        jd = jload(b31 / 'dec' / 'action_003000.json')
        jd['green_times']['SC109_p3'] = 25.0 + 1e-6
        put(b31 / 'dec' / 'action_003000.json', jd)
        RR, SPEC = rrs, [(c, k, r, t, ()) for c, k, r, t in spec]
        try:
            rows_m = m_rows(vbr, fkeys)
        finally:
            RR, SPEC = real_rr, real_spec
        Cm = Cmp()
        before = {(r['chain'], r['side'], r['T']): r for r in rows}
        for r in rows_m:
            for k, v in r.items():
                Cm.eq('%s/%s/%s/%s' % (r['chain'], r['side'], r['T'], k), v, before[(r['chain'], r['side'], r['T'])][k])
        checks['mut_value'] = [d['where'] for d in Cm.diffs] == ['VB-31/B1/3000/p3']
        # signature change -> no_match
        cj = jload(b31 / 'hook' / 't003150' / 'c_11_0002' / 'cand.json')
        cj['signature']['offsets']['SC109'] = 9.0
        put(b31 / 'hook' / 't003150' / 'c_11_0002' / 'cand.json', cj)
        cj1 = jload(b31 / 'hook' / 't003150' / 'c_11_0001' / 'cand.json')
        cj1['signature']['offsets']['SC109'] = 9.0
        put(b31 / 'hook' / 't003150' / 'c_11_0001' / 'cand.json', cj1)
        checks['mut_signature'] = reselect(b31 / 'hook' / 't003150', jload(b31 / 'dec' / 'action_003150.json'),
                                           3150)['status'] == 'no_match'
        # record number change -> conflict between the two matches (3300: change seq 1 only)
        rj = jload(b31 / 'hook' / 't003300' / 'c_11_0001' / 'k92_record.json')
        rj['horizon']['outw_veh_h_450'] = 4.1
        put(b31 / 'hook' / 't003300' / 'c_11_0001' / 'k92_record.json', rj)
        checks['mut_record'] = reselect(b31 / 'hook' / 't003300', jload(b31 / 'dec' / 'action_003300.json'),
                                        3300)['status'] == 'match_conflict'
        # Cmp catches a differing driver value
        C = Cmp()
        C.eq('x', 1.0, 1.0 + 1e-13)
        C.eq('y', {'a': 1}, {'a': 1})
        ok_eq = not C.diffs
        C.eq('z', 1.0, 1.0001)
        checks['cmp'] = ok_eq and len(C.diffs) == 1
    # VB-I2 by hand
    checks['i2_true'] = i2_of(act(3000, 25.0), [], 3000, 0, 0)['ok'] is True
    checks['i2_hold'] = i2_of(act(3000, 25.0), ['action_003000.hold.json'], 3000, 0, 0)['ok'] is False
    t1doc = act(1, 30.0, floor=S)
    t150 = act(150, 24.0, floor=S)
    t150['metadata']['head_observation_prior_discarded'] = 1.0
    checks['i2_warm_exception'] = i2_of(t150, [], 150, 0, 0, ('head_discharge_floor_173_p4_301ceabb95f116fa',
                                                             t1doc))['ok'] is True
    checks['i2_warm_exception_false'] = i2_of(t150, [], 150, 0, 0, ('head_discharge_floor_173_p4_301ceabb95f116fa',
                                                                   act(1, 30.0)))['ok'] is False
    checks['no_import_of_driver'] = not any(m in sys.modules for m in ('vb_chain', 'vb_lib32', 'vb_select', 'k92lib',
                                                                      'cglib', 'k92_compare', 'k92_record'))
    ok = all(v is True for v in checks.values())
    out = here / 'selftest' / 'vb_recalc_selftest.json'
    doc = {'schema': 'k92vb-recalc-selftest/v1', 'tool_sha256': fsha(__file__), 'ok': ok, 'checks': checks}
    out.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str) + '\n', encoding='utf-8')
    shutil.rmtree(root)
    print('VB_RECALC_SELFTEST ok=%s n=%d sha=%s' % (ok, len(checks), fsha(out)))
    return 0 if ok else 1


def main(argv):
    if len(argv) == 1 and argv[0] == 'selftest':
        return selftest()
    if len(argv) == 5 and argv[0] == 'run' and argv[1] == '--vbr' and argv[3] == '--dest':
        try:
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
        except Exception:  # noqa: BLE001
            pass
        r = run(argv[2], argv[4])
        print('VB_RECALC equal=%s compared=%d diff=%d' % (r['equal'], r['n_compared'], r['n_diff']))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
