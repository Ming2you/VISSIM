"""Judges of the V-A OfflineGates stage (amendment 34 section 5, OG_METHOD.md 2-5), written before any gate data of this
stage.  Read-only; BLIND (paths, kinds, counts, sha, booleans; never an objective / prediction value).

Copy of the K8b judge SP/j1/fix/gates/gjudge.py (b9daf7cd...).  Differences = amendment 34 section 5.0 R4 closed list:
  item 1  expected values: PROFILE_NEW = OUTVA, FRZ_K92, K9-2-7, tuning c8e3ee2c..., FRZ_K92 gb7_allowed.py
          (file sha = K9-2-7 blob bytes sha, list a8148f38...7af1).  FRZ7, K7 GB-9 wall reference, R-obs3 unchanged.
  item 2  gb7_row condition 7 = gb7_k92decl.judge_cond7(...)['c7_A_or_EK92'] (section 5.2-4, floor key
          head_discharge_floor_173_p4_e36d6761cfeac634, evidence Root = FRZ_K92); c7_declared_A, outside_A,
          outside_A_and_EK92, ek92 hits / checks are report fields; per-item hits counted with gb7_k92decl.which.
  item 3  GB-7' PASS also needs control_fields_equal_count == 61; each hash A/B run also needs control_fields_equal.
  item 4  the D-K9-12 branch (PROGRESS_DK912) and DK912_PATH are removed (raw_get went with it).
  item 5  cmp21 / judge_pairs / gh2*_pairs (G-H2a-d) are removed.
  item 7  PROFILE_K8B (FRZ_K8b, b9734abe, d0f9ef39..., list f954c2b0..., OUTH) is for self-test (i) only; its E_K92
          evidence Root is FRZ_K8b.  Because the two profiles use different lists, the list module is a profile entry
          (P['G']) instead of a module global.
Functions return dicts with 'status' in {PASS, FAIL, INCOMPLETE}."""
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gcommon as c  # noqa: E402
import gb7_k92decl as ek  # noqa: E402

EK92_FILE_SHA = c.sha256_file(Path(ek.__file__))
if EK92_FILE_SHA != c.EK92_SHA:
    raise SystemExit('gb7_k92decl.py sha %s != fixed %s (S-A34-11)' % (EK92_FILE_SHA, c.EK92_SHA))
G_NEW, LREC_NEW = c.load_allowed()
G_K8B, LREC_K8B = c.load_allowed(c.FRZ8, c.ALLOWED_FILE_K8B_SHA, c.LIST_K8B_SHA, c.A_K8_N_K8B)
PROFILE_NEW = {'name': 'FRZ_K92', 'OUT': c.OUTV, 'FRZ': c.FRZN, 'HEAD': c.HEAD, 'TUNING': c.TUNING_SHA, 'WT': c.WT,
               'G': G_NEW, 'LREC': LREC_NEW, 'EK92_ROOT': c.FRZN, 'FLOOR_KEY': c.FLOOR_KEY}
PROFILE_K8B = {'name': 'FRZ_K8b(selftest)', 'OUT': c.OUTH, 'FRZ': c.FRZ8, 'HEAD': c.HEAD_K8B,
               'TUNING': c.TUNING_K8B_SHA, 'WT': c.WT, 'G': G_K8B, 'LREC': LREC_K8B, 'EK92_ROOT': c.FRZ8,
               'FLOOR_KEY': c.FLOOR_KEY}
TIMES = [1] + [150 * k for k in range(1, 61)]
K7_WALL = {900: (670, 657.096231), 2700: (573.3, 560.722297), 4950: (664, 650.498557), 6300: (649.6, 636.919625)}
CONTROL_FIELDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
COND_KEYS = ('c1_prepare', 'c2_ps1_and_compare', 'c3_freeze', 'c4_roots', 'c5_tuning', 'c6_S', 'c7_diff_in_A', 'c8_csv')


def norm(p):
    return os.path.normcase(os.path.normpath(str(p))) if p is not None else None


def raw_diff(a, b, path='', out=None):
    """K7 gb_common.deep_diff (og_common.deep_diff) path form; returns (path, kind) only."""
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append((f'{path}/{key}', 'presence'))
            else:
                raw_diff(a[key], b[key], f'{path}/{key}', out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'list_length'))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                raw_diff(x, y, f'{path}[{i}]', out)
    elif a != b or type(a) is not type(b):
        out.append((path, 'value' if type(a) is type(b) else 'type'))
    return out


def standing(s):
    rr = s.get('replay_run') or {}
    st = s.get('standing') or {}
    df = (s.get('ps1') or {}).get('decision_failed')
    ok = (rr.get('exit_code') == 0 and st.get('error_files') == [] and not st.get('decision_failed_stdout')
          and not st.get('decision_failed_stderr') and not df)
    return {'ok': bool(ok), 'adapter_exit': rr.get('exit_code'), 'error_files': st.get('error_files'),
            'decision_failed': [st.get('decision_failed_stdout'), st.get('decision_failed_stderr'), df]}


def gb7_row(s, T, P):
    """OG_METHOD.md section 2 conditions 1-8 (no-control replay, Root = the profile's frozen root); condition 7 =
    A or E_K92 (amendment 34 section 5.2)."""
    s6 = '%06d' % T
    d = Path(s['replay_dir'])
    r = {'T': T, 'tag': s.get('tag')}
    pr = s.get('prepare') or {}
    rec = pr.get('record') or {}
    r['c1_prepare'] = (pr.get('exit') == 0 and rec.get('all_copies') is True
                       and rec.get('history_count') == rec.get('history_expected') == len(range(150, T, 150)))
    r['history'] = [rec.get('history_count'), rec.get('history_expected')]
    ps1 = s.get('ps1') or {}
    pc = s.get('ps1_compare') or {}
    cm = s.get('compare') or {}
    r['ps1_exit'] = ps1.get('exit')
    r['ps1_verdict'] = pc.get('verdict')
    r['ps1_checks'] = pc.get('checks')
    r['compare_verdict'] = cm.get('verdict')
    r['compare_checks'] = cm.get('checks')
    ac = pc.get('action_contract') or {}
    r['c2_ps1_and_compare'] = (ps1.get('exit') == 0 and pc.get('verdict') == 'IDENTICAL' and ac.get('ok') is True
                               and cm.get('verdict') == 'IDENTICAL')
    fl = ps1.get('freeze_line') or []
    r['freeze_line'] = fl
    r['c3_freeze'] = bool(fl) and 'FREEZE_VERIFIED' in fl[0] and ('head=' + P['HEAD']) in fl[0]
    rr = s.get('replay_run') or {}
    pv = s.get('provenance') or {}
    rl = ps1.get('root_lines') or []
    r['roots'] = {'replay_run_root': rr.get('root'), 'run_root': rr.get('run_root'), 'rebased': rr.get('rebased'),
                  'workspace_root': pv.get('workspace_root'), 'rebase_line': [l for l in rl if l.startswith('REBASE')]}
    r['c4_roots'] = (norm(rr.get('root')) == norm(P['FRZ']) and norm(rr.get('run_root')) == norm(c.FRZ7)
                     and rr.get('rebased') is True and bool(r['roots']['rebase_line'])
                     and norm(pv.get('workspace_root')) == norm(P['FRZ']))
    r['tuning'] = [rr.get('tuning_sha256'), pv.get('tuning_json_sha256')]
    r['c5_tuning'] = rr.get('tuning_sha256') == P['TUNING'] and pv.get('tuning_json_sha256') == P['TUNING']
    r['standing'] = standing(s)
    r['c6_S'] = r['standing']['ok']
    a_path, b_path = d / 'original' / ('action_%s.json' % s6), d / 'replay' / ('action_%s.json' % s6)
    if a_path.is_file() and b_path.is_file():
        a, b = c.read_json(a_path), c.read_json(b_path)
        diff = raw_diff(a, b)
        paths = [p for p, _ in diff]
        j = ek.judge_cond7(a, b, P['G'], P['EK92_ROOT'], floor_key=P['FLOOR_KEY'])
        r['diff_count'] = len(paths)
        r['c7_diff_in_A'] = j['c7_A_or_EK92'] is True
        r['c7_declared_A'] = j['c7_declared_A'] is True
        r['diff_outside_A'] = j['outside_A']
        r['diff_outside_A_EK92'] = j['outside_A_and_EK92']
        r['ek92'] = {'hits': j['ek92_hits'], 'checks': j['ek92_checks'], 'floor_key': j['floor_key'],
                     'allowed_list_sha256': j['allowed_list_sha256'],
                     'allowed_list_is_expected': j['allowed_list_is_expected'],
                     'outside_A_count': j['outside_A_count'], 'outside_A_and_EK92_count': j['outside_A_and_EK92_count']}
        ok_paths = tuple(p for p, _e in j['ek92_hits'])
        hits = {}
        for p, kind in diff:
            w = ek.which(p, P['G'], P['FLOOR_KEY'], ok_paths)
            h = hits.setdefault(w, {'paths': 0, 'kinds': {}})
            h['paths'] += 1
            h['kinds'][kind] = h['kinds'].get(kind, 0) + 1
        r['hits'] = hits
        r['c8_csv'] = ((d / 'original' / ('action_%s.csv' % s6)).read_bytes()
                       == (d / 'replay' / ('action_%s.csv' % s6)).read_bytes())
        r['control_fields_equal'] = all(not raw_diff(a.get(k), b.get(k)) for k in CONTROL_FIELDS)
    else:
        r['c7_diff_in_A'] = False
        r['c7_declared_A'] = False
        r['c8_csv'] = False
        r['control_fields_equal'] = False
        r['missing_action'] = [a_path.is_file(), b_path.is_file()]
    r['adapter_wall_sec'] = rr.get('wall_sec')
    r['ok'] = all(r.get(k) is True for k in COND_KEYS)
    return r


def judge_gb7(P):
    """GB-7' (OG_METHOD 2 + amendment 34 sections 5.1 row 1, 5.0 R4 item 3): 61 rows present, conditions 1-8 true in
    every row (condition 7 = A or E_K92) and control_fields_equal_count == 61 -> PASS; a missing row -> INCOMPLETE;
    otherwise FAIL.  c7_declared_A (list A alone) is reported only."""
    rows, missing, fails = [], [], []
    for T in TIMES:
        sp = P['OUT'] / 'gb7' / 'A' / ('T%06d.summary.json' % T)
        if not sp.is_file():
            missing.append(T)
            continue
        r = gb7_row(c.read_json(sp), T, P)
        rows.append(r)
        if not r['ok']:
            fails.append(T)
    agg = {}
    for r in rows:
        for k, h in (r.get('hits') or {}).items():
            a = agg.setdefault(k, {'paths': 0, 'decisions': 0})
            a['paths'] += h['paths']
            a['decisions'] += 1
    res = {'gate': "GB-7'", 'profile': P['name'], 'n_expected': 61, 'n_present': len(rows), 'missing': missing,
           'fails': fails, 'pass_count': sum(1 for r in rows if r['ok']), 'allowed_list': P['LREC'],
           'ek92_module_sha256': EK92_FILE_SHA, 'ek92_floor_key': P['FLOOR_KEY'], 'ek92_root': str(P['EK92_ROOT']),
           'hits_by_item': agg,
           'control_fields_equal_count': sum(1 for r in rows if r.get('control_fields_equal')),
           'csv_equal_count': sum(1 for r in rows if r.get('c8_csv')),
           'c7_declared_A_count': sum(1 for r in rows if r.get('c7_declared_A') is True),
           'cond_true_counts': {k: sum(1 for r in rows if r.get(k) is True) for k in COND_KEYS},
           'wall_sec_range': [min((r.get('adapter_wall_sec') or 0) for r in rows) if rows else None,
                              max((r.get('adapter_wall_sec') or 0) for r in rows) if rows else None],
           'rows': rows}
    if missing:
        res['status'] = 'INCOMPLETE'
    elif not fails and res['control_fields_equal_count'] == 61:
        res['status'] = 'PASS'
    else:
        res['status'] = 'FAIL'
    return res


def judge_hash(P):
    groups, ok_all, missing = {}, True, []
    v7 = tuple(P['G'].V)
    for T in (4050, 4500, 9000):
        s6 = '%06d' % T
        g = {'runs': {}, 'pairs': {}}
        docs = {}
        for seed in ('unset', '0', '2'):
            sp = P['OUT'] / 'gb7' / 'H' / ('T%s_h%s_r1.summary.json' % (s6, seed))
            if not sp.is_file():
                g['runs'][seed] = {'missing': True}
                missing.append((T, seed))
                ok_all = False
                continue
            s = c.read_json(sp)
            r = gb7_row(s, T, P)
            r['env_pythonhashseed'] = s.get('env_pythonhashseed')
            r['env_ok'] = s.get('env_pythonhashseed') == (None if seed == 'unset' else seed)
            r['ok_h'] = r['ok'] and r['env_ok'] and r.get('control_fields_equal') is True
            ok_all = ok_all and r['ok_h']
            g['runs'][seed] = {k: r.get(k) for k in ('ok_h', 'ok', 'env_ok', 'env_pythonhashseed', 'c1_prepare',
                                                     'c2_ps1_and_compare', 'c3_freeze', 'c4_roots', 'c5_tuning',
                                                     'c6_S', 'c7_diff_in_A', 'c8_csv', 'control_fields_equal',
                                                     'c7_declared_A', 'diff_count', 'standing', 'adapter_wall_sec',
                                                     'diff_outside_A', 'diff_outside_A_EK92', 'hits')}
            g['runs'][seed]['ek92_hits'] = (r.get('ek92') or {}).get('hits')
            g['runs'][seed]['csv_sha256'] = s.get('replay_action_csv_sha256')
            d = Path(s['replay_dir'])
            if (d / 'replay' / ('action_%s.json' % s6)).is_file():
                docs[seed] = (c.read_json(d / 'replay' / ('action_%s.json' % s6)), d)
        if len(docs) == 3:
            bd, bdir = docs['unset']
            for seed in ('0', '2'):
                doc, d = docs[seed]
                diff = [x for x in raw_diff(bd, doc) if x[0] not in v7]
                csv_same = ((bdir / 'replay' / ('action_%s.csv' % s6)).read_bytes()
                            == (d / 'replay' / ('action_%s.csv' % s6)).read_bytes())
                g['pairs']['unset_vs_' + seed] = {'json_diff_outside_V': [list(x) for x in diff[:20]], 'n': len(diff),
                                                  'csv_same': csv_same}
                ok_all = ok_all and not diff and csv_same
        else:
            ok_all = False
        groups[str(T)] = g
    return {'gate': 'hash A/B', 'profile': P['name'],
            'status': 'INCOMPLETE' if missing else ('PASS' if ok_all else 'FAIL'), 'missing': missing, 'groups': groups}


def judge_gb9(P):
    rows, missing, fails = [], [], []
    for T in (900, 2700, 4950, 6300):
        s6 = '%06d' % T
        sp = P['OUT'] / 'gb9' / 'B' / ('T%s_r1.summary.json' % s6)
        if not sp.is_file():
            missing.append(T)
            continue
        s = c.read_json(sp)
        d = Path(s['replay_dir'])
        r = {'T': T}
        pr = s.get('prepare') or {}
        rec = pr.get('record') or {}
        r['prepare_ok'] = (pr.get('exit') == 0 and rec.get('all_copies') is True
                           and rec.get('history_count') == rec.get('history_expected'))
        r['standing'] = standing(s)
        r['ps1_exit'] = (s.get('ps1') or {}).get('exit')
        r['c1_S'] = bool(r['prepare_ok'] and r['standing']['ok'] and r['ps1_exit'] in (0, 2))
        rr = s.get('replay_run') or {}
        pv = s.get('provenance') or {}
        act = d / 'replay' / ('action_%s.json' % s6)
        md = (c.read_json(act).get('metadata') or {}) if act.is_file() else {}
        r['validity'] = {'controller': rr.get('controller'), 'sdmpc_active': md.get('sdmpc_active'),
                         'tuning_arg_sha256': rr.get('tuning_sha256'), 'prov_tuning_sha256': pv.get('tuning_json_sha256'),
                         'workspace_root': pv.get('workspace_root'), 'workspace_git_commit': pv.get('workspace_git_commit'),
                         'replay_run_root': rr.get('root')}
        r['c2_valid'] = (rr.get('controller') == 'wu-link' and md.get('sdmpc_active') is True
                         and rr.get('tuning_sha256') == P['TUNING'] and pv.get('tuning_json_sha256') == P['TUNING']
                         and norm(pv.get('workspace_root')) == norm(P['WT']) and pv.get('workspace_git_commit') == P['HEAD']
                         and norm(rr.get('root')) == norm(P['WT']))
        ka, kb = K7_WALL[T]
        wa, wb = rr.get('wall_sec'), md.get('decision_wall_sec')
        r['wall'] = {'replay_run_wall_sec': wa, 'k7': ka, 'ratio_a': (wa / ka if isinstance(wa, (int, float)) else None),
                     'threshold_a': 1.5 * ka, 'decision_wall_sec': wb, 'k7_decision_wall_sec': kb,
                     'ratio_b': (wb / kb if isinstance(wb, (int, float)) else None), 'threshold_b': 1.5 * kb}
        r['c3_wall'] = (isinstance(wa, (int, float)) and isinstance(wb, (int, float))
                        and wa <= 1.5 * ka and wb <= 1.5 * kb)
        r['ok'] = bool(r['c1_S'] and r['c2_valid'] and r['c3_wall'])
        r['census_at_start'] = s.get('census_at_start')
        rows.append(r)
        if not r['ok']:
            fails.append(T)
    return {'gate': "GB-9'", 'profile': P['name'], 'status': 'INCOMPLETE' if missing else ('PASS' if not fails else 'FAIL'),
            'missing': missing, 'fails': fails, 'rows': rows}


def judge_s(gb7, h, gb9):
    n, bad = 0, []
    for r in gb7.get('rows', []):
        n += 1
        if not r['standing']['ok']:
            bad.append(('A', r['T']))
    for T, g in (h.get('groups') or {}).items():
        for seed, r in g['runs'].items():
            if r.get('missing'):
                continue
            n += 1
            if not (r.get('standing') or {}).get('ok'):
                bad.append(('H', T, seed))
    for r in gb9.get('rows', []):
        n += 1
        if not r['c1_S']:
            bad.append(('B', r['T']))
    expected = 61 + 9 + 4
    return {'gate': 'S', 'status': 'INCOMPLETE' if n < expected else ('PASS' if not bad else 'FAIL'), 'n': n,
            'expected': expected, 'bad': bad}
