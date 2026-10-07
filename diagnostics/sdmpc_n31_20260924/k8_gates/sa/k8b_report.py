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
their values and source fields; any criterion without its data is 'not confirmed'."""
import csv
import json
import math
import pickle
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


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = c.parser(__doc__)
    ap.add_argument('--tree', required=True)
    ap.add_argument('--gates-json')
    ap.add_argument('--eo-root', default=str(DEFAULT_EO))
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
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
