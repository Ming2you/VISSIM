"""K8b report items, alerts and the D-K8b-3 diagnosis (K8b-0; K8_PREDECLARATION_AMENDMENT_16 r2 sections 3.3, 6 and 7
as corrected by AMENDMENT_17).  Read-only on the judging outputs; never a gate verdict (the verdict is sa_gates.py).

    python -B k8b_report.py [--root R] [--out O] --tree k8bt [--gates-json F] [--eo-root DIR] [--data DIR]
        -> <out>/sa/gates/k8b_report_<tree>.{json,md}  (+ k8b_q7_diagnosis.{json,md} when the gates verdict is STOP)

Section 6 (report items, alerts are not verdicts; an alert goes to the head of the report and needs a user check before
K8-7 or a conditional J1 launch):
  R1 long SC105 / SC2004 / SC101 approach queues vs observed projection: long jobs TL3 s31 900 H24 / 2700 H42 / 4950 H27
     OBS, SAF and BASE, block ends t = T + 150 k: Q(t) = blocks[k].k8b0.signal_queue[signal]; Q_obs(t) = the ROBS61 SAF
     capture at t (capture.json probes.signal_queue); at GRID9 t the ROBS61 SAF value is checked against the TL3 BASE
     capture (+-1e-9, reported).  Alert: for a signal, >= 5 consecutive block ends with Q_SAF > 3 Q_obs + 30 and
     Q_SAF - Q_BASE > 30.
  R2 onW queue vs VISSIM: model blocks[k].w_queue[SC1001_W_to_onW]; VISSIM vissim_ref k8b onW (link 32 rows with
     NEXTLINK 10482).  Alert: TL3m 27 block 1 states with model - VISSIM(all) > +20 >= 9, or long block-end max excess
     > 60 (s31 SAF OBS).
  R3 ramps RM_C10484 / RM_C10480 and the W_out exit: (a) block-3 end ramp queue (TL3m 27 H3 OBS), alert when the
     states with SAF > 1.2 BASE and SAF - BASE > 5 are >= 9 (1/3); (b) accepted W_out -> R_D_E / R_D_W over [T, T+450)
     (blocks 1-3 k8b0.wout_accepted) vs VISSIM 10484 / 10480 entries (vissim_ref k8b wout_dest blocks 1-3), relative
     error = mean_s |M - V| / mean_s V (harness reading of "27 state mean |model - VISSIM| / VISSIM", fixed here before
     data); alert when > 0.5 and the SAF mean |error| > BASE mean |error| + 0.1 mean_s V; (c) SAF free-exit binding steps
     or OR_D_E landing-limited steps > 0 where BASE has 0, or a long block-end W_out occupancy > 84.8 veh (half of the
     deployed 169.61, AMENDMENT_17 item 5).
  R4 long 127 ready queue vs VISSIM stop: blocks[k].w_ready vs vissim_ref k8b long stop127[k] (s31).  Alert: >= 5
     consecutive block ends with w_ready < 0.5 VISSIM - 10.
  R5 3(a) decomposition (section 3.3) on the SAF 27 TL3m states: e = w_ports.total(T+150) - VISSIM(T+150.1); e0 =
     M(T) - VISSIM(T+0.1), M(T) = block_row's w_ports.total on the unpickled template state; g = template forecast gate
     inflow (forecast[0].urban_boundary[in_SC1001_W] x T_c) - VISSIM link 32 first appearances in (T+0.1, T+150.1];
     p = model port_inflow 10491 + 10481 (block 1) - VISSIM 10491 + 10481 first appearances; w = model w_departures
     (block 1) - VISSIM 10118 + 10368 + 10695 first appearances; r = e - e0 - g - p + w; u = e0 + g; i = e - u.
     Cross-checks (section 3.3 stage 2): |M(T) - k8b0.block0.w_ports.total| and |g_model - blocks[1].k8b0.gate_input_veh|
     <= 1e-6 per state.  No alert.
  R6 W_out exit law: per class assigned shares (k8b0.wout_counters 'assigned|c|d' at the last block) vs the evidence
     shares, exit shares reported, wout_store shrink.  Alert: |assigned share - declared| > 1e-9 or shrink > 0.01 veh.
  R7 G-EB-4 sign: per state signed error (gates JSON G-EB-4 per_state), event mean (s31 TL3 event states).  Alert:
     event mean < -25.
  R8 P-2 counters: p2_room_fallback_veh (k8b0.city_arrival.counters, last block) of every SAF job and the capture
     metadata k8b_p2_init.seed_residual_veh of every SAF capture.  Alert: room fallback > 1 veh in a judged job or a
     seed residual > 1e-6.
  Probe section 3.4 rule (BASE comparison): signal queue +20 % and +10 veh in >= 1/3 of the states (block 3, per
  signal), ramps RM_C10482 / RM_C10490 +20 % and +5 veh -- reported.
Section 7 (only when the gates verdict is STOP and INCOMPLETE items are 0): the (i)-(iv) criteria of section 7.3 with
their values and source fields; any criterion without its data is 'not confirmed'.

K9-1-0 (K8_PREDECLARATION_AMENDMENT_19 r2, sha 4ccfd8fd...; --k91):
  k91_outcome(gates, diag) -- sections 6.1-6.3 as one deterministic function of the gates JSON (gates_k91t.json) and
     the section 7.3 diagnosis (k8b_q7_diagnosis.json, optional) -> <out>/sa/gates/k91_outcome.json:
     classification (6.1): integrity = G-EB-0 / 1 / 2 / 8 / 9 / 13 / 14 and the G-EB-11 items (c) ad_vs_fd_T13,
       (d) d_s3_hooks, (e) e_state_error; fidelity = G-EB-3 / 4 / 5 / 6 / 7 and the G-EB-11 items (a) wall_ratio,
       (b) action_json; G-EB-10 / 12 not judged; any other gate, and any other judged G-EB-11 item, is integrity
       (unclassified -> integrity, conservative).  G-EB-11 is read item by item, every other gate by its verdict.
     complete = no judged item of a classified gate with pass_ null (G-EB-10 ignored).
     regression guard (6.2): R-a |b| of /gates/G-EB-3/items/d_W_out_TL3/value/bias > 5.559080631867624; R-b per
       checkpoint c in 6300 / 6750 |e_c| of /gates/G-EB-5/items/2700_stock/value/<c>/err > |k8bt e_c| (420.0430980575379
       / 523.1703620044482); R-c e_c < -150; full precision, strict inequalities, demotion ignored.  Valid only when
       every path exists with a finite number, the 3(d) TL3 item has value.n == 9 and pass_ not null, and the 2700
       stock item has pass_ not null and both checkpoints -- otherwise 'invalid' (never a silent pass).  It applies as
       soon as it is valid, before completeness.
     form (6.3): STOP_REGRESSION (a valid guard fires) > REGRESSION_INVALID (rerun per README; persisting -> STOP) >
       INCOMPLETE > INTEGRITY_FIX (an integrity gate / item FAIL: J1 held, amendment 20 path) > PASS_J1 (combined
       PROMOTE_ELIGIBLE) > CONDITIONAL_J1 (combined STOP, every failure a D-K8b-3 (i)-(iv) item and its section 7.3
       diagnosis confirmed) > KNOWN_DEFECT_J1 (failures in fidelity gates only).
  R9  W1 (k9_w1 capture metadata of the SAF TL3m / long captures): C_N + C_T (T = SC1001_N_SC2002_to_S_SC1003, the
      template capacity) vs 2 s_37p1 and s_37p1, the C_N rule value; block-1 model W1 departures (k91 record) vs VISSIM
      10119 / 10121 / 10698 entries (vissim_ref k91 conn, the same 450 s).  Alert: C_N + C_T > 2 s_37p1.
  R10 W2-A side class (SAF TL3m H3 and long jobs): assigned side shares (k8b0 wout_counters) vs the evidence shares,
      side_handoff_veh vs the corridor wout_handover transfers, long block-end corridor occupancy SAF vs BASE (k91
      records; the corridor 'ready' backlog is not recorded -- occupancy is reported in its place), model handover
      vs VISSIM 10703 entries.  'W_out room 0 blocked handover steps' is not recorded (None).  Alert: share deviation
      > 1e-9.
  R11 F17b: per exit s_hat (k9_f17b forecast) vs its c0 vs the VISSIM realized share of the same 450 s (TL3m); long
      jobs per period (D2 cuts 4500 / 6240 inside [T, min(T + 150 H, 8970)]): model 10491 blocked-step ratio (N9) vs
      the VISSIM spill-window ratio (spill_windows_W), request / landed / release.  Alert: any |difference| > 0.10.
  R12 D-EB-7 demotion of the G-EB-5 stock checkpoints vs the k8bt gates file (--k8bt-gates).  Alert: differs.
  R13 F14 open conditions (report): (a) VISSIM non-event 150 s blocks of a long job, plant 10491 blocked ratio > 0.2;
      (b) event start: first plant 10491 block earlier than the VISSIM event (ext127_first500) by > 300 s.
  R14 Z1: touch counts (k91 records), the latent sites outside Z1 (section 2.4), adfull state mismatches (key
      paths of the failed ad_full job errors)."""
import csv
import json
import math
import pickle
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
J = sc.JUDGING_ARM
R1_SIGNALS = ('SC105', 'SC2004', 'SC101')
ONW = 'SC1001_W_to_onW'
W_OUT_HALF = 84.8
DEFAULT_EO = Path(r'D:\VISSIM_runs\20260930_v3c2\reports\nc_analysis\eo')
ZONES = {'R1_0_5': range(0, 6), 'W_6_9': range(6, 10), 'D_10_18': range(10, 19), 'D_19_30': range(19, 31)}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return math.fsum(xs) / len(xs) if xs else None


def mae(xs):
    xs = [abs(x) for x in xs if x is not None]
    return math.fsum(xs) / len(xs) if xs else None


def job(tree, harness, T, arm, entry, H, seed=None):
    return sc.read_json(sc.job_dir(tree, sc.job_label(harness, T, arm, entry, H, seed=seed)) / 'summary.json')


def blk(s, k):
    if not s or not s.get('ok'):
        return None
    b = s.get('blocks') or []
    return b[k - 1] if len(b) >= k else None


def k8b0(s, k):
    b = blk(s, k)
    return (b or {}).get('k8b0') or None


def consecutive(flags):
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def tl3m_states():
    return [(s, T) for s in sc.TL3M_SEEDS for T in sc.GRID9]


def vref_k8b(ref, seed):
    return ((ref.get('seeds') or {}).get(str(seed)) or {}).get('k8b') or {}


# ------------------------------------------------------------------------------------------------ R1
def r1(tree):
    out = {'rows': {}, 'alert': False, 'robs_vs_tl3_base': {}}
    for T, H in sc.LONG_H.items():
        saf, base = job(tree, 'TL3', T, J, 'OBS', H), job(tree, 'TL3', T, 'BASE', 'OBS', H)
        row = {}
        for sig in R1_SIGNALS:
            series = []
            for k in range(1, H + 1):
                t = T + 150 * k
                cap = sc.read_json(sc.cap_dir(tree, 'ROBS61', t, J) / 'capture.json') if t <= 9000 else None
                q_obs = ((cap or {}).get('probes') or {}).get('signal_queue', {}).get(sig) if cap else None
                qs = ((k8b0(saf, k) or {}).get('signal_queue') or {}).get(sig)
                qb = ((k8b0(base, k) or {}).get('signal_queue') or {}).get(sig)
                series.append([t, qs, qb, q_obs])
            flags = [x[1] is not None and x[2] is not None and x[3] is not None and x[1] > 3 * x[3] + 30
                     and x[1] - x[2] > 30 for x in series]
            row[sig] = {'series': series, 'max_consecutive': consecutive(flags),
                        'missing': sum(1 for x in series if None in x[1:])}
            out['alert'] |= consecutive(flags) >= 5
        out['rows'][str(T)] = row
    for T in sc.GRID9:
        a = sc.read_json(sc.cap_dir(tree, 'ROBS61', T, J) / 'capture.json')
        b = sc.read_json(sc.cap_dir(tree, 'TL3', T, 'BASE') / 'capture.json')
        qa = ((a or {}).get('probes') or {}).get('signal_queue')
        qb = ((b or {}).get('probes') or {}).get('signal_queue')
        out['robs_vs_tl3_base'][str(T)] = (None if qa is None or qb is None else
                                          max(abs(qa[k] - qb.get(k, float('nan'))) for k in qa))
    return out


# ------------------------------------------------------------------------------------------------ R2
def r2(tree, ref):
    rows, n_over = [], 0
    for s, T in tl3m_states():
        m = (blk(job(tree, 'TL3', T, J, 'OBS', 3, seed=s), 1) or {}).get('w_queue', {}).get(ONW)
        v = ((vref_k8b(ref, s).get('states') or {}).get(str(T)) or {}).get('onW_T150')
        d = None if m is None or v is None else m - v
        n_over += d is not None and d > 20
        rows.append([s, T, m, v, d])
    lng = {}
    for T, H in sc.LONG_H.items():
        sj = job(tree, 'TL3', T, J, 'OBS', H)
        vl = ((vref_k8b(ref, 31).get('long') or {}).get(str(T)) or {}).get('onW') or {}
        ex = [((blk(sj, k) or {}).get('w_queue', {}).get(ONW), vl.get(str(k))) for k in range(1, H + 1)]
        diffs = [a - b for a, b in ex if a is not None and b is not None]
        lng[str(T)] = {'max_excess': max(diffs) if diffs else None, 'n': len(diffs)}
    alert = n_over >= 9 or any((v['max_excess'] or 0) > 60 for v in lng.values())
    return {'tl3m_block1': rows, 'n_states_over_20': n_over, 'long': lng, 'alert': alert}


# ------------------------------------------------------------------------------------------------ R3
def r3(tree, ref):
    a_rows, cnt = [], {r: 0 for r in sc.K8B_WOUT_RAMPS}
    b_err = {arm: {d: [] for d in ('R_D_E', 'R_D_W')} for arm in (J, 'BASE')}
    vis = {d: [] for d in ('R_D_E', 'R_D_W')}
    c_rows = []
    ramp_of = {'R_D_E': 'RM_C10484', 'R_D_W': 'RM_C10480'}
    for s, T in tl3m_states():
        sj, bj = job(tree, 'TL3', T, J, 'OBS', 3, seed=s), job(tree, 'TL3', T, 'BASE', 'OBS', 3, seed=s)
        qs, qb = (k8b0(sj, 3) or {}).get('ramp_queue') or {}, (k8b0(bj, 3) or {}).get('ramp_queue') or {}
        for r in sc.K8B_WOUT_RAMPS:
            if qs.get(r) is not None and qb.get(r) is not None and qs[r] > 1.2 * qb[r] and qs[r] - qb[r] > 5:
                cnt[r] += 1
        a_rows.append([s, T, qs, qb])
        vd = ((vref_k8b(ref, s).get('states') or {}).get(str(T)) or {}).get('wout_dest') or {}
        for d in ('R_D_E', 'R_D_W'):
            v = sum((vd.get(d) or {}).get(str(k), 0) for k in (1, 2, 3)) if vd else None
            vis[d].append(v)
            for arm, sm in ((J, sj), ('BASE', bj)):
                m = sum(((k8b0(sm, k) or {}).get('wout_accepted') or {}).get(ramp_of[d], 0.0) for k in (1, 2, 3)) \
                    if sm and sm.get('ok') else None
                b_err[arm][d].append(None if m is None or v is None else m - v)
        cs = [sum(((k8b0(sm, k) or {}).get(key) or 0.0) for k in (1, 2, 3)) if sm and sm.get('ok') else None
              for sm in (sj, bj) for key in ('wout_free_bind_steps', 'orde_room_limited_steps')]
        c_rows.append([s, T] + cs)
    b = {}
    alert_b = False
    for d in ('R_D_E', 'R_D_W'):
        mv = mean(vis[d])
        ms, mb = mae(b_err[J][d]), mae(b_err['BASE'][d])
        rel = None if mv in (None, 0.0) or ms is None else ms / mv
        flag = rel is not None and mb is not None and rel > 0.5 and ms > mb + 0.1 * mv
        alert_b |= flag
        b[d] = {'mean_vissim': mv, 'saf_mae': ms, 'base_mae': mb, 'saf_rel': rel, 'alert': flag}
    alert_c = any(r[2] is not None and r[4] is not None and ((r[2] > 0 and r[4] == 0)) for r in c_rows) or \
        any(r[3] is not None and r[5] is not None and (r[3] > 0 and r[5] == 0) for r in c_rows)
    occ = {}
    for T, H in sc.LONG_H.items():
        sj = job(tree, 'TL3', T, J, 'OBS', H)
        vals = [(blk(sj, k) or {}).get('w_out_occ') for k in range(1, H + 1)]
        vals = [v for v in vals if v is not None]
        occ[str(T)] = max(vals) if vals else None
    alert_c |= any(v is not None and v > W_OUT_HALF for v in occ.values())
    return {'a_block3': a_rows, 'a_count': cnt, 'a_alert': any(v >= 9 for v in cnt.values()), 'b': b,
            'b_alert': alert_b, 'c_rows_saf_bind_saf_limited_base_bind_base_limited': c_rows,
            'c_long_wout_occ_max': occ, 'c_alert': alert_c,
            'alert': any(v >= 9 for v in cnt.values()) or alert_b or alert_c}


# ------------------------------------------------------------------------------------------------ R4
def r4(tree, ref):
    out, alert = {}, False
    for T, H in sc.LONG_H.items():
        sj = job(tree, 'TL3', T, J, 'OBS', H)
        st = ((vref_k8b(ref, 31).get('long') or {}).get(str(T)) or {}).get('stop127') or {}
        series = [[k, (blk(sj, k) or {}).get('w_ready'), st.get(str(k))] for k in range(1, H + 1)]
        flags = [a is not None and v is not None and a < 0.5 * v - 10 for _k, a, v in series]
        out[str(T)] = {'series': series, 'max_consecutive': consecutive(flags)}
        alert |= consecutive(flags) >= 5
    return {'rows': out, 'alert': alert}


# ------------------------------------------------------------------------------------------------ R5 (section 3.3)
def w_ports_total(s, cfg):
    net = cfg.network
    cap = net.urban_link_storage_veh

    def f(x):
        return float(getattr(x, 'value', x))
    q = {m: f(v) for m, v in s.urban_movement_queue.items()}
    w_all = math.fsum(v for m, v in q.items() if m.startswith('SC1001_W_to_'))
    gate_occ = f(cap[sc.GATE]) - f(s.urban_link_storage.get(sc.GATE, cap[sc.GATE])) if sc.GATE in cap else 0.0
    transit = math.fsum(f(v) for v in (s.urban_inflow_transit_buffer.get('gate:' + sc.GATE) or {}).values())
    ports = getattr(s, 'lane_offramp_runtime', None)
    port = [f(ports.ports[o].stock) if ports is not None and o in ports.ports else 0.0 for o in ('10491', '10481')]
    return w_all + gate_occ + transit + port[0] + port[1]


def r5(tree, ref):
    for p in (str(c.R), str(c.R / 'vendor/NumSim-mine'), str(c.R / 'evaluation/controllers')):
        if p not in sys.path:
            sys.path.insert(0, p)
    rows, missing = [], []
    for s, T in tl3m_states():
        sj = job(tree, 'TL3', T, J, 'OBS', 3, seed=s)
        st = (((ref.get('seeds') or {}).get(str(s)) or {}).get('states') or {}).get(str(T)) or {}
        kv = (vref_k8b(ref, s).get('states') or {}).get(str(T)) or {}
        tpl = sc.cap_dir(tree, 'TL3', T, J, seed=s) / 'template.pickle'
        b1 = blk(sj, 1)
        if b1 is None or not tpl.is_file() or not st.get('w_ports_T150') or not kv:
            missing.append([s, T])
            continue
        t = pickle.loads(tpl.read_bytes())
        follower, state, _ref, forecast = t['owned']
        cfg = follower.cfg
        MT = w_ports_total(state, cfg)
        g_model = float(forecast[0].urban_boundary.get(sc.GATE, 0.0)) * float(cfg.simulation.T_c_h)
        fa = kv['first_appear']
        e = b1['w_ports']['total'] - st['w_ports_T150']['total']
        e0 = MT - st['w_ports_T']['total']
        g = g_model - fa['32']
        p = b1['port_inflow']['10491'] + b1['port_inflow']['10481'] - fa['10491'] - fa['10481']
        w = math.fsum(b1['w_departures'].values()) - fa['10118'] - fa['10368'] - fa['10695']
        r = e - e0 - g - p + w
        u = e0 + g
        rec0 = (((sj or {}).get('k8b0') or {}).get('block0') or {}).get('w_ports') or {}
        gi = (b1.get('k8b0') or {}).get('gate_input_veh')
        rows.append({'seed': s, 'T': T, 'e': e, 'e0': e0, 'g': g, 'p': p, 'w': w, 'r': r, 'u': u, 'i': e - u,
                     'M_T': MT, 'g_model': g_model,
                     'xcheck_M_T': None if rec0.get('total') is None else abs(MT - rec0['total']),
                     'xcheck_g': None if gi is None else abs(g_model - gi),
                     'persistence': abs(st['w_ports_T']['total'] - st['w_ports_T150']['total'])})
    i_vals = [x['i'] for x in rows]
    pers = mae([x['persistence'] for x in rows])
    xok = all(x['xcheck_M_T'] is not None and x['xcheck_M_T'] <= 1e-6 and x['xcheck_g'] is not None
              and x['xcheck_g'] <= 1e-6 for x in rows)
    stage2 = (None if missing or len(rows) != 27 else
              bool(abs(mean(i_vals)) <= 50 and mae(i_vals) <= pers and xok))
    return {'rows': rows, 'missing': missing, 'mae_e': mae([x['e'] for x in rows]), 'mean_i': mean(i_vals),
            'mae_i': mae(i_vals), 'persistence_mae': pers, 'xchecks_ok': xok, 'stage2_iv': stage2}


# ------------------------------------------------------------------------------------------------ R6 / R7 / R8
def r6(tree, root):
    ev_path = Path(root) / 'diagnostics' / 'sdmpc_n31_20260924' / 'k8b' / 'wout_exit_v3c3_20261007.json'
    ev = sc.read_json(ev_path) or {}
    shares = (ev.get('values') or {}).get('shares') or {}
    ramp_of = (ev.get('values') or {}).get('ramp_of') or {}
    dest_key = {'free': 'free', **{v: k for k, v in ramp_of.items()}}
    worst, shrink, rows = 0.0, 0.0, []
    for s, T in tl3m_states():
        sj = job(tree, 'TL3', T, J, 'OBS', 3, seed=s)
        last = (k8b0(sj, 3) or {}).get('wout_counters') or {}
        if not last:
            continue
        shrink = max(shrink, last.get('shrink_veh', 0.0))
        for cls in shares:
            tot = math.fsum(v for k, v in last.items() if k.startswith(f'assigned|{cls}|'))
            if tot <= 0:
                continue
            for k, v in last.items():
                if k.startswith(f'assigned|{cls}|'):
                    d = dest_key.get(k.split('|')[2], k.split('|')[2])
                    dev = abs(v / tot - float(shares[cls][d]))
                    worst = max(worst, dev)
        rows.append([s, T, {k: v for k, v in last.items() if k.startswith(('assigned|', 'exited|', 'shrink'))}])
    return {'worst_assigned_share_dev': worst, 'max_shrink_veh': shrink, 'rows': rows,
            'alert': worst > 1e-9 or shrink > 0.01}


def r7(gates):
    g4 = ((gates or {}).get('gates') or {}).get('G-EB-4') or {}
    rows = ((g4.get('items') or {}).get('per_state') or {}).get('value') or []
    ev = [r[3] for r in rows if r and r[0] in sc.TL3_EVENT and r[3] is not None]
    m = mean(ev)
    return {'per_state': rows, 'event_mean': m, 'alert': m is not None and m < -25}


def r8(tree):
    fall, resid = [], []
    jdir = sc.sa_out() / 'jobs' / tree
    for p in sorted(jdir.glob(f'*_{J}_*/summary.json')):
        s = sc.read_json(p) or {}
        b = (s.get('blocks') or [{}])[-1] if s.get('ok') else {}
        ca = ((b.get('k8b0') or {}).get('city_arrival') or {}).get('counters') or {}
        if ca.get('p2_room_fallback_veh', 0.0) > 1.0:
            fall.append([p.parent.name, ca.get('p2_room_fallback_veh')])
    for p in sorted((sc.sa_out() / 'cap' / tree).rglob('capture.json')):
        if p.parent.name != J:
            continue
        m = (((sc.read_json(p) or {}).get('metadata') or {}).get('k8b_p2_init') or {})
        if m.get('seed_residual_veh', 0.0) > 1e-6:
            resid.append([str(p.parent), m.get('seed_residual_veh')])
    return {'room_fallback_over_1': fall, 'seed_residual_over_1e6': resid, 'alert': bool(fall or resid)}


def probe34(tree):
    """Probe section 3.4 rule vs BASE (block 3 of the TL3m H3 OBS jobs): signal queues +20 % and +10 veh, ramps
    RM_C10482 / RM_C10490 +20 % and +5 veh, counted per signal / ramp; flagged at >= 1/3 of the states."""
    sig = defaultdict(int)
    ramp = defaultdict(int)
    n = 0
    for s, T in tl3m_states():
        a, b = k8b0(job(tree, 'TL3', T, J, 'OBS', 3, seed=s), 3), k8b0(job(tree, 'TL3', T, 'BASE', 'OBS', 3, seed=s), 3)
        ba, bb = blk(job(tree, 'TL3', T, J, 'OBS', 3, seed=s), 3), blk(job(tree, 'TL3', T, 'BASE', 'OBS', 3, seed=s), 3)
        if not a or not b or not ba or not bb:
            continue
        n += 1
        for k, v in a['signal_queue'].items():
            w = b['signal_queue'].get(k)
            if w is not None and v > 1.2 * w and v - w > 10:
                sig[k] += 1
        for r in ('RM_C10482', 'RM_C10490'):
            v, w = ba['ramp_queue'].get(r), bb['ramp_queue'].get(r)
            if v is not None and w is not None and v > 1.2 * w and v - w > 5:
                ramp[r] += 1
    third = n / 3.0
    return {'n_states': n, 'signal_counts': dict(sig), 'ramp_counts': dict(ramp),
            'flagged_signals': sorted(k for k, v in sig.items() if v >= third),
            'flagged_ramps': sorted(k for k, v in ramp.items() if v >= third)}


# ------------------------------------------------------------------------------------------------ section 7
def eo_n(eo_root, seed=31):
    out = {}
    with open(Path(eo_root) / f's{seed}_v3c2nc' / 'cells_30s.csv', newline='', encoding='utf-8') as h:
        for row in csv.DictReader(h):
            if row['road'] == 'FW_W':
                out.setdefault(round(float(row['time_s']), 1), {})[int(row['cell'])] = float(row['n_veh'])
    return out


def _period(T, H):
    return float(T), sc.g5_period_end(T, H)


def diag_i(tree, ref, gates, root):
    """Section 7.3 (i) per failed long job (2700 H42, 4950 H27): (i-a) 10491 blocked steps and FIFO = 0 seconds
    <= 1 % of the period steps; (i-b) OR_D_W request (landed + blocked, FW_W diagnostics) period mean <= 0.85 x the
    VISSIM 10491 flow and landed >= 0.98 x request; (i-d) K8b share: request + phi x Delta_RDW <= 0.85 V10491 and the
    10491 flow + phi x Delta_RDW still outside +-15 %; (i-c) EB only: E lanes ready 0 in >= 25 % of the E green
    seconds and model city 127 entries >= 0.85 x VISSIM city 127 entries."""
    g5 = ((gates or {}).get('gates') or {}).get('G-EB-5') or {}
    out = {}
    for T in sc.LONG_JUDGED:
        H = sc.LONG_H[T]
        s = job(tree, 'TL3', T, J, 'OBS', H)
        if not s or not s.get('ok'):
            out[str(T)] = {'confirmed': False, 'why': 'job absent or failed'}
            continue
        t0, t1 = _period(T, H)
        st = s.get('steps') or {}
        cap = (s.get('cap') or {}).get('10491')
        tt = [t for t in st.get('t') or [] if t0 < t <= t1]
        n = len(tt)
        blocked = sum(1 for t, x in zip(st.get('t') or [], st.get('stock_10491') or [])
                      if t0 < t <= t1 and cap is not None and x is not None and x >= cap - sc.PORT_BLOCK_MARGIN_VEH)
        sa_st = (s.get('k8b0') or {}).get('sa_steps') or {}
        fifo0 = sum(1 for t, f, q in zip(sa_st.get('t') or [], sa_st.get('fifo_10491') or [],
                                         sa_st.get('request_10491') or [])
                    if t0 <= t < t1 and f is not None and q is not None and f <= 1e-9 and q > 1e-9)
        fw = (s.get('k8b0') or {}).get('fw_steps') or {}
        key = next((k for k in fw if k.startswith('offramp_flow_') and ('OR_D_W' in k)), None) or \
            next((k for k in fw if k.startswith('offramp_flow_') and '10491' in k), None)
        bkey = key.replace('offramp_flow_', 'offramp_blocked_flow_') if key else None
        landed = [v for t, v in zip(fw.get('t') or [], fw.get(key) or []) if t0 <= t < t1] if key else []
        blockedf = [v for t, v in zip(fw.get('t') or [], fw.get(bkey) or []) if t0 <= t < t1] if bkey else []
        req = mean([a + b for a, b in zip(landed, blockedf)]) if landed and blockedf else None
        land = mean(landed) if landed else None
        f5 = (((g5.get('items') or {}).get(f'{T}_flow10491') or {}).get('value') or {}) if g5 else {}
        v10491, p10491 = f5.get('vissim_vph'), f5.get('plant_inflow_vph')
        vd = ((vref_k8b(ref, 31).get('long') or {}).get(str(T)) or {}).get('wout_dest') or {}
        kmax = int(math.ceil((t1 - T - 1e-9) / 150.0))
        V10480 = sum((vd.get('R_D_W') or {}).get(str(k), 0) for k in range(1, kmax + 1)) / max(t1 - t0, 1e-9) * 3600 \
            if vd else None
        M10480 = sum(((k8b0(s, k) or {}).get('wout_accepted') or {}).get('RM_C10480', 0.0)
                     for k in range(1, kmax + 1)) / max(t1 - t0, 1e-9) * 3600
        phi = None
        tpl = sc.cap_dir(tree, 'TL3', T, J) / 'template.pickle'
        if tpl.is_file():
            for p in (str(c.R), str(c.R / 'vendor/NumSim-mine'), str(c.R / 'evaluation/controllers')):
                if p not in sys.path:
                    sys.path.insert(0, p)
            net = pickle.loads(tpl.read_bytes())['owned'][0].cfg.network
            phi = float((getattr(net, 'off_ramp_split_ratio', {}) or {}).get('OR_D_W', float('nan')))
        delta = None if V10480 is None else max(0.0, V10480 - M10480)
        ia = n > 0 and blocked <= 0.01 * n and fifo0 <= 0.01 * n
        ib = (req is not None and land is not None and v10491 is not None and req <= 0.85 * v10491
              and land >= 0.98 * req)
        idd = (req is not None and v10491 is not None and delta is not None and phi is not None
               and req + phi * delta <= 0.85 * v10491)
        idd_b = (p10491 is not None and v10491 and delta is not None and phi is not None
                 and abs(p10491 + phi * delta - v10491) / v10491 > sc.G5_FLOW_REL)
        e_green = sum(((k8b0(s, k) or {}).get('e_green_steps') or 0.0) for k in range(1, kmax + 1))
        e0 = {l: sum((((k8b0(s, k) or {}).get('e_green_ready0_steps') or {}).get(l) or 0.0)
                     for k in range(1, kmax + 1)) for l in ('1', '2')}
        city_m = None
        bl = [k8b0(s, k) or {} for k in range(1, kmax + 1)]
        if bl and bl[-1].get('city_arrival'):
            cnt = bl[-1]['city_arrival']['counters']
            city_m = cnt.get('p2_landed_gate_veh', 0.0) + cnt.get('p2_landed_init_veh', 0.0) + \
                cnt.get('p2_room_fallback_veh', 0.0)
        city_v = sum((((vref_k8b(ref, 31).get('long') or {}).get(str(T)) or {}).get('city127') or {})
                     .get(str(k), 0) for k in range(1, kmax + 1))
        out[str(T)] = {'steps': n, 'blocked_10491': blocked, 'fifo0_s_10491': fifo0, 'i_a': ia,
                       'request_veh_h': req, 'landed_veh_h': land, 'vissim_10491_veh_h': v10491, 'i_b': ib,
                       'V10480_veh_h': V10480, 'M10480_veh_h': M10480, 'phi_OR_D_W': phi, 'delta_RDW': delta,
                       'plant_10491_veh_h': p10491, 'i_d_a': idd, 'i_d_b': idd_b, 'e_green_s': e_green, 'e_green_ready0_s': e0,
                       'i_c_starved': e_green > 0 and any(v >= 0.25 * e_green for v in e0.values()),
                       'city127_model': city_m, 'city127_vissim': city_v,
                       'i_c_city_ok': city_m is not None and city_v > 0 and city_m >= 0.85 * city_v,
                       'fw_key': key}
    return out


def diag_ii(tree, gates, eo_root):
    g4 = ((gates or {}).get('gates') or {}).get('G-EB-4') or {}
    rows = ((g4.get('items') or {}).get('per_state') or {}).get('value') or []
    eo = eo_n(eo_root)
    out = {}
    for r in rows:
        T, e_total = r[0], r[3]
        if e_total is None or abs(e_total) <= sc.G4_ABS_MAX:
            continue
        s = job(tree, 'TL3', T, J, 'OBS', 3)
        b3 = blk(s, 3)
        v = eo.get(round(T + 450.1, 1))
        if b3 is None or v is None:
            out[str(T)] = {'confirmed': False, 'why': 'inputs absent'}
            continue
        n = b3['fw_w_cell_n']
        ez = {z: math.fsum(n[i] for i in idx) - math.fsum(v.get(i, 0.0) for i in idx) for z, idx in ZONES.items()}
        st = s.get('steps') or {}
        cap = (s.get('cap') or {}).get('10491')
        blocked = [t for t, x in zip(st.get('t') or [], st.get('stock_10491') or [])
                   if cap is not None and x is not None and x >= cap - sc.PORT_BLOCK_MARGIN_VEH]
        vmin = []
        vm = None
        try:
            tp = sc.cap_dir(tree, 'TL3', T, J) / 'template.pickle'
            vm = float(pickle.loads(tp.read_bytes())['owned'][0].cfg.network.v_min)
        except Exception:
            pass
        if vm is not None:
            vmin = [t for t, x in zip(st.get('t') or [], st.get('cell_v_6_9_min') or []) if x is not None
                    and x <= vm + 1e-9]
        after = all(any(0 <= t - b <= 30 for b in blocked) for t in vmin) if vmin else True
        out[str(T)] = {'e_total': e_total, 'e_zone': ez, 'blocked_steps': len(blocked), 'vmin_steps': len(vmin),
                       'ii_a': not blocked and abs(e_total - ez['R1_0_5']) <= sc.G4_ABS_MAX,
                       'ii_b': bool(blocked) and after and abs(e_total - ez['R1_0_5'] - ez['W_6_9']) <= sc.G4_ABS_MAX}
    return out


def diag_iii(tree):
    out = {}
    for T in sc.LONG_JUDGED:
        H = sc.LONG_H[T]
        s = job(tree, 'TL3', T, J, 'OBS', H)
        if not s or not s.get('ok'):
            out[str(T)] = {'confirmed': False}
            continue
        st = s.get('steps') or {}
        cap = (s.get('cap') or {}).get('10491')
        blocked = [t for t, x in zip(st.get('t') or [], st.get('stock_10491') or [])
                   if cap is not None and x is not None and x >= cap - sc.PORT_BLOCK_MARGIN_VEH]
        vm = None
        try:
            tp = sc.cap_dir(tree, 'TL3', T, J) / 'template.pickle'
            vm = float(pickle.loads(tp.read_bytes())['owned'][0].cfg.network.v_min)
        except Exception:
            pass
        vmin = [t for t, x in zip(st.get('t') or [], st.get('cell_v_6_9_min') or [])
                if vm is not None and x is not None and x <= vm + 1e-9]
        miss = [t for t in vmin if not any(0 <= t - b <= 30 for b in blocked)]
        out[str(T)] = {'vmin_steps': len(vmin), 'without_block_in_30s': len(miss), 'examples': miss[:10],
                       'iii': vm is not None and not miss}
    return out


# ------------------------------------------------------------------------------------------------ K9-1-0
K91_INTEGRITY_GATES = ('G-EB-0', 'G-EB-1', 'G-EB-2', 'G-EB-8', 'G-EB-9', 'G-EB-13', 'G-EB-14')
K91_FIDELITY_GATES = ('G-EB-3', 'G-EB-4', 'G-EB-5', 'G-EB-6', 'G-EB-7')
K91_NOT_JUDGED = ('G-EB-10', 'G-EB-12')
K91_G11 = {'wall_ratio': 'fidelity', 'action_json': 'fidelity', 'ad_vs_fd_T13': 'integrity',
           'd_s3_hooks': 'integrity', 'e_state_error': 'integrity'}
K91_REG_BIAS = ('/gates/G-EB-3/items/d_W_out_TL3/value/bias', -5.559080631867624)
K91_REG_STOCK = {'6300': ('/gates/G-EB-5/items/2700_stock/value/6300/err', 420.0430980575379),
                 '6750': ('/gates/G-EB-5/items/2700_stock/value/6750/err', 523.1703620044482)}
K91_REG_FLOOR = -150.0
K8BT_GATES = Path(r'D:/VISSIM-merge/k8_gates_out_v3/sa/gates/gates_k8bt.json')
K8BT_GATES_SHA256 = '120974f9807477a8cf16d9404bede9f682c65840ae8bf8674d9a51c78240e12f'
K91_LATENT_OUTSIDE_Z1 = ('local_upstream row 10638 (LOR:97-99 -> LUR schedule_upstream / consume_upstream / register_ready)',
                         'OR_F_E direct row 10682 known_legsplit_receive cohort (RCC:1090-1110)',
                         'movement rows (LOR:116-121 _receive_corridor / _schedule; not in the SA arms)')
K91_W1 = ('SC1001_E_SC1002_to_W_RAMP', 'SC1001_N_SC2002_to_W_RAMP', 'SC1001_S_SC1003_to_W_RAMP')
K91_W1_CONN = {'SC1001_E_SC1002_to_W_RAMP': '10119', 'SC1001_N_SC2002_to_W_RAMP': '10121',
               'SC1001_S_SC1003_to_W_RAMP': '10698'}
K91_T_SHARED = 'SC1001_N_SC2002_to_S_SC1003'
K91_EW = ('10479', '10491', '10638', '10645')


def _ptr(doc, path):
    """(found, value) of a '/a/b/c' path in a JSON document."""
    node = doc
    for key in path.strip('/').split('/'):
        if not isinstance(node, dict) or key not in node:
            return False, None
        node = node[key]
    return True, node


def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def k91_regression(gates):
    """Amendment 19 r2 section 6.2 (r2 B-r1-3): the three values, their validity and R-a / R-b / R-c."""
    out = {'values': {}, 'invalid': [], 'k8bt': {'bias': K91_REG_BIAS[1], **{c_: v[1] for c_, v in K91_REG_STOCK.items()}}}
    found, b = _ptr(gates, K91_REG_BIAS[0])
    out['values']['bias'] = b
    if not found or not _finite(b):
        out['invalid'].append('3(d) TL3 bias absent / null / not finite')
    it = ((((gates or {}).get('gates') or {}).get('G-EB-3') or {}).get('items') or {}).get('d_W_out_TL3') or {}
    n = (it.get('value') or {}).get('n') if isinstance(it.get('value'), dict) else None
    if n != 9:
        out['invalid'].append('3(d) TL3 value.n = %r != 9' % (n,))
    if it.get('pass_') is None:
        out['invalid'].append('3(d) TL3 pass_ null')
    st = ((((gates or {}).get('gates') or {}).get('G-EB-5') or {}).get('items') or {}).get('2700_stock') or {}
    if st.get('pass_') is None:
        out['invalid'].append('2700_stock pass_ null')
    for c_, (path, _ref) in K91_REG_STOCK.items():
        found, e = _ptr(gates, path)
        out['values'][c_] = e
        if not found or not _finite(e):
            out['invalid'].append('2700 stock %s err absent / null / not finite' % c_)
    out['valid'] = not out['invalid']
    if not out['valid']:
        out.update(R_a=None, R_b=None, R_c=None, fires=None)
        return out
    out['R_a'] = abs(b) > abs(K91_REG_BIAS[1])
    out['R_b'] = {c_: abs(out['values'][c_]) > abs(ref) for c_, (_p, ref) in K91_REG_STOCK.items()}
    out['R_c'] = {c_: out['values'][c_] < K91_REG_FLOOR for c_ in K91_REG_STOCK}
    out['fires'] = bool(out['R_a'] or any(out['R_b'].values()) or any(out['R_c'].values()))
    return out


def k91_classify(gates):
    """Section 6.1 (r2 B-r1-4): rows {key: {gate, item, class, pass_, unclassified}} of every judged unit."""
    rows = {}
    for gid, g in sorted(((gates or {}).get('gates') or {}).items()):
        if gid in K91_NOT_JUDGED:
            continue
        items = g.get('items') or {}
        if gid == 'G-EB-11':
            for key, it in sorted(items.items()):
                if not it.get('judged'):
                    continue
                cls = K91_G11.get(key)
                rows[f'{gid}/{key}'] = {'gate': gid, 'item': key, 'class': cls or 'integrity',
                                        'unclassified': cls is None, 'pass_': it.get('pass_')}
            continue
        cls = ('integrity' if gid in K91_INTEGRITY_GATES else 'fidelity' if gid in K91_FIDELITY_GATES else None)
        verdict = g.get('verdict')
        rows[gid] = {'gate': gid, 'item': None, 'class': cls or 'integrity', 'unclassified': cls is None,
                     'pass_': True if verdict == 'PASS' else False if verdict == 'FAIL' else None,
                     'verdict': verdict,
                     'failed_items': sorted(k for k, it in items.items() if it.get('judged') and it.get('pass_') is False),
                     'null_items': sorted(k for k, it in items.items() if it.get('judged') and it.get('pass_') is None)}
    return rows


def k91_incomplete(gates):
    """Section 6.1 completeness: every judged item of every classified gate (G-EB-11: its five items) not null."""
    out = []
    for gid, g in sorted(((gates or {}).get('gates') or {}).items()):
        if gid in K91_NOT_JUDGED:
            continue
        for key, it in sorted((g.get('items') or {}).items()):
            if it.get('judged') and it.get('pass_') is None:
                out.append(f'{gid}/{key}')
    return out


def k91_conditional_units(gates, diag):
    """D-K8b-3 (i)-(iv) (amendment 16 r2 sections 7.1-7.3): {gate/item: confirmed} for every failed fidelity item;
    an item outside the list or without its confirming diagnosis is False (conservative)."""
    diag = diag or {}
    out = {}
    for gid in K91_FIDELITY_GATES:
        g = (((gates or {}).get('gates') or {}).get(gid) or {})
        for key, it in sorted((g.get('items') or {}).items()):
            if not it.get('judged') or it.get('pass_') is not False:
                continue
            ok = False
            if gid == 'G-EB-5' and key.split('_', 1)[-1] in ('flow10491', 'eb'):
                T = key.split('_', 1)[0]
                d = (diag.get('i') or {}).get(T) or {}
                base = bool(d.get('i_a') and d.get('i_b') and d.get('i_d_a') and d.get('i_d_b'))
                ok = base if key.endswith('flow10491') else bool(d.get('i_a') and d.get('i_b') and d.get('i_d_a')
                                                                 and d.get('i_c_starved') and d.get('i_c_city_ok'))
            elif gid == 'G-EB-4' and key == 'per_state':
                rows = (diag.get('ii') or {})
                failed = [r for r in (it.get('value') or []) if r and r[3] is not None and abs(r[3]) > sc.G4_ABS_MAX]
                ok = bool(failed) and all(((rows.get(str(r[0])) or {}).get('ii_a') or
                                           (rows.get(str(r[0])) or {}).get('ii_b')) for r in failed)
            elif gid == 'G-EB-7' and key.endswith('_collapse'):
                ok = bool(((diag.get('iii') or {}).get(key.split('_', 1)[0]) or {}).get('iii'))
            elif gid == 'G-EB-3' and key in ('a_bias', 'a_mae'):
                ok = diag.get('iv') is True
            out[f'{gid}/{key}'] = ok
    return out


def k91_outcome(gates, diag=None):
    """Amendment 19 r2 sections 6.1-6.3 (the one deterministic function; docstring of this module)."""
    reg = k91_regression(gates)
    rows = k91_classify(gates)
    incomplete = k91_incomplete(gates)
    integ = sorted(k for k, r in rows.items() if r['class'] == 'integrity' and r['pass_'] is False)
    fid = sorted(k for k, r in rows.items() if r['class'] == 'fidelity' and r['pass_'] is False)
    combined = (gates or {}).get('combined')
    cond = k91_conditional_units(gates, diag)
    if reg['valid'] and reg['fires']:
        form = 'STOP_REGRESSION'
    elif not reg['valid']:
        form = 'REGRESSION_INVALID'
    elif incomplete:
        form = 'INCOMPLETE'
    elif integ:
        form = 'INTEGRITY_FIX'
    elif combined == 'PROMOTE_ELIGIBLE' and not fid:
        form = 'PASS_J1'
    elif combined == 'STOP' and fid and cond and all(cond.values()):
        form = 'CONDITIONAL_J1'
    elif fid:
        form = 'KNOWN_DEFECT_J1'
    else:
        form = 'INCOMPLETE'                    # no failure but the combined verdict is not PROMOTE_ELIGIBLE
    return {'schema': 'k91-outcome/v1', 'amendment19_sha256': sc.K91_AMENDMENT19_SHA256, 'combined': combined,
            'regression': reg, 'classification': rows, 'unclassified': sorted(k for k, r in rows.items()
                                                                              if r['unclassified']),
            'incomplete_items': incomplete, 'integrity_failures': integ, 'fidelity_failures': fid,
            'conditional_units': cond, 'form': form,
            'rule': 'amendment 19 r2 sections 6.1-6.3 (k8b_report.py module docstring)'}


def _k91_record(tree, label):
    """The k91 record of a job: the summary's own (K9-keyed run) or k91_record.json (every run)."""
    d = sc.job_dir(tree, label)
    rec = sc.read_json(d / 'k91_record.json')
    if isinstance(rec, dict):
        return rec
    s = sc.read_json(d / 'summary.json') or {}
    return {'keyed': True, 'top': s.get('k91'), 'blocks': [b.get('k91') for b in s.get('blocks') or []]}


def _cap_meta(tree, harness, T, arm, seed=None):
    rec = sc.read_json(sc.cap_dir(tree, harness, T, arm, seed=seed) / 'capture.json') or {}
    return rec.get('metadata') or {}


def _vk91(ref, seed):
    return ((ref.get('seeds') or {}).get(str(seed)) or {}).get('k91') or {}


def _vwin(table, w0, w1):
    """Sum of window counts w0 <= w < w1 (ints, or [off, elig] pairs)."""
    if not isinstance(table, dict) or 'missing' in table:
        return None
    vals = [table.get(str(w)) for w in range(w0, w1)]
    if any(isinstance(v, list) for v in vals):
        return [sum((v or [0, 0])[0] for v in vals), sum((v or [0, 0])[1] for v in vals)]
    return sum(v or 0 for v in vals)


def _long_states():
    return [(31, T, H) for T, H in sc.LONG_H.items()]


def r9(tree, ref):
    for p in (str(c.R), str(c.R / 'vendor/NumSim-mine'), str(c.R / 'evaluation/controllers')):
        if p not in sys.path:
            sys.path.insert(0, p)
    rows, alert = [], False
    for s, T in tl3m_states():
        m = _cap_meta(tree, 'TL3', T, J, seed=s).get('k9_w1') or {}
        C_T = None
        tpl = sc.cap_dir(tree, 'TL3', T, J, seed=s) / 'template.pickle'
        if tpl.is_file():
            try:
                C_T = pickle.loads(tpl.read_bytes())['owned'][0].cfg.network.movement_capacity_by_movement_veh_h.get(
                    K91_T_SHARED)
            except Exception:
                C_T = None
        s37 = (m.get('s') or {}).get('37|p1')
        C_N = (m.get('after') or {}).get(K91_W1[1])
        lane1 = None if C_N is None or C_T is None else C_N + C_T
        flag = lane1 is not None and s37 is not None and lane1 > 2 * s37
        alert |= flag
        rec = _k91_record(tree, sc.job_label('TL3', T, J, 'OBS', 3, seed=s))
        b1 = ((rec.get('blocks') or [None])[0] or {})
        vk = _vk91(ref, s).get('conn') or {}
        w0 = int(T) // 150
        rows.append({'seed': s, 'T': T, 'C_N': C_N, 'C_T': C_T, 'lane1_sum': lane1, 's37p1': s37,
                     'two_s37p1': None if s37 is None else 2 * s37, 'alert': flag, 'rule': m.get('rule'),
                     'model_w1_departures_block1': b1.get('w1_departures'),
                     'vissim_entries_block1': {mv: _vwin(vk.get(cn), w0, w0 + 1) for mv, cn in K91_W1_CONN.items()}})
    return {'rows': rows, 'alert': alert}


def r10(tree, root, ref):
    ev = sc.read_json(Path(root) / 'diagnostics' / 'sdmpc_n31_20260924' / 'k9' /
                      'wout_side_handoff_v3c3_20261009.json') or {}
    v = ev.get('values') or {}
    shares = ({'free': v['shares']['free'], v['ramp_of']['R_D_E']: v['shares']['R_D_E'],
               v['ramp_of']['R_D_W']: v['shares']['R_D_W']} if v else {})
    rows, worst = [], 0.0
    for s, T in tl3m_states():
        label = sc.job_label('TL3', T, J, 'OBS', 3, seed=s)
        sm = sc.read_json(sc.job_dir(tree, label) / 'summary.json') or {}
        wc = (k8b0(sm, 3) or {}).get('wout_counters') or {}
        tot = math.fsum(wc.get(f'assigned|side|{d}', 0.0) for d in shares)
        dev = max(abs(wc.get(f'assigned|side|{d}', 0.0) / tot - shares[d]) for d in shares) if tot > 0 else None
        worst = max(worst, dev or 0.0)
        rec = _k91_record(tree, label)
        hand = math.fsum(((b or {}).get('sc2001_transfer') or {}).get('wout_handover', 0.0)
                         for b in (rec.get('blocks') or [])[:3])
        w0 = int(T) // 150
        rows.append({'seed': s, 'T': T, 'side_assigned_veh': tot, 'share_dev': dev,
                     'side_handoff_veh': wc.get('side_handoff_veh'), 'handover_transfer_veh': hand,
                     'blocked_by_room0_steps': None,
                     'vissim_10703_450s': _vwin((_vk91(ref, s).get('conn') or {}).get('10703'), w0, w0 + 3)})
    long_rows = {}
    for s, T, H in _long_states():
        occ = {}
        for arm in (J, 'BASE'):
            rec = _k91_record(tree, sc.job_label('TL3', T, arm, 'OBS', H))
            occ[arm] = [((b or {}).get('corridor') or {}).get('occupancy_veh') for b in rec.get('blocks') or []]
        long_rows[str(T)] = {'corridor_occupancy_block_ends': occ, 'note': 'the corridor ready backlog is not '
                             'recorded; block-end occupancy is reported in its place'}
    return {'rows': rows, 'max_share_dev': worst, 'long': long_rows, 'alert': worst > 1e-9}


def _periods(T, H):
    end = min(float(T) + H * 150.0, 8970.0)
    cuts = [float(T)] + [x for x in (4500.0, 6240.0) if T < x < end] + [end]
    return [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]


def r11(tree, ref):
    rows = []
    for s, T in tl3m_states():
        m = _cap_meta(tree, 'TL3', T, J, seed=s).get('k9_f17b') or {}
        ew = _vk91(ref, s).get('ew') or {}
        w0 = int(T) // 150
        per = {}
        for o in K91_EW:
            pe = (m.get('per_exit') or {}).get(o) or {}
            v = _vwin(ew.get(o), w0, w0 + 3)
            per[o] = {'forecast': pe.get('forecast'), 'c0': pe.get('c0'),
                      'vissim_real_450s': (v[0] / v[1]) if v and v[1] else None}
        rows.append({'seed': s, 'T': T, 'candidate': m.get('candidate'), 'per_exit': per})
    long_rows, alert = {}, False
    spill = ((ref.get('seeds') or {}).get('31') or {}).get('spill_windows_W') or []
    for s, T, H in _long_states():
        sm = job(tree, 'TL3', T, J, 'OBS', H)
        if not sm or not sm.get('ok'):
            long_rows[str(T)] = {'missing': True}
            continue
        st = sm.get('steps') or {}
        cap = (sm.get('cap') or {}).get('10491')
        tt, xs = st.get('t') or [], st.get('stock_10491') or []
        fw = (sm.get('k8b0') or {}).get('fw_steps') or {}
        ft = fw.get('t') or []
        kl = [k for k in fw if k.startswith('offramp_flow_') and '10491' in k]
        kb = [k for k in fw if k.startswith('offramp_blocked_flow_') and '10491' in k]
        per = []
        for a0, a1 in _periods(T, H):
            n = sum(1 for t in tt if a0 < t <= a1 + 1e-9)
            blk = sum(1 for t, x in zip(tt, xs) if a0 < t <= a1 + 1e-9 and cap is not None and x is not None
                      and x >= cap - sc.PORT_BLOCK_MARGIN_VEH)
            nw = int(round((a1 - a0) / 30.0))
            vw = sum(1 for w0_, w1_ in spill if a0 <= w0_ and w1_ <= a1 + 1e-9)
            land = sum(sum((fw[k][i] or 0.0) for k in kl) for i, t in enumerate(ft) if a0 < t <= a1 + 1e-9)
            blkf = sum(sum((fw[k][i] or 0.0) for k in kb) for i, t in enumerate(ft) if a0 < t <= a1 + 1e-9)
            nft = sum(1 for t in ft if a0 < t <= a1 + 1e-9)
            rel = sum((b.get('port_release') or {}).get('10491', 0.0) for b in sm.get('blocks') or []
                      if a0 < b['t_end'] <= a1 + 1e-9)
            row = {'period': [a0, a1], 'model_blocked_ratio': blk / n if n else None,
                   'vissim_spill_ratio': vw / nw if nw else None,
                   'model_request_veh_h': (land + blkf) / nft if nft else None,
                   'model_landed_veh_h': land / nft if nft else None,
                   'model_release_veh_h': rel * 3600.0 / (a1 - a0)}
            if row['model_blocked_ratio'] is not None and row['vissim_spill_ratio'] is not None:
                row['diff'] = row['model_blocked_ratio'] - row['vissim_spill_ratio']
                alert |= abs(row['diff']) > 0.10
            per.append(row)
        long_rows[str(T)] = {'periods': per}
    return {'rows': rows, 'long': long_rows, 'alert': alert}


def r12(gates, k8bt_path=K8BT_GATES):
    k8bt = sc.read_json(k8bt_path) if Path(k8bt_path).is_file() else None
    sha_ok = Path(k8bt_path).is_file() and sc.sha256_file(k8bt_path) == K8BT_GATES_SHA256

    def dem(g):
        out = {}
        for T in sc.LONG_JUDGED:
            it = ((((g or {}).get('gates') or {}).get('G-EB-5') or {}).get('items') or {}).get(f'{T}_stock') or {}
            out[str(T)] = {k: v.get('demoted') for k, v in sorted((it.get('value') or {}).items())
                           if isinstance(v, dict)}
        return out
    now, then = dem(gates), dem(k8bt) if k8bt else None
    return {'k91t': now, 'k8bt': then, 'k8bt_sha_ok': sha_ok,
            'alert': None if then is None else now != then}


def r13(tree, ref):
    out = {}
    R = (ref.get('seeds') or {}).get('31') or {}
    spill = R.get('spill_windows_W') or []
    for s, T, H in _long_states():
        sm = job(tree, 'TL3', T, J, 'OBS', H)
        if not sm or not sm.get('ok'):
            out[str(T)] = {'missing': True}
            continue
        ne = [k for k in range(1, H + 1)
              if not any(w0 < T + 150.0 * k and w1 > T + 150.0 * (k - 1) for w0, w1 in spill)]
        blk = sum(((sm['blocks'][k - 1] if k <= len(sm['blocks']) else {}).get('blocked_steps') or {}).get('10491', 0.0)
                  for k in ne)
        ratio = blk / (150.0 * len(ne)) if ne else None
        fb = (sm.get('first_block_t') or {}).get('10491')
        ev = (((R.get('states') or {}).get(str(T))) or {}).get('ext127_first500')
        out[str(T)] = {'nonevent_blocks': len(ne), 'blocked_ratio_nonevent': ratio,
                       'open_a': None if ratio is None else ratio > 0.2, 'first_block_10491': fb,
                       'vissim_event_start': ev,
                       'open_b': None if fb is None or ev is None else fb < ev - 300.0}
    return out


def r14(tree):
    touches = {}
    jdir = sc.sa_out() / 'jobs' / tree
    for p in sorted(jdir.glob('*/k91_record.json')):
        rec = sc.read_json(p) or {}
        touches[p.parent.name] = ((rec.get('top') or {}).get('z1_touch_events'))
    adfull = {}
    for p in sorted(jdir.glob('*_ad_full/summary.json')):
        s = sc.read_json(p) or {}
        if s.get('ok') and s.get('complete_primal_state_match') is not False:
            continue
        err = s.get('error') or ''
        keys = sorted(set(re.findall(r'State keys mismatch: ([^\s\'"]+)', err)))
        adfull[p.parent.name] = {'error_kind': s.get('error_kind'), 'key_paths': keys, 'tail': err[-300:]}
    return {'z1_touch_events': touches, 'latent_outside_z1': list(K91_LATENT_OUTSIDE_Z1), 'adfull_failures': adfull,
            'alert': None}


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = c.parser(__doc__)
    ap.add_argument('--tree', required=True)
    ap.add_argument('--gates-json')
    ap.add_argument('--eo-root', default=str(DEFAULT_EO))
    ap.add_argument('--k91', action='store_true', help='K9-1-0: R9-R14 and k91_outcome (amendment 19 r2 6 / 7)')
    ap.add_argument('--k8bt-gates', default=str(K8BT_GATES), help='R12: the k8bt gates file (sha checked)')
    args = ap.parse_args()
    c.apply(args)
    c.lower_priority()
    ref = sc.read_json(sc.sa_out() / 'vissim_ref.json') or {}
    gates = sc.read_json(args.gates_json) if args.gates_json else sc.read_json(
        sc.sa_out() / 'gates' / f'gates_{args.tree}.json')
    rep = {'schema': 'k8b-report/v1', 'tree': args.tree, 'amendment16_sha256': sc.K8B_AMENDMENT16_SHA256,
           'amendment17_sha256': sc.K8B_AMENDMENT17_SHA256, 'gates_combined': (gates or {}).get('combined')}
    for name, fn in (('R1', lambda: r1(args.tree)), ('R2', lambda: r2(args.tree, ref)),
                     ('R3', lambda: r3(args.tree, ref)), ('R4', lambda: r4(args.tree, ref)),
                     ('R5', lambda: r5(args.tree, ref)), ('R6', lambda: r6(args.tree, c.R)),
                     ('R7', lambda: r7(gates)), ('R8', lambda: r8(args.tree)),
                     ('probe_3_4', lambda: probe34(args.tree))):
        try:
            rep[name] = fn()
        except Exception as exc:
            import traceback
            rep[name] = {'error': traceback.format_exc()[-1500:], 'alert': None}
    rep['alerts'] = [k for k in ('R1', 'R2', 'R3', 'R4', 'R6', 'R7', 'R8') if (rep.get(k) or {}).get('alert')]
    dest = sc.sa_out() / 'gates' / f'k8b_report_{args.tree}.json'
    sc.write_json(dest, rep)
    lines = [f'# K8b report items ({args.tree}) -- report, not a verdict', '',
             f'alerts (section 6): {rep["alerts"] or "none"}', '',
             sc.md_table(['item', 'alert'], [[k, (rep.get(k) or {}).get('alert')] for k in
                                             ('R1', 'R2', 'R3', 'R4', 'R6', 'R7', 'R8')]), '',
             f'R5 3(a) decomposition: MAE(e) {(rep.get("R5") or {}).get("mae_e")}, mean(i) '
             f'{(rep.get("R5") or {}).get("mean_i")}, MAE(i) {(rep.get("R5") or {}).get("mae_i")}, persistence '
             f'{(rep.get("R5") or {}).get("persistence_mae")}, stage 2 (iv) {(rep.get("R5") or {}).get("stage2_iv")}']
    dest.with_suffix('.md').write_text('\n'.join(lines), encoding='utf-8')
    print('K8B_REPORT', rep['alerts'], '->', dest)
    if (gates or {}).get('combined') == 'STOP':
        diag = {'schema': 'k8b-q7-diagnosis/v1', 'tree': args.tree, 'i': diag_i(args.tree, ref, gates, c.R),
                'ii': diag_ii(args.tree, gates, args.eo_root), 'iii': diag_iii(args.tree),
                'iv': (rep.get('R5') or {}).get('stage2_iv'),
                'rule': 'section 7.3; a criterion without data is not confirmed (conservative)'}
        sc.write_json(sc.sa_out() / 'gates' / 'k8b_q7_diagnosis.json', diag)
        print('K8B_Q7_DIAGNOSIS ->', sc.sa_out() / 'gates' / 'k8b_q7_diagnosis.json')
    if args.k91:                                          # K9-1-0 (amendment 19 r2 sections 6 / 7)
        k91 = {'schema': 'k91-report/v1', 'tree': args.tree, 'amendment19_sha256': sc.K91_AMENDMENT19_SHA256}
        for name, fn in (('R9', lambda: r9(args.tree, ref)), ('R10', lambda: r10(args.tree, c.R, ref)),
                         ('R11', lambda: r11(args.tree, ref)), ('R12', lambda: r12(gates, args.k8bt_gates)),
                         ('R13', lambda: r13(args.tree, ref)), ('R14', lambda: r14(args.tree))):
            try:
                k91[name] = fn()
            except Exception as exc:
                import traceback
                k91[name] = {'error': traceback.format_exc()[-1500:], 'alert': None}
        k91['alerts'] = [k for k in ('R9', 'R10', 'R11', 'R12') if (k91.get(k) or {}).get('alert')]
        sc.write_json(sc.sa_out() / 'gates' / f'k91_report_{args.tree}.json', k91)
        diag = sc.read_json(sc.sa_out() / 'gates' / 'k8b_q7_diagnosis.json')
        outcome = k91_outcome(gates, diag)
        sc.write_json(sc.sa_out() / 'gates' / 'k91_outcome.json', outcome)
        print('K91_REPORT', k91['alerts'], 'K91_OUTCOME', outcome['form'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
