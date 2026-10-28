"""VerifyGates recomputation of every V-A offline-gate verdict (amendment 34 sections 5.0-5.2) from raw files.

python -B v_judge.py NEW  <out.json>     the V-A gates on FRZ_K92 (OUTVA), then agreement with the gate judge JSONs
python -B v_judge.py K8B  <out.json>     self-test profile: the K8b gate outputs (OUTH) with the K8b list (no guard/FG/GH5)

Raw inputs only: replay bundles (manifest, copies, state, original/replay action JSON + CSV, replay_run.json,
adapter stdout/stderr, replay_compare*.json), the ps1 / prepare / compare text files, R-obs3 sources, FREEZE.json
tables, git objects, the preflight outputs / plan / provenance, K7 GB-9 r1 raw files, amendment 34 text.
Harness records (*.summary.json, *.prep.json, *.aim_gwt8.json) are read only for two values that exist nowhere else
(the ps1 process exit code and the hash A/B child PYTHONHASHSEED) and are marked 'harness_record'.
Gate judge JSONs (OUTVA/judge/*.json) are read only at the end, after all of my verdicts are computed, to compare.
Nothing of VA/gates is imported or executed.  BLIND: paths, kinds, booleans, counts, sha256, wall seconds only."""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v_lib as L  # noqa: E402

SP = Path(__file__).resolve().parents[3]          # .../scratchpad/k8
VA = SP / 'k92' / 'va'
DOCS = {'amendment34': (SP / 'K8_PREDECLARATION_AMENDMENT_34.md',
                        'a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e'),
        'amendment34_fixed_point': (VA / 'AMENDMENT34_FIXED.md',
                                    'fef58eca53240e6026a78e19729a699be5fa7e965a2d1648f185e551afc3c167'),
        'a34_pins': (VA / 'a34_pins.sha256', '4e44741657dc483f2cbe5dd99a83fe9b477f5bdeffd5eadd534f87cb6cac0403'),
        'decisions': (SP / 'K9_1_J1_NOTES_20261013.md',
                      '6b76cc09cc0bc0ea568f219dce16900799e3b1095b0d850ecc1d442720e6af88'),
        'og_method': (SP / 'j1' / 'og' / 'OG_METHOD.md',
                      '8edf86736c88b796dcc542538dadf228589fc996533379d71090c026fc2d475d'),
        'amendment21': (SP / 'K8_PREDECLARATION_AMENDMENT_21.md',
                        'ca369954977fc5f98e19b84d08932202847d37e36e26f243caa25df2d135d176')}
GATE_PINS = VA / 'gates' / 'va_gates_pins.sha256'
GATE_PINS_SHA = '6af36e7bd77dcc122886e56d30f0dae5ff76f75c72a74d2f6d9c33efeadfb669'

PROFILES = {
    'NEW': {'name': 'FRZ_K92', 'OUT': L.OUTVA, 'FRZ': L.FRZN, 'HEAD': L.HEAD, 'FREEZE_SHA': L.FREEZE_SHA,
            'TUNING': L.TUNING_SHA, 'WT': L.WT, 'LIST': (L.GB7_FILE_SHA, L.LIST_SHA, 35), 'EV_ROOT': L.FRZN,
            'GB9_TUNING_ARG_NOW': True},
    'K8B': {'name': 'FRZ_K8b(selftest)', 'OUT': L.OUTH, 'FRZ': L.FRZ8, 'HEAD': L.HEAD_K8B,
            'FREEZE_SHA': L.FREEZE_K8B_SHA, 'TUNING': L.TUNING_K8B_SHA, 'WT': L.WT,
            'LIST': (L.GB7_FILE_K8B_SHA, L.LIST_K8B_SHA, 34), 'EV_ROOT': L.FRZ8,
            # the GB-9' tuning argument is the GWT8 file, which K9-2-6 changed after the K8b gates; only the
            # recorded provenance sha can speak for the K8b time (self-test profile only).
            'GB9_TUNING_ARG_NOW': False},
}
COND = ('c1_prepare', 'c2_ps1_and_compare', 'c3_freeze', 'c4_roots', 'c5_tuning', 'c6_S', 'c7_A_or_EK92', 'c8_csv')


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S')


# ------------------------------------------------------------------------------------------------ prepare (c1)
def prev_sec(T):
    """Previous decision on the obs150 clock (n31_common.previous_decision_sec: 150 -> 1, 300 -> 150, ...; T=1 none)."""
    return None if T == 1 else (1 if T == 150 else T - 150)


def prepare_check(d, T, prepare_txt):
    s6 = '%06d' % T
    r = {}
    pl = L.lines_of(prepare_txt) or []
    r['replay_state_ok_line'] = any(l.startswith('REPLAY_STATE_OK') and ('sim_sec=%d ' % T) in l for l in pl)
    mp = d / 'replay_manifest.json'
    m = L.read_json(mp) if mp.is_file() else {}
    r['manifest_schema'] = m.get('schema') == 'sdmpc31-replay-state/v1' and m.get('sim_sec') == T
    r['previous_sec'] = m.get('previous_sec') == prev_sec(T)
    links = m.get('links') or []
    bad = []
    for lk in links:
        tgt = d / Path(*lk['rel'].split('/'))
        src = Path(lk['source'])
        ok = (lk.get('method') == 'copy' and tgt.is_file() and src.is_file()
              and L.sha256_file(tgt) == lk['sha256'] == L.sha256_file(src)
              and os.stat(L.long(tgt)).st_nlink == 1 and str(src).lower().startswith(str(L.ROBS3_DEC).lower()))
        if not ok:
            bad.append(lk['rel'])
    r['links'] = len(links)
    r['links_bad'] = bad
    r['links_all_copy_sha_ok'] = bool(links) and not bad
    st = d / ('state_%s.json' % s6)
    sd = L.read_json(st) if st.is_file() else {}
    r['state_obs150_dir_is_bundle'] = L.same_path((sd.get('obs150') or {}).get('directory'), d)
    hist_bad, n = [], 0
    for Tp in range(150, T, 150):
        n += 1
        a = d / 'obs150' / ('derived_%06d.json' % Tp)
        b = L.ROBS3_DEC / 'obs150' / ('derived_%06d.json' % Tp)
        if not (a.is_file() and b.is_file() and open(L.long(a), 'rb').read() == open(L.long(b), 'rb').read()
                and os.stat(L.long(a)).st_nlink == 1):
            hist_bad.append(Tp)
    r['history'] = [n - len(hist_bad), n]
    r['history_bad'] = hist_bad
    r['ok'] = (r['replay_state_ok_line'] and r['manifest_schema'] and r['previous_sec'] and r['links_all_copy_sha_ok']
               and r['state_obs150_dir_is_bundle'] and not hist_bad)
    return r


def standing_check(d, ps1f):
    rr = L.read_json(d / 'replay' / 'replay_run.json') if (d / 'replay' / 'replay_run.json').is_file() else {}
    err = sorted(str(p.relative_to(d)) for p in d.rglob('*.error.txt')) if d.is_dir() else ['<no bundle>']
    dfo = L.count_in_file(d / 'replay' / 'adapter_stdout.txt', 'DECISION_FAILED')
    dfe = L.count_in_file(d / 'replay' / 'adapter_stderr.txt', 'DECISION_FAILED')
    s = {'adapter_exit': rr.get('exit_code'), 'error_files': err,
         'decision_failed': [dfo, dfe, ps1f['decision_failed']]}
    s['ok'] = (rr.get('exit_code') == 0 and err == [] and dfo == 0 and dfe == 0 and ps1f['decision_failed'] == 0)
    return s


def harness_summary(group, tag):
    p = group / (tag + '.summary.json')
    if not p.is_file():
        return None
    s = L.read_json(p)
    return {'ps1_exit': (s.get('ps1') or {}).get('exit'), 'env_pythonhashseed': s.get('env_pythonhashseed'),
            'hashseed': s.get('hashseed')}


# ------------------------------------------------------------------------------------------------ GB-7' row
def gb7_row(P, G, group, tag, T):
    s6 = '%06d' % T
    d = group / tag
    r = {'T': T, 'tag': tag, 'bundle_present': d.is_dir()}
    r['prepare'] = prepare_check(d, T, group / (tag + '.prepare.txt'))
    r['c1_prepare'] = r['prepare']['ok']
    pl = L.lines_of(group / (tag + '.ps1.txt'))
    pf = L.ps1_facts(pl, s6)
    r['ps1'] = {k: pf[k] for k in ('refused', 'adapter_exit_line', 'compare_verdicts', 'ps1_exit_inferred',
                                   'decision_failed')}
    hs = harness_summary(group, tag)
    r['harness_record'] = hs
    r['ps1_exit_agrees_harness'] = hs is not None and hs['ps1_exit'] == pf['ps1_exit_inferred']
    c1p = d / 'replay_compare_ps1.json'
    c2p = d / 'replay_compare.json'
    cp1 = L.read_json(c1p) if c1p.is_file() else {}
    cp2 = L.read_json(c2p) if c2p.is_file() else {}
    ac1 = (cp1.get('checks') or {}).get('action_contract') or {}
    ac2 = (cp2.get('checks') or {}).get('action_contract') or {}
    cl = L.lines_of(group / (tag + '.compare.txt')) or []
    cv = [re.search(r'verdict=(\w+)', l).group(1) for l in cl if l.startswith('REPLAY_COMPARE verdict=')]
    r['compare'] = {'ps1_file_verdict': cp1.get('verdict'), 'ps1_file_has_tuning_contract': 'vsl_in_written_set' in ac1,
                    'ps1_action_contract_ok': ac1.get('ok'), 'second_file_verdict': cp2.get('verdict'),
                    'second_file_has_tuning_contract': 'vsl_in_written_set' in ac2, 'second_text_verdicts': cv}
    r['c2_ps1_and_compare'] = (pf['ps1_exit_inferred'] == 0 and pf['compare_verdicts'][-1:] == ['IDENTICAL']
                               and cp1.get('verdict') == 'IDENTICAL' and ac1.get('ok') is True
                               and 'vsl_in_written_set' in ac1 and cp2.get('verdict') == 'IDENTICAL'
                               and 'vsl_in_written_set' not in ac2 and cv[-1:] == ['IDENTICAL'])
    fl = pf['freeze_lines']
    r['freeze_lines'] = len(fl)
    r['c3_freeze'] = (len(fl) == 1 and ('sha256=' + P['FREEZE_SHA']) in fl[0] and ('head=' + P['HEAD']) in fl[0]
                      and ('path=' + str(P['FRZ'] / 'FREEZE.json').replace('/', '\\')).lower() in fl[0].lower())
    rrp = d / 'replay' / 'replay_run.json'
    rr = L.read_json(rrp) if rrp.is_file() else {}
    ap, bp = d / 'original' / ('action_%s.json' % s6), d / 'replay' / ('action_%s.json' % s6)
    a = L.read_json(ap) if ap.is_file() else None
    b = L.read_json(bp) if bp.is_file() else None
    prov = (b or {}).get('run_provenance') or {}
    exp_rebase = ('REBASE provenance root %s -> %s' % (str(L.FRZ7).replace('/', '\\'),
                                                         str(P['FRZ']).replace('/', '\\'))).lower()
    r['roots'] = {'root_is_frz': L.same_path(rr.get('root'), P['FRZ']), 'run_root_is_frz7': L.same_path(rr.get('run_root'), L.FRZ7),
                  'rebased': rr.get('rebased') is True,
                  'rebase_line': [l.lower() for l in pf['rebase_lines']] == [exp_rebase],
                  'workspace_root_is_frz': L.same_path(prov.get('workspace_root'), P['FRZ'])}
    r['c4_roots'] = all(r['roots'].values())
    args = rr.get('arguments') or []
    targ = args[args.index('--tuning-json') + 1] if '--tuning-json' in args else None
    prev = args[args.index('--previous-action-json') + 1] if '--previous-action-json' in args else None
    r['report_previous_arg_ok'] = (prev is None if T == 1 else
                                   L.same_path(prev, L.ROBS3_DEC / ('action_%06d.json' % prev_sec(T))))
    r['report_controller'] = rr.get('controller')
    r['tuning'] = {'arg_is_frz_file': L.same_path(targ, P['FRZ'] / L.TUNING_REL),
                   'arg_sha_now': L.sha256_file(targ) if targ and Path(targ).is_file() else None,
                   'prov_sha': ((prov.get('inputs') or {}).get('tuning_json') or {}).get('sha256')}
    r['c5_tuning'] = (r['tuning']['arg_is_frz_file'] and r['tuning']['arg_sha_now'] == P['TUNING']
                      and r['tuning']['prov_sha'] == P['TUNING'])
    r['standing'] = standing_check(d, pf)
    r['c6_S'] = r['standing']['ok']
    if a is not None and b is not None:
        j = L.cond7(a, b, G, P['EV_ROOT'])
        r.update({k: j[k] for k in ('diff_count', 'c7_declared_A', 'c7_A_or_EK92', 'outside_A', 'outside_A_and_EK92',
                                    'ek92_hits', 'ek92_failed', 'hits', 'which_disagree')})
        r['c8_csv'] = (open(L.long(d / 'original' / ('action_%s.csv' % s6)), 'rb').read()
                       == open(L.long(d / 'replay' / ('action_%s.csv' % s6)), 'rb').read())
        r['control_fields_equal'] = L.control_fields_equal(a, b)
        r['replay_json_sha256'] = L.sha256_file(bp)
        r['replay_csv_sha256'] = L.sha256_file(d / 'replay' / ('action_%s.csv' % s6))
        r['original_json_is_robs3'] = L.sha256_file(ap) == L.sha256_file(L.ROBS3_DEC / ('action_%s.json' % s6))
    else:
        r.update({'c7_declared_A': False, 'c7_A_or_EK92': False, 'c8_csv': False, 'control_fields_equal': False,
                  'missing_action': [ap.is_file(), bp.is_file()]})
    r['adapter_wall_sec'] = rr.get('wall_sec')
    r['ok'] = all(r.get(k) is True for k in COND)
    return r


def judge_gb7(P, G):
    group = P['OUT'] / 'gb7' / 'A'
    rows, missing = [], []
    for T in L.TIMES:
        tag = 'T%06d' % T
        if not (group / tag).is_dir():
            missing.append(T)
            continue
        rows.append(gb7_row(P, G, group, tag, T))
    agg = {}
    for r in rows:
        for k, h in (r.get('hits') or {}).items():
            x = agg.setdefault(k, {'paths': 0, 'decisions': 0})
            x['paths'] += h['paths']
            x['decisions'] += 1
    fails = [r['T'] for r in rows if not r['ok']]
    res = {'gate': "GB-7'", 'profile': P['name'], 'n_present': len(rows), 'missing': missing, 'fails': fails,
           'pass_count': len(rows) - len(fails),
           'cond_true_counts': {k: sum(1 for r in rows if r.get(k) is True) for k in COND},
           'control_fields_equal_count': sum(1 for r in rows if r.get('control_fields_equal') is True),
           'c7_declared_A_count': sum(1 for r in rows if r.get('c7_declared_A') is True),
           'ps1_exit_agrees_harness_count': sum(1 for r in rows if r.get('ps1_exit_agrees_harness')),
           'original_is_robs3_count': sum(1 for r in rows if r.get('original_json_is_robs3')),
           'report_previous_arg_ok_count': sum(1 for r in rows if r.get('report_previous_arg_ok')),
           'report_controllers': sorted({str(r.get('report_controller')) for r in rows}),
           'which_disagree_total': sum(len(r.get('which_disagree') or []) for r in rows),
           'outside_A_union': sorted({p for r in rows for p in r.get('outside_A') or []}),
           'outside_A_and_EK92_union': sorted({p for r in rows for p in r.get('outside_A_and_EK92') or []}),
           'ek92_item_decisions': {i: sum(1 for r in rows if any(h[1] == i for h in r.get('ek92_hits') or []))
                                   for i in ('E1', 'E2', 'E3', 'E4')},
           'ek92_E4_T': [r['T'] for r in rows if any(h[1] == 'E4' for h in r.get('ek92_hits') or [])],
           'ek92_failed_total': sum(len(r.get('ek92_failed') or []) for r in rows),
           'hits_by_item': agg,
           'adapter_wall_range': [min(ws), max(ws)] if (ws := [r['adapter_wall_sec'] for r in rows
                                                                if isinstance(r.get('adapter_wall_sec'), (int, float))])
           else None,
           'rows': rows}
    if missing:
        res['status'] = 'INCOMPLETE'
    elif not fails and res['control_fields_equal_count'] == 61:
        res['status'] = 'PASS'
    else:
        res['status'] = 'FAIL'
    return res


def judge_hash(P, G):
    group = P['OUT'] / 'gb7' / 'H'
    out, ok_all, missing = {}, True, []
    for T in L.HASH_T:
        s6 = '%06d' % T
        g = {'runs': {}, 'pairs': {}}
        for seed in L.HASH_SEEDS:
            tag = 'T%s_h%s_r1' % (s6, seed)
            if not (group / tag).is_dir():
                missing.append([T, seed])
                ok_all = False
                continue
            r = gb7_row(P, G, group, tag, T)
            hs = r['harness_record'] or {}
            r['env_ok_harness_record'] = hs.get('env_pythonhashseed') == (None if seed == 'unset' else seed)
            r['ok_h'] = r['ok'] and r['env_ok_harness_record'] and r.get('control_fields_equal') is True
            ok_all = ok_all and r['ok_h']
            g['runs'][seed] = {k: r.get(k) for k in COND + ('ok', 'ok_h', 'env_ok_harness_record', 'c7_declared_A',
                                                             'control_fields_equal', 'diff_count', 'outside_A',
                                                             'outside_A_and_EK92', 'ek92_hits', 'ek92_failed',
                                                             'standing', 'adapter_wall_sec', 'replay_csv_sha256',
                                                             'replay_json_sha256', 'ps1_exit_agrees_harness',
                                                             'which_disagree')}
        if all(s in g['runs'] for s in L.HASH_SEEDS):
            base = group / ('T%s_hunset_r1' % s6) / 'replay'
            bd = L.read_json(base / ('action_%s.json' % s6))
            bc = open(L.long(base / ('action_%s.csv' % s6)), 'rb').read()
            for seed in ('0', '2'):
                other = group / ('T%s_h%s_r1' % (s6, seed)) / 'replay'
                od = L.read_json(other / ('action_%s.json' % s6))
                diff = [x for x in L.deep_diff(bd, od) if x[0] not in G.V]
                v_in = [x for x in L.deep_diff(bd, od) if x[0] in G.V]
                same_csv = bc == open(L.long(other / ('action_%s.csv' % s6)), 'rb').read()
                g['pairs']['unset_vs_' + seed] = {'outside_V': [list(x[:2]) for x in diff], 'n_outside_V': len(diff),
                                                  'n_inside_V': len(v_in), 'csv_same': same_csv}
                ok_all = ok_all and not diff and same_csv
        else:
            ok_all = False
        out[str(T)] = g
    return {'gate': 'hash A/B', 'profile': P['name'], 'missing': missing,
            'status': 'INCOMPLETE' if missing else ('PASS' if ok_all else 'FAIL'), 'groups': out}


# ------------------------------------------------------------------------------------------------ GB-9'
def k7_reference():
    ref = {}
    for T in L.GB9_T:
        s6 = '%06d' % T
        d = L.K7GB9 / ('T%s_r1' % s6) / 'replay'
        rr = L.read_json(d / 'replay_run.json')
        md = L.read_json(d / ('action_%s.json' % s6)).get('metadata') or {}
        ref[T] = {'a': rr.get('wall_sec'), 'b': md.get('decision_wall_sec'),
                  'files': {'replay_run.json': L.sha256_file(d / 'replay_run.json'),
                            'action': L.sha256_file(d / ('action_%s.json' % s6))}}
    return ref


def code_bytes_vs_table(prov, wt, table):
    """run_provenance inputs/imported_modules entries whose path is under GWT8: sha == FRZ table entry."""
    base = os.path.normcase(os.path.normpath(str(wt))) + os.sep
    n, bad, outside = 0, [], 0
    entries = list(((prov.get('inputs') or {}).items())) + list(((prov.get('imported_modules') or {}).items()))
    for name, e in entries:
        if not isinstance(e, dict) or not e.get('path'):
            continue
        p = os.path.normcase(os.path.normpath(str(e['path'])))
        if not p.startswith(base):
            outside += 1
            continue
        rel = os.path.normpath(str(e['path']))[len(base):].replace('\\', '/')
        n += 1
        if table.get(rel) != e.get('sha256'):
            bad.append(name)
    return {'checked': n, 'mismatch': bad, 'not_under_gwt8': outside}


def judge_gb9(P, frz_table, k7):
    group = P['OUT'] / 'gb9' / 'B'
    rows, missing = [], []
    for T in L.GB9_T:
        s6 = '%06d' % T
        tag = 'T%s_r1' % s6
        d = group / tag
        if not d.is_dir():
            missing.append(T)
            continue
        r = {'T': T}
        r['prepare'] = prepare_check(d, T, group / (tag + '.prepare.txt'))
        pf = L.ps1_facts(L.lines_of(group / (tag + '.ps1.txt')), s6)
        r['ps1'] = {k: pf[k] for k in ('refused', 'adapter_exit_line', 'compare_verdicts', 'ps1_exit_inferred',
                                       'decision_failed')}
        hs = harness_summary(group, tag)
        r['harness_record'] = hs
        r['ps1_exit_agrees_harness'] = hs is not None and hs['ps1_exit'] == pf['ps1_exit_inferred']
        r['standing'] = standing_check(d, pf)
        r['c1_S'] = bool(r['prepare']['ok'] and r['standing']['ok'] and pf['ps1_exit_inferred'] in (0, 2))
        rr = L.read_json(d / 'replay' / 'replay_run.json')
        act = L.read_json(d / 'replay' / ('action_%s.json' % s6))
        md = act.get('metadata') or {}
        prov = act.get('run_provenance') or {}
        args = rr.get('arguments') or []
        targ = args[args.index('--tuning-json') + 1] if '--tuning-json' in args else None
        prev = args[args.index('--previous-action-json') + 1] if '--previous-action-json' in args else None
        v = {'controller_wu_link': rr.get('controller') == 'wu-link', 'sdmpc_active': md.get('sdmpc_active') is True,
             'tuning_arg_is_gwt8_file': L.same_path(targ, P['WT'] / L.TUNING_REL),
             'prov_tuning_sha': ((prov.get('inputs') or {}).get('tuning_json') or {}).get('sha256') == P['TUNING'],
             'workspace_root_gwt8': L.same_path(prov.get('workspace_root'), P['WT']),
             'workspace_git_commit': prov.get('workspace_git_commit') == P['HEAD'],
             'replay_root_gwt8': L.same_path(rr.get('root'), P['WT']),
             'previous_is_robs3_T_minus_150': L.same_path(prev, L.ROBS3_DEC / ('action_%06d.json' % (T - 150)))}
        if P['GB9_TUNING_ARG_NOW']:
            v['tuning_arg_sha_now'] = bool(targ) and L.sha256_file(targ) == P['TUNING']
        r['validity'] = v
        r['c2_valid'] = all(v.values())
        r['code_bytes'] = code_bytes_vs_table(prov, P['WT'], frz_table)
        wa, wb = rr.get('wall_sec'), md.get('decision_wall_sec')
        ka, kb = k7[T]['a'], k7[T]['b']
        r['wall'] = {'a': wa, 'b': wb, 'k7_a': ka, 'k7_b': kb, 'thr_a': 1.5 * ka, 'thr_b': 1.5 * kb,
                     'ratio_a': wa / ka if isinstance(wa, (int, float)) else None,
                     'ratio_b': wb / kb if isinstance(wb, (int, float)) else None}
        r['c3_wall'] = (isinstance(wa, (int, float)) and isinstance(wb, (int, float)) and wa <= 1.5 * ka
                        and wb <= 1.5 * kb)
        floors = sorted(k for k in md if L.FLOOR_173_RE.fullmatch(k))
        bind = md.get('k92_hb_seed_binding')
        r['report_only'] = {'k92_w_present': 'k92_w' in md, 'k92_hb_present': 'k92_hb' in md,
                            'seed_binding_flag': (bind if (type(bind) is float and bind in (0.0, 1.0)) else 'other'),
                            'floor_173_p4_key_count': len(floors), 'floor_173_p4_key_is_robs3_name': floors == [L.FLOOR_KEY]}
        r['ok'] = bool(r['c1_S'] and r['c2_valid'] and r['c3_wall'])
        rows.append(r)
    fails = [r['T'] for r in rows if not r['ok']]
    return {'gate': "GB-9'", 'profile': P['name'], 'missing': missing, 'fails': fails,
            'status': 'INCOMPLETE' if missing else ('PASS' if not fails else 'FAIL'), 'rows': rows}


def judge_s(gb7, h, g9):
    n, bad = 0, []
    for r in gb7['rows']:
        n += 1
        if not r['standing']['ok']:
            bad.append(['A', r['T']])
    for T, g in h['groups'].items():
        for seed, r in g['runs'].items():
            n += 1
            if not (r.get('standing') or {}).get('ok'):
                bad.append(['H', T, seed])
    for r in g9['rows']:
        n += 1
        if not r['c1_S']:
            bad.append(['B', r['T']])
    return {'gate': 'S', 'n': n, 'expected': 74, 'bad': bad,
            'status': 'INCOMPLETE' if n < 74 else ('PASS' if not bad else 'FAIL')}


# ------------------------------------------------------------------------------------------------ NEW only
def guard(frz_table):
    rec = {'when': now()}
    rec['docs'] = {k: {'sha256': L.sha256_file(p), 'ok': L.sha256_file(p) == e} for k, (p, e) in DOCS.items()}
    fsha = L.sha256_file(L.FRZN / 'FREEZE.json')
    fd = L.read_json(L.FRZN / 'FREEZE.json')
    rec['frz_freeze_sha'] = fsha == L.FREEZE_SHA
    rec['frz_head'] = (fd.get('git') or {}).get('head') == L.HEAD
    rec['frz_branch'] = (fd.get('git') or {}).get('branch') == 'claude/k92-b1-20261016'
    rec['frz_status_entries_0'] = (fd.get('git') or {}).get('status_entries') == 0
    rec['frz8_freeze_sha'] = L.sha256_file(L.FRZ8 / 'FREEZE.json') == L.FREEZE_K8B_SHA
    rec['gwt8_head'] = L.git('rev-parse', 'HEAD').strip() == L.HEAD
    st = [l for l in L.git('status', '--porcelain', '--ignored').splitlines()
          if l and '__tangentcache__' not in l and '__pycache__' not in l and '.pytest_cache' not in l]
    rec['gwt8_status_filtered_lines'] = st
    rec['gwt8_status_0'] = st == []
    t0 = time.perf_counter()
    gw = L.tree_table(L.WT)
    dg = L.table_diff(frz_table, gw)
    rec['gwt8_vs_frz_counts'] = {k: len(v) for k, v in dg.items()}
    rec['gwt8_vs_frz_sample'] = {k: v[:10] for k, v in dg.items()}
    rec['gwt8_vs_frz_000'] = not any(dg.values())
    rec['gwt8_hash_sec'] = round(time.perf_counter() - t0, 1)
    G = L.AllowedList(L.FRZN, L.GB7_FILE_SHA, L.LIST_SHA, 35)
    rec['list'] = G.record()
    blob = L.git('cat-file', 'blob', '%s:%s' % (L.HEAD, L.GB7_REL), binary=True)
    rec['list_file_eq_k927_blob'] = L.sha256_bytes(blob) == G.file_sha256 == L.GB7_FILE_SHA
    rec['tools'] = {n: [L.sha256_file(L.FRZN / L.TOOLS_REL / n), L.sha256_file(L.FRZ8 / L.TOOLS_REL / n)]
                    for n in L.TOOL_SHA}
    rec['tools_ok'] = all(v[0] == v[1] == L.TOOL_SHA[n] for n, v in rec['tools'].items())
    rec['frz_tuning_sha'] = L.sha256_file(L.FRZN / L.TUNING_REL) == L.TUNING_SHA
    rec['ek92_judge_file_sha'] = L.sha256_file(VA / 'gates' / 'gb7_k92decl.py') == L.EK92_JUDGE_SHA
    rec['ok'] = (all(v['ok'] for v in rec['docs'].values()) and rec['frz_freeze_sha'] and rec['frz_head']
                 and rec['frz_branch'] and rec['frz_status_entries_0'] and rec['frz8_freeze_sha'] and rec['gwt8_head']
                 and rec['gwt8_status_0'] and rec['gwt8_vs_frz_000'] and G.ok and rec['list_file_eq_k927_blob']
                 and rec['tools_ok'] and rec['frz_tuning_sha'] and rec['ek92_judge_file_sha'])
    return rec, G


def fg(frz_table):
    rec = {'when': now()}
    ns = sorted(tuple(l.split('\t', 1)) for l in L.git('diff', '--name-status', '--no-renames', L.HEAD_K925,
                                                     L.HEAD).splitlines() if l.strip())
    rec['fg1_name_status'] = [list(x) for x in ns]
    rec['FG-1'] = ns == sorted([('M', L.TUNING_REL), ('M', L.GB7_REL)])
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    r2 = subprocess.run(['git', '-C', str(L.WT), 'diff', L.HEAD_K925, L.HEAD, '--', 'evaluation', 'vendor', 'plant',
                         'scripts'], capture_output=True, env=env)
    rec['fg2'] = {'exit': r2.returncode, 'stdout_bytes': len(r2.stdout)}
    rec['FG-2'] = r2.returncode == 0 and r2.stdout == b''
    t8 = L.read_json(L.FRZ8 / 'FREEZE.json')['files']
    tn = L.read_json(L.FRZN / 'FREEZE.json')['files']
    sha = (lambda v: v if isinstance(v, str) else (v or {}).get('sha256'))
    tn = {k: sha(v) for k, v in tn.items()}
    t8 = {k: sha(v) for k, v in t8.items()}
    ch = sorted(k for k in tn.keys() & t8.keys() if tn[k] != t8[k])
    ad = sorted(tn.keys() - t8.keys())
    rm = sorted(t8.keys() - tn.keys())
    gd = {'M': set(), 'A': set(), 'D': set(), 'other': set()}
    for line in L.git('diff', '--name-status', '--no-renames', L.HEAD_K8B, L.HEAD).splitlines():
        if line.strip():
            s, p = line.split('\t', 1)
            gd.get(s, gd['other']).add(p)
    rows, ok_rows = [], True
    for p in sorted(gd['M'] | gd['A']):
        lt = L.git('ls-tree', L.HEAD, '--', p).split()
        f = L.FRZN / Path(*p.split('/'))
        data = open(L.long(f), 'rb').read() if f.is_file() else None
        ok = (data is not None and len(lt) >= 3 and lt[2] == L.git_blob_sha1(data)
              and L.sha256_bytes(data) == tn.get(p) == frz_table.get(p))
        ok_rows = ok_rows and ok
        rows.append({'path': p, 'ok': ok})
    rec['fg3'] = {'counts': [len(ch), len(ad), len(rm)], 'git_counts': {k: len(v) for k, v in gd.items()},
                  'sets_equal': set(ch) == gd['M'] and set(ad) == gd['A'] and set(rm) == gd['D'] and not gd['other'],
                  'blob_rows_ok': ok_rows, 'blob_rows': len(rows),
                  'bad_rows': [x['path'] for x in rows if not x['ok']]}
    rec['FG-3'] = (rec['fg3']['sets_equal'] and rec['fg3']['counts'] == [12, 21, 0] and len(rows) == 33 and ok_rows)
    tools = {n: [L.sha256_file(L.FRZN / L.TOOLS_REL / n), L.sha256_file(L.FRZ8 / L.TOOLS_REL / n)] for n in L.TOOL_SHA}
    rec['FG-4'] = all(v[0] == v[1] == L.TOOL_SHA[n] for n, v in tools.items())
    rec['status'] = 'PASS' if all(rec[k] for k in ('FG-1', 'FG-2', 'FG-3', 'FG-4')) else 'FAIL'
    return rec


def gh5():
    WD = 'RW_DECISION_ERROR_POLICY=hold_previous_on_exception (runtime.decision_error_policy)'
    pre = L.RVA / '_preflight'
    res = {}
    for S in L.SEEDS:
        name = 'sdmpc31_v3c3_k92va_s%d' % S
        out = L.OUTVA / 'gh5' / ('gh5_preflight_k92va_s%d.out' % S)
        lines = L.lines_of(out) or []
        g = lambda pat: [l for l in lines if re.search(pat, l)]  # noqa: E731
        k = {}
        fv = g(r'FREEZE_VERIFIED')
        k['1'] = len(fv) == 1 and ('sha256=' + L.FREEZE_SHA) in fv[0] and ('head=' + L.HEAD) in fv[0]
        lp = g(r'LAUNCH_PLAN_DETAIL')
        rd = g(r'\bRUN_DIR\b')
        run_dir = Path(rd[-1].split('RUN_DIR', 1)[1].strip()) if len(rd) == 1 else None
        plan_p = run_dir / 'launch_plan.json' if run_dir else None
        plan = L.read_json(plan_p) if plan_p and plan_p.is_file() else {}
        msha = re.search(r'LAUNCH_PLAN_DETAIL sha256=([0-9a-f]{64})', lp[0]) if len(lp) == 1 else None
        k['2'] = (len(lp) == 1 and 'network_sha=3de889f0' in lp[0] and 'controller=wu-link' in lp[0]
                  and 'sim_period=9000' in lp[0] and re.search(r'\bseed=%d\b' % S, lp[0]) is not None
                  and (plan.get('tuning') or {}).get('sha256') == L.TUNING_SHA and plan.get('warnings') == []
                  and bool(msha) and plan_p is not None and L.sha256_file(plan_p) == msha.group(1))
        nc, no = g(r'NETWORK_COPY_OK'), g(r'\bNETWORK_OK\b')
        k['3'] = (len(nc) == 1 and ('sha256=' + L.NET_SHA) in nc[0] and len(no) == 1 and ('sha256=' + L.NET_SHA) in no[0])
        po = g(r'PROVENANCE_OK')
        k['4'] = len(po) == 1 and ('freeze=' + L.FREEZE_SHA) in po[0]
        mp = re.search(r'path=(.+?\.json)', po[0]) if len(po) == 1 else None
        prov = L.read_json(mp.group(1)) if mp and Path(mp.group(1)).is_file() else {}
        k['5'] = ((prov.get('env') or {}).get('RW_DECISION_ERROR_POLICY') == 'hold_previous_on_exception'
                  and (plan.get('expected_env') or {}).get('RW_DECISION_ERROR_POLICY') == 'hold_previous_on_exception')
        k['6'] = sum(WD in l for l in lines) == 1
        ex = g(r'\bEXIT\b')
        k['7'] = len(g(r'PREFLIGHT_ONLY done; no VISSIM started')) == 1 and len(ex) == 1 and ('EXIT %s code=0' % name) in ex[0]
        k['8'] = not (L.RVA / name).exists()
        pf = sorted(p.name for p in pre.iterdir() if re.fullmatch(r'%s_\d{8}_\d{6}' % name, p.name)) if pre.is_dir() else []
        rep = {'run_dir_is_under_preflight': bool(run_dir) and L.same_path(run_dir.parent, pre),
               'preflight_folders_for_name': pf,
               'tuning_line_under_frz': any(l.split('  ', 1)[-1].startswith('TUNING ' + str(L.FRZN).replace('/', '\\'))
                                            for l in lines),
               'freeze_worktree_lines': len(g(r'FREEZE_WORKTREE')), 'refused_lines': len(g(r'REFUSED')),
               'provenance_tuning_sha': ((prov.get('files') or {}).get('tuning') or {}).get('sha256') == L.TUNING_SHA,
               'output_sha256': L.sha256_file(out) if out.is_file() else None,
               'plan_sha256': L.sha256_file(plan_p) if plan_p and plan_p.is_file() else None}
        res[str(S)] = {'conditions': k, 'report': rep, 'status': 'PASS' if all(k.values()) else 'FAIL'}
    return {'gate': "G-H5'", 'seeds': res,
            'status': 'PASS' if all(v['status'] == 'PASS' for v in res.values()) else 'FAIL'}


def thresholds(k7):
    """GB-9' wall thresholds: amendment 34 section 5.1 row 3 text = OG_METHOD table = 1.5 x K7 GB-9 r1 raw
    = the gate judge source constants (read as text with a regex; the judge is not imported)."""
    txt = L.read_text(DOCS['amendment34'][0])
    row = [l for l in txt.splitlines() if l.startswith('| 3 | **GB-9′**')]
    nums = lambda s: [float(x.replace(',', '')) for x in re.findall(r'[\d,]+\.\d+', s)]  # noqa: E731
    out = {'row_found': len(row) == 1}
    if len(row) == 1:
        ma = re.search(r'\(가\) `replay_run\.json wall_sec` ≤ ([^s]+) s', row[0])
        mb = re.search(r'\(나\) `metadata\.decision_wall_sec` ≤ ([^s]+) s', row[0])
        out['text_a'] = nums(ma.group(1)) if ma else None
        out['text_b'] = nums(mb.group(1)) if mb else None
    out['k7x15_a'] = [1.5 * k7[T]['a'] for T in L.GB9_T]
    out['k7x15_b'] = [1.5 * k7[T]['b'] for T in L.GB9_T]
    close = lambda xs, ys: xs is not None and len(xs) == len(ys) == 4 and all(abs(x - y) <= 1e-6 for x, y in zip(xs, ys))  # noqa: E731
    out['text_a_eq_k7x15'] = close(out.get('text_a'), out['k7x15_a'])
    out['text_b_eq_k7x15'] = close(out.get('text_b'), out['k7x15_b'])
    og = L.read_text(DOCS['og_method'][0])
    og_rows = {int(m.group(1)): [float(m.group(i)) for i in range(2, 6)]
               for m in re.finditer(r'^\| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$', og, re.M)}
    out['og_method_rows'] = og_rows
    out['og_eq_k7'] = all(T in og_rows and abs(og_rows[T][0] - k7[T]['a']) < 1e-9 and abs(og_rows[T][2] - k7[T]['b']) < 1e-9
                          and abs(og_rows[T][1] - 1.5 * k7[T]['a']) < 1e-6 and abs(og_rows[T][3] - 1.5 * k7[T]['b']) < 1e-6
                          for T in L.GB9_T)
    src = L.read_text(VA / 'gates' / 'gjudge.py')
    m = re.search(r'K7_WALL = \{(.+?)\}\n', src)
    gw = {int(a): (float(b), float(c)) for a, b, c in re.findall(r'(\d+): \(([\d.]+), ([\d.]+)\)', m.group(1))} if m else {}
    out['gate_judge_k7'] = gw
    out['gate_judge_k7_eq_raw'] = all(T in gw and gw[T][0] == k7[T]['a'] and gw[T][1] == k7[T]['b'] for T in L.GB9_T)
    out['gate_judge_uses_1_5'] = ('wa <= 1.5 * ka' in src and 'wb <= 1.5 * kb' in src)
    out['ok'] = (out['row_found'] and out['text_a_eq_k7x15'] and out['text_b_eq_k7x15'] and out['og_eq_k7']
                 and out['gate_judge_k7_eq_raw'] and out['gate_judge_uses_1_5'])
    return out


def order_and_pins():
    rec = {}
    ci = L.git('log', '-1', '--format=%cI|%aI|%an <%ae>|%cn <%ce>', L.HEAD).strip().split('|')
    rec['k927_commit'] = {'committer_time': ci[0], 'author_time': ci[1], 'author': ci[2], 'committer': ci[3]}
    rec['gb7_last_commit_is_k927'] = L.git('log', '-1', '--format=%H', L.HEAD, '--', L.GB7_REL).strip() == L.HEAD
    rec['k927_parent_is_k926'] = L.git('rev-parse', L.HEAD + '^').strip() == L.HEAD_K926
    import datetime as _dt
    t_commit = _dt.datetime.fromisoformat(ci[0]).timestamp()
    fd = L.read_json(L.FRZN / 'FREEZE.json')
    rec['freeze_created_at'] = fd.get('created_at')
    t_freeze = _dt.datetime.fromisoformat(fd['created_at']).timestamp()
    # creation time (st_ctime on Windows) of OUTVA/gb7 and every immediate entry of OUTVA/gb7/A (bundle folders and the
    # harness text files are created fresh; copied files inside bundles keep their source mtime, so mtimes are not used)
    ga = L.OUTVA / 'gb7' / 'A'
    first = None
    cands = [L.OUTVA / 'gb7', ga] + [ga / n for n in os.listdir(ga)] if ga.is_dir() else []
    for p in cands:
        t = os.stat(L.long(p)).st_ctime
        if first is None or t < first[0]:
            first = (t, str(p))
    rec['first_gb7A_output'] = {'time': _dt.datetime.fromtimestamp(first[0]).isoformat(timespec='seconds') if first else None,
                                'path': first[1] if first else None}
    gl = L.lines_of(L.OUTVA / 'logs' / 'g_driver.log') or []
    sa = [l for l in gl if 'STAGE_A start' in l]
    rec['driver_stage_A_start_line'] = sa[:1]
    t_stage_a = (_dt.datetime.fromisoformat(sa[0].split(' ', 1)[0]).timestamp() if sa else None)
    rec['commit_before_freeze'] = t_commit < t_freeze
    rec['commit_before_first_replay_output'] = bool(first) and t_commit < first[0]
    rec['commit_before_stage_A'] = t_stage_a is not None and t_commit < t_stage_a
    # judge pins: sha of the pin file, every pinned file unchanged now, pin file before the first replay output
    pins_sha = L.sha256_file(GATE_PINS)
    rec['gate_pins_file_sha'] = pins_sha
    rec['gate_pins_file_sha_ok'] = pins_sha == GATE_PINS_SHA
    bad, n, latest_pinned = [], 0, 0.0
    for line in L.read_text(GATE_PINS).splitlines():
        if not line.strip():
            continue
        h, name = line.split(' ', 1)
        p = GATE_PINS.parent / name.lstrip('*')
        n += 1
        if not p.is_file() or L.sha256_file(p) != h:
            bad.append(name)
        else:
            latest_pinned = max(latest_pinned, os.stat(p).st_mtime)
    pin_m = os.stat(GATE_PINS).st_mtime
    rec['gate_pins'] = {'lines': n, 'mismatch': bad, 'pin_file_mtime': _dt.datetime.fromtimestamp(pin_m).isoformat(timespec='seconds'),
                        'latest_pinned_file_mtime': _dt.datetime.fromtimestamp(latest_pinned).isoformat(timespec='seconds')}
    rec['pins_before_first_replay_output'] = bool(first) and pin_m < first[0]
    rec['pinned_files_not_newer_than_pin_file'] = latest_pinned <= pin_m
    so = VA / 'gates' / 'gb7_k92decl_selftest_gates.out.txt'
    rec['selftest_iii_stdout_sha'] = L.sha256_file(so) if so.is_file() else None
    rec['selftest_iii_stdout_eq_fixed'] = rec['selftest_iii_stdout_sha'] == L.EK92_SELFTEST_OUT_SHA
    rec['ok'] = (rec['gb7_last_commit_is_k927'] and rec['k927_parent_is_k926'] and rec['commit_before_freeze']
                 and rec['commit_before_first_replay_output'] and rec['commit_before_stage_A']
                 and rec['gate_pins_file_sha_ok'] and not bad and n == 31 and rec['pins_before_first_replay_output']
                 and rec['pinned_files_not_newer_than_pin_file'] and rec['selftest_iii_stdout_eq_fixed'])
    return rec


def state_now(frz_table):
    rec = {}
    t0 = time.perf_counter()
    act = L.tree_table(L.FRZN)
    dd = L.table_diff(frz_table, act)
    rec['frz_bytes_vs_table_counts'] = {k: len(v) for k, v in dd.items()}
    rec['frz_bytes_eq_table'] = not any(dd.values())
    rec['frz_hash_sec'] = round(time.perf_counter() - t0, 1)
    lst = L.listing(L.FRZN)
    caches = [k for k in lst if any(x.lower() in L.EXCL_DIRS for x in k.split('/')[:-1]) or k.lower().endswith('.pyc')]
    rec['frz_cache_files'] = [c for c in caches if not c.lower().startswith('.git')][:20]
    rec['frz_cache_0'] = not rec['frz_cache_files']
    before = [l.split('\t', 1)[0].strip() for l in L.read_text(VA / 'freeze' / 'frozen_top_before.txt').splitlines()
              if l.strip()]
    nowtop = sorted(os.listdir(L.FROZEN))
    rec['frozen_top_now'] = len(nowtop)
    rec['frozen_top_added'] = sorted(set(nowtop) - set(before))
    rec['frozen_top_removed'] = sorted(set(before) - set(nowtop))
    rec['frozen_top_ok'] = (rec['frozen_top_added'] == sorted([L.FRZN.name, 'robocopy_%s.log' % L.FRZN.name])
                            and not rec['frozen_top_removed'])
    rec['rva_top'] = sorted(os.listdir(L.RVA)) if L.RVA.is_dir() else None
    rec['rva_preflight'] = sorted(os.listdir(L.RVA / '_preflight')) if (L.RVA / '_preflight').is_dir() else None
    rec['rva_no_run_folders'] = not any((L.RVA / ('sdmpc31_v3c3_k92va_s%d' % s)).exists() for s in L.SEEDS)
    sums = L.OUTVA / 'SHA256SUMS_gates.txt'
    n, bad = 0, []
    for line in L.read_text(sums).splitlines():
        if not line.strip():
            continue
        h, name = line.split(' ', 1)
        name = name.lstrip('*').lstrip()
        p = (L.OUTVA / name) if not re.match(r'^[A-Za-z]:', name) else Path(name)
        n += 1
        if not p.is_file() or L.sha256_file(p) != h:
            bad.append(name)
    rec['outva_sums'] = {'file_sha': L.sha256_file(sums), 'lines': n, 'bad': bad[:20], 'bad_n': len(bad)}
    rec['ok'] = rec['frz_bytes_eq_table'] and rec['frz_cache_0'] and rec['frozen_top_ok'] and rec['rva_no_run_folders'] and not bad
    return rec


# ------------------------------------------------------------------------------------------------ agreement
def paths_of(xs):
    """Path list of a gate field that may hold paths or [path, kind] pairs (format not assumed)."""
    return sorted((x[0] if isinstance(x, (list, tuple)) else x) for x in (xs or []))


def agreement(mine):
    J = L.OUTVA / 'judge'
    g = lambda n: L.read_json(J / n) if (J / n).is_file() else None  # noqa: E731
    out = {}
    fgr = g('fg_result.json')
    out['FG'] = fgr is not None and fgr.get('status') == mine['FG']['status'] and all(
        fgr.get(k) == mine['FG'][k] for k in ('FG-1', 'FG-2', 'FG-3', 'FG-4')) and fgr['fg3']['counts'] == mine['FG']['fg3']['counts']
    g7 = g('gb7_result.json')
    rows_bad = []
    if g7:
        gr = {r['T']: r for r in g7['rows']}
        for r in mine['gb7']['rows']:
            x = gr.get(r['T'])
            keys = [('c1_prepare', 'c1_prepare'), ('c2_ps1_and_compare', 'c2_ps1_and_compare'), ('c3_freeze', 'c3_freeze'),
                    ('c4_roots', 'c4_roots'), ('c5_tuning', 'c5_tuning'), ('c6_S', 'c6_S'), ('c7_A_or_EK92', 'c7_diff_in_A'),
                    ('c7_declared_A', 'c7_declared_A'), ('c8_csv', 'c8_csv'), ('control_fields_equal', 'control_fields_equal'),
                    ('ok', 'ok')]
            diff = [m for m, gk in keys if x is None or bool(x.get(gk)) != bool(r.get(m))]
            if x is not None and (paths_of(x.get('diff_outside_A')) != paths_of(r.get('outside_A'))
                                  or paths_of(x.get('diff_outside_A_EK92')) != paths_of(r.get('outside_A_and_EK92'))
                                  or x.get('diff_count') != r.get('diff_count')):
                diff.append('path_lists_or_count')
            if diff:
                rows_bad.append([r['T'], diff])
    out['gb7_rows_disagree'] = rows_bad
    out['gb7'] = (g7 is not None and g7.get('status') == mine['gb7']['status'] and not rows_bad
                  and g7.get('c7_declared_A_count') == mine['gb7']['c7_declared_A_count']
                  and g7.get('control_fields_equal_count') == mine['gb7']['control_fields_equal_count'])
    if g7:
        gi = {k: v['paths'] for k, v in (g7.get('hits_by_item') or {}).items()}
        mi = {('OUTSIDE' if k is None else k): v['paths'] for k, v in mine['gb7']['hits_by_item'].items()}
        gi = {('OUTSIDE' if k in (None, 'None', 'null') else k): v for k, v in gi.items()}
        out['gb7_hits_by_item_equal'] = gi == mi
        out['gb7_hits_by_item_gate'] = gi
    hr = g('hash_result.json')
    hb = []
    if hr:
        for T, gg in mine['hash']['groups'].items():
            for s, r in gg['runs'].items():
                x = ((hr['groups'].get(T) or {}).get('runs') or {}).get(s) or {}
                d = [k for k, gk in (('ok_h', 'ok_h'), ('c7_A_or_EK92', 'c7_diff_in_A'), ('c7_declared_A', 'c7_declared_A'),
                                     ('c8_csv', 'c8_csv'), ('control_fields_equal', 'control_fields_equal'))
                     if bool(x.get(gk)) != bool(r.get(k))]
                if d:
                    hb.append([T, s, d])
            for pk, pv in gg['pairs'].items():
                x = ((hr['groups'].get(T) or {}).get('pairs') or {}).get(pk) or {}
                if x.get('n') != pv['n_outside_V'] or x.get('csv_same') != pv['csv_same']:
                    hb.append([T, pk, 'pair'])
    out['hash_disagree'] = hb
    out['hash'] = hr is not None and hr.get('status') == mine['hash']['status'] and not hb
    g9 = g('gb9_result.json')
    nb = []
    if g9:
        gr = {r['T']: r for r in g9['rows']}
        for r in mine['gb9']['rows']:
            x = gr.get(r['T']) or {}
            d = [k for k in ('c1_S', 'c2_valid', 'c3_wall', 'ok') if bool(x.get(k)) != bool(r.get(k))]
            w = x.get('wall') or {}
            if w.get('replay_run_wall_sec') != r['wall']['a'] or w.get('decision_wall_sec') != r['wall']['b']:
                d.append('wall_values')
            if d:
                nb.append([r['T'], d])
    out['gb9_disagree'] = nb
    out['gb9'] = g9 is not None and g9.get('status') == mine['gb9']['status'] and not nb
    sr = g('s_result.json')
    out['S'] = sr is not None and sr.get('status') == mine['S']['status'] and sr.get('n') == mine['S']['n']
    gh = g('gh5_result.json')
    gb = []
    if gh:
        for S, v in mine['GH5']['seeds'].items():
            x = (gh.get('seeds') or {}).get(S) or {}
            if x.get('status') != v['status']:
                gb.append([S, 'status'])
            r1 = g('gh5_s%s_result.json' % S) or {}
            if r1.get('status') != ('PASS' if all(v['conditions'][k] for k in '1234567') else 'FAIL'):
                gb.append([S, 'conditions_1_7'])
    out['gh5_disagree'] = gb
    out['GH5'] = gh is not None and gh.get('status') == mine['GH5']['status'] and not gb
    stg = g('stages.json') or {}
    flat = {}
    for v in stg.values():
        for k, s in (v.get('statuses') or {}).items():
            if isinstance(s, str) and k != 'seed':
                flat[k] = s
    out['stages_gate'] = flat
    mine_flat = {'FG': mine['FG']['status'], "GB-7'": mine['gb7']['status'], 'hash A/B': mine['hash']['status'],
                 "GB-9'": mine['gb9']['status'], 'S': mine['S']['status'], "G-H5'": mine['GH5']['status']}
    out['stages_mine'] = mine_flat
    out['stages_equal'] = flat == mine_flat
    gd = sorted(J.glob('guard_*.json'))
    out['gate_guard_files'] = [p.name for p in gd]
    out['gate_guard_ok'] = bool(gd) and all(L.read_json(p).get('ok') is True for p in gd)
    out['stop_files'] = sorted(p.name for p in J.glob('STOP_*.json'))
    out['all_agree'] = all(out[k] for k in ('FG', 'gb7', 'hash', 'gb9', 'S', 'GH5', 'stages_equal', 'gate_guard_ok')) \
        and out.get('gb7_hits_by_item_equal', False) and not out['stop_files']
    return out


# ------------------------------------------------------------------------------------------------ main
def main(profile, out_path):
    P = PROFILES[profile]
    t0 = time.perf_counter()
    res = {'profile': profile, 'started': now(), 'tool_sha256': {n: L.sha256_file(Path(__file__).parent / n)
                                                                  for n in ('v_lib.py', 'v_judge.py')}}
    frz_table = L.read_json(P['FRZ'] / 'FREEZE.json')['files']
    if profile == 'NEW':
        res['guard'], G = guard(frz_table)
        print('V_GUARD ok=%s gwt8_vs_frz=%s list=%s' % (res['guard']['ok'], res['guard']['gwt8_vs_frz_counts'],
                                                        res['guard']['list']['list_sha256'][:8]), flush=True)
        res['FG'] = fg(frz_table)
        print('V_FG %s FG-1=%s FG-2=%s FG-3=%s FG-4=%s counts=%s' % (res['FG']['status'], res['FG']['FG-1'],
              res['FG']['FG-2'], res['FG']['FG-3'], res['FG']['FG-4'], res['FG']['fg3']['counts']), flush=True)
    else:
        G = L.AllowedList(P['FRZ'], *P['LIST'])
        res['list'] = G.record()
    res['gb7'] = judge_gb7(P, G)
    g7 = res['gb7']
    print("V_GB7 %s pass=%d/61 fails=%s cond=%s controls=%d c7_declared_A=%d E=%s E4_T=%s outsideA=%s outsideAE=%s" % (
        g7['status'], g7['pass_count'], g7['fails'], g7['cond_true_counts'], g7['control_fields_equal_count'],
        g7['c7_declared_A_count'], g7['ek92_item_decisions'], g7['ek92_E4_T'], g7['outside_A_union'],
        g7['outside_A_and_EK92_union']), flush=True)
    res['hash'] = judge_hash(P, G)
    print('V_HASH %s pairs=%s' % (res['hash']['status'], {T: {k: [v['n_outside_V'], v['csv_same']] for k, v in g['pairs'].items()}
                                                          for T, g in res['hash']['groups'].items()}), flush=True)
    k7 = k7_reference()
    res['k7_reference'] = k7
    res['gb9'] = judge_gb9(P, frz_table, k7)
    print("V_GB9 %s %s" % (res['gb9']['status'], [(r['T'], r['c1_S'], r['c2_valid'], r['c3_wall'], r['wall']['a'],
                                                    round(r['wall']['b'], 3), r['code_bytes']['checked'],
                                                    len(r['code_bytes']['mismatch'])) for r in res['gb9']['rows']]),
          flush=True)
    res['S'] = judge_s(res['gb7'], res['hash'], res['gb9'])
    print('V_S %s n=%d bad=%s' % (res['S']['status'], res['S']['n'], res['S']['bad']), flush=True)
    if profile == 'NEW':
        res['GH5'] = gh5()
        print("V_GH5 %s %s" % (res['GH5']['status'], {S: v['conditions'] for S, v in res['GH5']['seeds'].items()}), flush=True)
        res['thresholds'] = thresholds(k7)
        print('V_THRESHOLDS ok=%s text_a=%s text_b=%s' % (res['thresholds']['ok'], res['thresholds'].get('text_a'),
                                                          res['thresholds'].get('text_b')), flush=True)
        res['order_pins'] = order_and_pins()
        op = res['order_pins']
        print('V_ORDER ok=%s commit=%s first_gb7A=%s pins=%s' % (op['ok'], op['k927_commit']['committer_time'],
                                                                 op['first_gb7A_output']['time'], op['gate_pins']), flush=True)
        res['state_now'] = state_now(frz_table)
        sn = res['state_now']
        print('V_STATE ok=%s frz_eq_table=%s cache0=%s frozen_added=%s rva=%s outva_sums=%s/%s' % (
            sn['ok'], sn['frz_bytes_eq_table'], sn['frz_cache_0'], sn['frozen_top_added'], sn['rva_preflight'],
            sn['outva_sums']['lines'] - sn['outva_sums']['bad_n'], sn['outva_sums']['lines']), flush=True)
        verdicts = [res['guard']['ok'], res['FG']['status'] == 'PASS', g7['status'] == 'PASS',
                    res['hash']['status'] == 'PASS', res['gb9']['status'] == 'PASS', res['S']['status'] == 'PASS',
                    res['GH5']['status'] == 'PASS']
        res['all_gates_pass_by_recomputation'] = all(verdicts)
        res['agreement'] = agreement(res)   # gate judge JSONs are read only here, after my verdicts
        ag = res['agreement']
        print('V_AGREE all=%s FG=%s gb7=%s(rows_bad=%d hits=%s) hash=%s gb9=%s S=%s GH5=%s stages=%s guard=%s stops=%s' % (
            ag['all_agree'], ag['FG'], ag['gb7'], len(ag['gb7_rows_disagree']), ag.get('gb7_hits_by_item_equal'),
            ag['hash'], ag['gb9'], ag['S'], ag['GH5'], ag['stages_equal'], ag['gate_guard_ok'], ag['stop_files']),
            flush=True)
        res['pass'] = (res['all_gates_pass_by_recomputation'] and ag['all_agree'] and res['thresholds']['ok']
                       and res['order_pins']['ok'] and res['state_now']['ok'])
    res['wall_sec'] = round(time.perf_counter() - t0, 1)
    res['finished'] = now()
    L.write_json(out_path, res)
    print('V_JUDGE_DONE profile=%s pass=%s wall=%s out_sha256=%s' % (profile, res.get('pass'), res['wall_sec'],
                                                                     L.sha256_file(out_path)), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
