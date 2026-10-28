# -*- coding: utf-8 -*-
"""fog_summary.py - FO gate summary (PRE_FO s4, 2026-10-27 KST, D-K9-113). Read-only. Written before any FO replay.

Per FO replay R1/R2/R3 (FRZ_FO + FO config, recorded B state v3c3-s31/s41/s43, T=900):
  A1 exit 0                                   A2 no exception (no 'Traceback (most recent call last)', no 'DECISION_FAILED'
  A3 decision completed (json+csv, budget       in stdout/stderr, no action_000900*.error* file)
     output_completed true)                   A4 decision wall <= 1,500 s (max of wrapper stopwatch and budget wall_sec)
  A5 urban signals = baseline only: JSON green_times (68) and offsets (17) == config baseline exactly; CSV 'signal' rows = 17
     with p1-p4 and offset == baseline (|d| <= 1e-9); every 'signal_sg' row SC is one of the 17
  A6 meters decided by SDMPC: controller_status ok, sdmpc_active true, sdmpc_state present, 8 'ramp_meter' CSV rows, and the
     decision coordinates are meter axes only (kinds == {meter}, count == the B record's meter-coordinate count, 0 green/offset)
  A7 VSL as B: 66 'vsl' CSV rows, all 110.0; JSON vsl values all 110
  A8 markers differ from the B record (same seed, same T) only as declared:
     - metadata.sdmpc_state.policy_sha256 != the B record value, and equal across R1-R3
     - metadata.sdmpc_state key set == the B record key set
     - joint_leader_selection.policy == the B record policy plus exactly one key 'actuator_scope' (== the FO config value)
     - none of the regional keys (regional_context, regional_prediction_blocks, regional_boundary, regional_mode,
       active_cost_owners, input_isolation_qualified, input_context_schema, regional_startup_baseline, active_resources,
       active_resource, region, regional_prediction_prototype, regional_context_required) anywhere in the action JSON
     - report only: top-level metadata keys without the 'head_' prefix, symmetric difference vs the B record
Control R0 (FRZ_FO + B config, recorded B state v3c3-s31, T=900):
  C1 exit 0, C2 no exception, C3 completed, C4 policy_sha256 == B record and policy == B record policy, C5 action_000900.csv
  bytes == the B record action_000900.csv (else HOLD = gate not passed)
Tree: freeze verify FRZ_FO before and after the replays (FREEZE_VERIFIED with the FRZ_FO sha).
G2: work/gate/g2_R1..R3.json pass (fog_sg_native.py gate).
Gate pass = all of the above. The wall-time line also reports R0 and the max over R1-R3 (StallSec 3,600 margin).
usage: python -B fog_summary.py <FRZ_FO> <out.json> [--selftest]
  --selftest: no replay outputs are read; every replay slot is pointed at the B record T=900 files of its seed (used once
  before PRE_FO is fixed, to exercise the parsers: R1-R3 must FAIL A5/A6/A8, R0 must PASS C4/C5).
"""
import csv, glob, hashlib, json, os, re, sys

W = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
G = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/gate'
BR = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc/decisions_sdmpc31_sdmpc9000_s%d'
FO_TUN_REL = 'diagnostics/b0_v3c3/config_fo_v3c3.json'
REGIONAL = ('regional_context', 'regional_prediction_blocks', 'regional_boundary', 'regional_mode', 'active_cost_owners',
            'input_isolation_qualified', 'input_context_schema', 'regional_startup_baseline', 'active_resources',
            'active_resource', 'region', 'regional_prediction_prototype', 'regional_context_required')
WALL_MAX = 1500.0
ITEMS = [('R1', 'b_s31', 31, 'fo'), ('R2', 'b_s41', 41, 'fo'), ('R3', 'b_s43', 43, 'fo'), ('R0', 'b_s31b', 31, 'b')]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    return json.load(open(p, encoding='utf-8-sig'))


def txt(p):
    if not os.path.exists(p):
        return ''
    raw = open(p, 'rb').read()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8-sig', errors='replace')


def keyscan(x, names, found):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in names:
                found[k] = found.get(k, 0) + 1
            keyscan(v, names, found)
    elif isinstance(x, list):
        for v in x:
            keyscan(v, names, found)
    return found


def csv_rows(p):
    with open(p, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def slot(item, selftest):
    rid, src, seed, cfg = item
    if selftest:
        d = BR % (seed, seed)
        return {'dec': d, 'state': None, 'stdout': '', 'stderr': '', 'files_dir': d, 'selftest': True}
    out = G + '/out/fog%s/%s/T000900' % (rid, src)
    return {'dec': out + '/files/decisions_sdmpc31_sdmpc9000_s%d' % seed, 'state': out + '/replay_state.json',
            'stdout': out + '/stdout.txt', 'stderr': out + '/stderr.txt', 'files_dir': out + '/files', 'selftest': False}


def common(item, sl):
    rid, src, seed, cfg = item
    r = {'id': rid, 'src': src, 'seed': seed, 'config': cfg}
    st = jl(sl['state']) if sl['state'] and os.path.exists(sl['state']) else {}
    r['replay_state'] = {k: st.get(k) for k in ('exit_code', 'wall_sec', 'status', 'python_priority', 'tuning_sha256', 'start', 'end', 'collect_exit')}
    err, out = txt(sl['stderr']), txt(sl['stdout'])
    r['stderr_tail'] = err[-400:]
    r['warn_lines'] = len(re.findall(r'\[\uacbd\uace0\]', err))
    act_j, act_c = sl['dec'] + '/action_000900.json', sl['dec'] + '/action_000900.csv'
    bud = sl['dec'] + '/action_000900.decision_budget.json'
    errs = [os.path.basename(p) for p in glob.glob(sl['dec'] + '/action_000900*.error*')]
    b = jl(bud) if os.path.exists(bud) else {}
    r['budget'] = {k: b.get(k) for k in ('output_completed', 'wall_sec', 'cpu_sec', 'unlimited_time')}
    walls = [x for x in (st.get('wall_sec'), b.get('wall_sec')) if isinstance(x, (int, float))]
    r['decision_wall_sec'] = max(walls) if walls else None
    r['error_files'] = errs
    r['A1_exit0'] = sl['selftest'] or st.get('exit_code') == 0
    r['A2_no_exception'] = ('Traceback (most recent call last)' not in err and 'DECISION_FAILED' not in err and 'DECISION_FAILED' not in out and not errs)
    r['A3_completed'] = os.path.exists(act_j) and os.path.exists(act_c) and b.get('output_completed') is True
    r['A4_wall_le_1500'] = r['decision_wall_sec'] is not None and r['decision_wall_sec'] <= WALL_MAX
    return r, act_j, act_c


def evaluate(frz, out, selftest=False):
    res = {'frz_fo': frz, 'selftest': selftest, 'items': []}
    fo_cfg = jl(frz + '/' + FO_TUN_REL)
    scope = fo_cfg['adapter']['sdmpc_actuator_scope']
    base = scope['baseline']
    res['fo_config_sha256'] = sha(frz + '/' + FO_TUN_REL)
    pol_fo = []
    for item in ITEMS:
        rid, src, seed, cfg = item
        sl = slot(item, selftest)
        r, act_j, act_c = common(item, sl)
        bj_p, bc_p = BR % (seed, seed) + '/action_000900.json', BR % (seed, seed) + '/action_000900.csv'
        r['b_record'] = {'json_sha256': sha(bj_p), 'csv_sha256': sha(bc_p)}
        if not (os.path.exists(act_j) and os.path.exists(act_c)):
            r['pass'] = False
            res['items'].append(r)
            continue
        a, rows = jl(act_j), csv_rows(act_c)
        bj, brows = jl(bj_p), csv_rows(bc_p)
        m, bm = a.get('metadata', {}), bj.get('metadata', {})
        sel, bsel = m.get('joint_leader_selection', {}) or {}, bm.get('joint_leader_selection', {}) or {}
        kinds = {}
        for row in rows:
            kinds[row['kind']] = kinds.get(row['kind'], 0) + 1
        r['csv_rows_by_kind'] = kinds
        r['csv_sha256'] = sha(act_c)
        st, bst = m.get('sdmpc_state') or {}, bm.get('sdmpc_state') or {}
        r['policy_sha256'], r['b_policy_sha256'] = st.get('policy_sha256'), bst.get('policy_sha256')
        r['selection_status'] = sel.get('selection_status')
        coords = sel.get('coordinates') or []
        ck = {}
        for c in coords:
            ck[c.get('kind')] = ck.get(c.get('kind'), 0) + 1
        bck = {}
        for c in bsel.get('coordinates') or []:
            bck[c.get('kind')] = bck.get(c.get('kind'), 0) + 1
        r['coordinate_kinds'], r['b_coordinate_kinds'] = ck, bck
        pol, bpol = sel.get('policy') or {}, bsel.get('policy') or {}
        r['policy_extra_keys'] = sorted(set(pol) - set(bpol))
        r['policy_missing_keys'] = sorted(set(bpol) - set(pol))
        r['policy_changed_keys'] = sorted(k for k in set(pol) & set(bpol) if pol[k] != bpol[k])
        found = keyscan(a, set(REGIONAL), {})
        r['regional_keys_found'] = found
        top, btop = {k for k in m if not k.startswith('head_')}, {k for k in bm if not k.startswith('head_')}
        r['report_top_metadata_only_replay'] = sorted(top - btop)
        r['report_top_metadata_only_b_record'] = sorted(btop - top)
        sig_rows = [x for x in rows if x['kind'] == 'signal']
        sg_rows = [x for x in rows if x['kind'] == 'signal_sg']
        r['signal_sg_rows'] = len(sg_rows)
        r['signal_sg_csv_sha256'] = hashlib.sha256('\n'.join(','.join([x['id'], x['dsd_no'], x['sc_no'], x['link'], x['p1_green'], x['p2_green'], x['offset'], x['green_sec']]) for x in sg_rows).encode()).hexdigest()
        if cfg == 'fo':
            gt, of = a.get('green_times') or {}, a.get('offsets') or {}
            dg = max((abs(float(gt.get(k, 'nan')) - v) for k, v in base['green_times'].items()), default=None)
            do = max((abs(float(of.get(k, 'nan')) - v) for k, v in base['offsets'].items()), default=None)
            csv_dev = []
            for x in sig_rows:
                sc = x['id']
                for i, p in enumerate(('p1_green', 'p2_green', 'p3_green', 'p4_green')):
                    want = base['green_times'].get('%s_p%d' % (sc, i + 1))
                    if want is None or abs(float(x[p]) - want) > 1e-9:
                        csv_dev.append((sc, p, x[p], want))
                if base['offsets'].get(sc) is None or abs(float(x['offset']) - base['offsets'][sc]) > 1e-9:
                    csv_dev.append((sc, 'offset', x['offset'], base['offsets'].get(sc)))
            sg_sc = sorted({int(x['sc_no']) for x in sg_rows})
            want_sc = sorted(int(k[2:]) for k in base['offsets'])
            r['json_green_max_abs_diff'], r['json_offset_max_abs_diff'] = dg, do
            r['csv_signal_deviations'] = csv_dev[:20]
            r['A5_urban_baseline_only'] = (dg == 0 and do == 0 and len(sig_rows) == 17 and not csv_dev and set(gt) == set(base['green_times'])
                                           and set(of) == set(base['offsets']) and set(sg_sc) <= set(want_sc))
            r['A6_meters_decided'] = (m.get('controller_status') == 'ok' and m.get('sdmpc_active') is True and bool(st)
                                      and kinds.get('ramp_meter') == 8 and set(ck) == {'meter'} and ck.get('meter') == bck.get('meter'))
            vsl_csv = [float(x['speed_kph']) for x in rows if x['kind'] == 'vsl']
            vj = a.get('vsl') or {}
            vvals = [float(v) for v in (vj.values() if isinstance(vj, dict) else vj)]
            r['A7_vsl_110'] = len(vsl_csv) == 66 and all(v == 110.0 for v in vsl_csv) and all(v == 110.0 for v in vvals)
            r['A8_markers_declared'] = (r['policy_sha256'] is not None and r['policy_sha256'] != r['b_policy_sha256']
                                        and set(st) == set(bst) and r['policy_extra_keys'] == ['actuator_scope']
                                        and not r['policy_missing_keys'] and not r['policy_changed_keys']
                                        and pol.get('actuator_scope') == scope and not found)
            pol_fo.append(r['policy_sha256'])
            r['pass'] = all(r[k] for k in ('A1_exit0', 'A2_no_exception', 'A3_completed', 'A4_wall_le_1500', 'A5_urban_baseline_only',
                                           'A6_meters_decided', 'A7_vsl_110', 'A8_markers_declared'))
        else:
            r['C4_policy_equals_b'] = r['policy_sha256'] == r['b_policy_sha256'] and not r['policy_extra_keys'] and not r['policy_missing_keys'] and not r['policy_changed_keys']
            r['C5_csv_bytes_equal_b_record'] = r['csv_sha256'] == r['b_record']['csv_sha256']
            r['pass'] = all(r[k] for k in ('A1_exit0', 'A2_no_exception', 'A3_completed', 'C4_policy_equals_b', 'C5_csv_bytes_equal_b_record'))
        res['items'].append(r)
    fo_items = [r for r in res['items'] if r['config'] == 'fo']
    res['policy_equal_across_fo'] = len(set(pol_fo)) == 1 and len(pol_fo) == 3
    res['signal_sg_equal_across_fo'] = len({r.get('signal_sg_csv_sha256') for r in fo_items}) == 1
    walls = [r.get('decision_wall_sec') for r in fo_items if r.get('decision_wall_sec') is not None]
    res['fo_decision_wall_max_sec'] = max(walls) if walls else None
    if selftest:
        res['freeze_verify'] = {'before': None, 'after': None}
        res['g2'] = {}
    else:
        fsha = sha(frz + '/FREEZE.json')
        vb, va = txt(G + '/freeze_verify_before.txt'), txt(G + '/freeze_verify_after.txt')
        res['freeze_verify'] = {'sha256': fsha, 'before': 'FREEZE_VERIFIED' in vb and fsha in vb, 'after': 'FREEZE_VERIFIED' in va and fsha in va}
        res['g2'] = {}
        for rid in ('R1', 'R2', 'R3'):
            p = W + '/g2_%s.json' % rid
            g = jl(p) if os.path.exists(p) else {}
            res['g2'][rid] = {'pass': g.get('pass') is True, 'written_sg': g.get('written_sg'), 'sg_with_difference': g.get('sg_with_difference'),
                              'differing_frames_total': g.get('differing_frames_total'), 'cycles_equal': g.get('cycles_equal'),
                              'sha256': sha(p) if os.path.exists(p) else None}
    res['pass'] = (all(r.get('pass') for r in res['items']) and res['policy_equal_across_fo'] and
                   (not selftest and res['freeze_verify']['before'] and res['freeze_verify']['after']
                    and all(v['pass'] for v in res['g2'].values()) and len(res['g2']) == 3))
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in res['items']:
        keys = [k for k in r if re.match(r'^[AC]\d_', k)]
        print(r['id'], r['src'], 'pass=%s' % r.get('pass'), ' '.join('%s=%s' % (k, r[k]) for k in keys),
              'wall=%s' % r.get('decision_wall_sec'), 'policy=%s' % (r.get('policy_sha256') or '')[:12],
              'coords=%s' % json.dumps(r.get('coordinate_kinds')), 'sel=%s' % r.get('selection_status'))
    print('POLICY_EQUAL_ACROSS_FO', res['policy_equal_across_fo'], 'SG_EQUAL_ACROSS_FO', res['signal_sg_equal_across_fo'],
          'FO_WALL_MAX', res['fo_decision_wall_max_sec'], 'FREEZE', json.dumps(res['freeze_verify']), 'G2', json.dumps({k: v['pass'] for k, v in res['g2'].items()}))
    print('FO_GATE_PASS', res['pass'])
    return 0


if __name__ == '__main__':
    a = sys.argv[1:]
    sys.exit(evaluate(a[0].replace('\\', '/').rstrip('/'), a[1], selftest='--selftest' in a))
